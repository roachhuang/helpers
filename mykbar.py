# -*- coding: utf-8 -*-
"""
Created on Wed Feb  9 21:47:24 2022

@author: William Zhuo
todo:
    1. start and end are in date format
    2. column name of ts and Date to be unify. 
"""
# import shioaji as sj
import numpy as np
import pandas as pd

# import yfinance as yf

# from pandas import DataFrame
from time import sleep
from datetime import date, datetime, timedelta
from typing import Optional

# import sqlite3
import json
from pymongo import MongoClient

from ShioajiLogin import shioajiLogin
from yf_data import download_data


###############################################
# 取得0050和小台近月的合約
##############################################
def getContract(api, symbol: str, the_type: str = "stock"):  # ='MXFR1'  # ='future'
    if the_type == "future":
        return api.Contracts.Futures[symbol]
    elif the_type == "stock":
        return api.Contracts.Stocks[symbol]
    else:
        print("Un-implemented type in getContract")


# get future recent months contract
def getFrontMonthContract(
    api,
    futureID,  # ='UDF'
    removeR1R2=False,  # 回傳物件要用來抓報價的時候設False,物件要用來下單的時候設True
    daysSwitch=7,
):
    l = list(api.Contracts.Futures[futureID])
    # 移除近月和次月,近月次月只能抓報價無法下單
    if removeR1R2:
        for i in range(len(l) - 1, -1, -1):
            # 近月和次月
            if l[i].code[3] == "R":
                l.pop(i)
            else:
                # 移除即將結算的合約,或者已結算的合約
                delivery_date = datetime.strptime(l[i].delivery_date, "%Y/%m/%d").date()
                today = get_today()
                diffdays = (delivery_date - today).days
                if diffdays <= max(daysSwitch, 0):
                    l.pop(i)
    len_l = len(l)
    min_delivery_month = "99999999999"
    min_i = 0
    min_id = 0
    for i in range(0, len_l, 1):
        if l[i].code == futureID + "R1":
            min_delivery_month = l[i].delivery_month
            min_i = i
            min_id = l[i].code
            break
        valA = int(l[i].delivery_month)
        valB = int(min_delivery_month)
        if valA < valB:
            min_delivery_month = l[i].delivery_month
            min_i = i
            min_id = l[i].code
    ret = api.Contracts.Futures[min_id]
    return ret


#######################################
# 用datetime取得兩年前/一年前/昨天的日期
#######################################
def get_today()->datetime.date:
    return datetime.today().date()
    # return datetime.date.today()  if just import datetime


def sub_N_Days(days: int) -> datetime.date:
    return (datetime.today() - timedelta(days)).date()


def add_N_Days(days: int, date=None) -> datetime.date:
    if date is None:
        date = datetime.today()
    return (date + timedelta(days))


#######################################
# 給定日期時間範圍，回傳1分k的dataframe. exclude the data when mkt is not close yet.
#######################################
def getKbars(
    symbol: str,
    start: str,  # ='2022-01-01'
    end: str  # ='2022-01-20'
    # set longer timeout if date range is wide
    ,
    timeout=100000,
) -> pd.DataFrame:

    # 取得kbars資料
    api = shioajiLogin(simulation=False)
    contract = getContract(api=api, symbol=symbol)
    if timeout > 0:
        kbars = api.kbars(contract, start=start, end=end, timeout=timeout)
    else:
        kbars = api.kbars(contract, start=start, end=end)

    # 把0050的tick轉成dataframe，並且印出最前面的資料
    df = sjDataToDf(kbars)
    # inplace=True This argument modifies the original DataFrame df instead of creating a new one.
    df.drop(df.tail(1).index, inplace=True)
    sleep(1)

    # df=yf.download('00686R' + ".tw",start=start, end=end, interval='1m')
    api.logout()
    return df


#######################################
# 給定日期時間範圍，回傳ticks (bid/ask price and volume) 的dataframe. include historic and current in transaction data
#######################################
def getTicks(
    api,
    contract,
    start,  # ='2022-01-01'
    end,  # ='2022-01-20'
    timeout=100000,
    Enable_print=False,
):

    list_ticks = []
    enddate = datetime.strptime(end, "%Y-%m-%d").date()
    day = datetime.strptime(start, "%Y-%m-%d").date()
    while day != enddate:
        # 取得ticks
        if timeout > 0:
            ticks = api.ticks(contract=contract, date=str(day), timeout=timeout)
        else:
            ticks = api.ticks(contract=contract, date=str(day), timeout=timeout)
        df_ticks = sjDataToDf(ticks)
        list_ticks.append(df_ticks)
        # 加一天
        day = day + datetime.timedelta(days=1)
        if Enable_print:
            print(day)
        # CD 50 miliseconds,避免抓太快被永豐ban掉
        sleep(0.05)
    if len(list_ticks) > 0:
        df_ticks_concat = pd.concat(list_ticks)
        df_ticks_concat = df_ticks_concat.drop(columns="ts")
    else:
        df_ticks_concat = []
    return df_ticks_concat


#########################################################
# 檢查collectionN在與否
#########################################################
def checkCollectionExist(
    dbname: str, collectionName: str
) -> bool:  # ='kbars.db'  # ='\'MXFR1\''
    with MongoClient() as client:
        db = client[dbname]
        collection_names = db.list_collection_names()
        return collectionName in collection_names


# 用來看最後一筆日期, ts column is datetime
def checkLastTs(dbname: str, collectionName: str):
    with MongoClient() as client:
        collection = client[dbname][collectionName]

        # Determine the field to sort by based on the database name
        sort_field = "Date" if dbname != "1m" else "ts"

        # Find the document with the maximum timestamp value
        max_document = collection.find_one({}, sort=[(sort_field, -1)])

    assert max_document, "Cannot find the last document in the collection"

    return max_document[sort_field]


#######################################
# 更新資料庫的kbars. get 1minute k data and write to kbars database
############################################
# covert to datetime.date format
def convert2Date(t) -> datetime.date:
    if type(t) == datetime.date:
        # Already a datetime.date object, return it directly
        return t
    elif type(t) == datetime:
        # Convert datetime object to date
        return t.date()
    else:
        # Try converting from string format (if possible)
        try:
            return datetime.strptime(
                str(t), "%Y-%m-%d"
            ).date()  # Assuming YYYY-MM-DD format
        except ValueError:
            print("Couldnt convert, return None!")
            return None


def UpdateMA(KBar1M, symbol, period):
    # 取得要計算MA的時間週期
    number = 6  # 1 day kbar for short-term trading
    # 取得N日的股票日資料 returns a datetime.date object
    today = date.today()
    start = today - timedelta(days=number)

    # contract = kb.getContract(api, symbol=symbol, the_type="stock")

    # make sure the collection is in 1m candle data. may change to 5M if i want to replace 1m with 5m candle data for intraday trade.
    backFillKbars(collectionName=symbol, period="1m", start=start, end=today)
    df = readFromDB(dbName=period, collectionName=symbol, start=start, end=today)

    # # Get today's date
    # today = date.today()

    # # Calculate yesterday's date by subtracting one day
    # yesterday = today - timedelta(days = 1)

    # # Format yesterday's date as a string (YYYY-MM-DD)
    # formatted_date = yesterday.strftime('%Y-%m-%d')

    # contract = api.Contracts.Stocks[symbol]
    # dict_ticks = api.kbars(contract=contract, date=formatted_date)
    # df=pd.DataFrame({**dict_ticks})   # he double asterisk (**) is a Python operator used for unpacking dictionaries.
    # df.index=pd.to_datetime(df.ts)
    df.columns = df.columns.str.lower()
    # df.drop('_id', axis=1)
    # df.rename(columns={'ts': 'time'})
    for index, row in df.iterrows():
        KBar1M.TAKBar["time"] = np.append(KBar1M.TAKBar["time"], row.ts)
        KBar1M.TAKBar["open"] = np.append(KBar1M.TAKBar["open"], row.open)
        KBar1M.TAKBar["close"] = np.append(KBar1M.TAKBar["close"], row.close)
        KBar1M.TAKBar["high"] = np.append(KBar1M.TAKBar["high"], row.high)
        KBar1M.TAKBar["low"] = np.append(KBar1M.TAKBar["low"], row.low)
        KBar1M.TAKBar["volume"] = np.append(KBar1M.TAKBar["volume"], row.volume)
    # KBar1M.TAKBar = np.vstack((KBar1M.TAKBar, df.to_numpy()))


#######################################
# 更新資料庫的ticks. get tick data and write to ticks database
############################################
def backFillTicks(api, contractObj, collectionName, start, end):
    today = get_today()
    # for 100ma needs at least 17days' sample data coz 6hrs trading hrs per day
    ten_days_ago = sub_N_Days(days=20)
    one_years_ago = sub_N_Days(days=365)
    yesterday = sub_N_Days(days=1)

    dbName = "ticks"  # 這個應該放在function
    # push kbars data to collectionN    symbol:str = collectionName
    db_exist = checkCollectionExist(dbname=dbName, collectionName=collectionName)
    client = MongoClient()
    db = client[dbName]
    collection = db[collectionName]

    # the tbl exists
    if db_exist:
        ret = checkLastTs(dbname=dbName, collectionName=collectionName)
        # lastdatetime = datetime.datetime.strptime(str(ret), '%Y-%m-%d %H:%M:%S.%f')
        lastdatetime = datetime.fromtimestamp(ret / 1000)
        start = add_N_Days(date=lastdatetime.date(), days=1)  # date of last data
        end = today
        if start < end:
            ticks = getTicks(
                api, contractObj, start=str(start), end=str(end), Enable_print=True
            )
            # Convert DataFrame to list of dictionaries (one dictionary per row)
            data = json.loads(ticks.reset_index().to_json(orient="records"))
            # Insert data into MongoDB collection
            collection.insert_many(data)
    else:
        # ticks = getTicks(api, contractObj, start=str(
        #     one_years_ago), end=str(yesterday), Enable_print=True)
        ticks = getTicks(
            api,
            contractObj,
            start=str(ten_days_ago),
            end=str(yesterday),
            Enable_print=True,
        )

        # create collectionN        # Convert DataFrame to list of dictionaries (one dictionary per row)
        data = json.loads(ticks.reset_index().to_json(orient="records"))

        # Replace existing documents in MongoDB collection with new data
        collection.delete_many({})  # Delete existing documents
        collection.insert_many(data)  # Insert new documents

    client.close()


# shioaji data into dataframe
def sjDataToDf(sjBars):
    def remove_illegal_time(df):
        # futures
        cond_Sat = ~((df.index.weekday == 5) * (df.index.hour > 5))
        cond_Sun = df.index.weekday != 6
        cond_Mon = ~((df.index.weekday == 0) * (df.index.hour < 8))
        df = df[cond_Sat * cond_Sun * cond_Mon]
        return df

    df = pd.DataFrame({**sjBars})  # 轉成dataframe
    # dfBars.index = pd.to_datetime(dfBars.ts)
    df.ts = pd.to_datetime(df.ts)
    new_column_names = {col: col.lower() for col in df.columns}
    df = df.rename(columns=new_column_names)
    # have to set index for func remove_illegial_time -> pd.index.weekday
    df.index = pd.to_datetime(df.ts)
    df = df.groupby(df.index).first()
    df = df.drop(columns="ts")
    df = remove_illegal_time(df)
    return df


# convert ticks's dataframe into 1minute k dataframe
def ticksTo1mkbars(ticks):
    period = "1min"
    kbars_out = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    kbars_out["Open"] = (
        ticks["close"].resample(period).first()
    )  # 區間第一筆資料為開盤(Open)
    kbars_out["High"] = ticks["close"].resample(period).max()  # 區間最大值為最高(High)
    kbars_out["Low"] = ticks["close"].resample(period).min()  # 區間最小值為最低(Low)
    kbars_out["Close"] = (
        ticks["close"].resample(period).last()
    )  # 區間最後一個值為收盤(Close)
    kbars_out["Volume"] = ticks["volume"].resample(period).sum()  # 區間所有成交量加總
    kbars_out = kbars_out.dropna()
    return kbars_out


def resampleKbars(kbars: pd.DataFrame, period: str = "1d") -> pd.DataFrame:
    # period:1m => 1 month
    # period:1min => 1 minute

    kbars_out = pd.DataFrame({})
    if not kbars.empty:
        kbars_out = kbars.resample(period).agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        kbars_out = kbars_out.dropna()
    # df.resample('4H', label='right').agg(OHLCV_AGG).dropna()
    return kbars_out


def backFillKbars(
    collectionName: str, interval: str, start: datetime.date, end=datetime.today()
) -> None:

    kbars = pd.DataFrame()
    start = convert2Date(start)
    end = convert2Date(end)
    assert start < end, "start date >= end date!"

    dbName = interval
    # push kbars data to collectionN    # symbol:str = collectionName
    tbl_exist = checkCollectionExist(dbname=dbName, collectionName=collectionName)

    # the tbl exists
    if tbl_exist:
        ret = checkLastTs(dbname=dbName, collectionName=collectionName)
        # lastdatetime = datetime.datetime.strptime(ret, '%Y-%m-%d %H:%M:%S')
        lastdatetime = datetime.fromtimestamp(ret / 1000)
        start = add_N_Days(date=lastdatetime.date(), days=1)  # date of last data

    end = sub_N_Days(days=1)

    if interval == "1m":
        kbars = getKbars(symbol=collectionName, start=str(start), end=str(end))
    else:
        # yfinance
        kbars = download_data(
            collectionName, interval=interval, start=str(start), end=str(end)
        )
        kbars.index.names = ["Date"]  # index is Datetime if interval < '1d'
    # assert not kbars.empty, "no data retrieved!" # this can happen if market not open with the period
    if not kbars.empty:
        kbars = kbars.drop_duplicates()
        # kbars = kbars.dropna()

        # json data will now has a 'ts' key
        data = json.loads(kbars.reset_index().to_json(orient="records"))
        # dict_list = kbars.to_dict(orient='records')
        with MongoClient() as client:            
            collection = client[dbName][collectionName]
            collection.insert_many(data)  # Insert new documents

##################################
# 從資料庫讀取kbars
# start: datetime or none
# todo: start and end are to be in date format
#########################################
def readFromDB(
    dbName: str,
    collectionName: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> pd.DataFrame:
    """
    retruned df columns are renamed into lower case
    """
    with MongoClient() as client:        
        collection = client[dbName][collectionName]

        # Retrieve data from MongoDB collection
        if start is None and end is None:
            query = {}  # Retrieve all data
        else:
            if start is not None:
                # convert datetime.date to ts
                start_ts = int(
                    datetime(start.year, start.month, start.day).timestamp() * 1000
                )
                # start_ts = int(start.timestamp() * 1000)
            if end is not None:
                end_ts = int(datetime(end.year, end.month, end.day).timestamp() * 1000)
                # end_ts = int(end.timestamp() * 1000)

            if dbName == "1m":
                query = {"ts": {"$gte": start_ts, "$lte": end_ts}}
            else:
                # yfinance
                query = {"Date": {"$gte": start_ts, "$lte": end_ts}}
        cursor = collection.find(query)

        # The return type of a find query in MongoDB is a cursor,
        # which is a database object that provides a stream of documents
        # Converting the Cursor to Dataframe, 1st, we convert the cursor to the list of dictionary.
        # list_cur = pd.DataFrame(list(cursor))
        df = pd.DataFrame(cursor).dropna()

        assert not df.empty, "no data in the db"

        # unit=ms is requied for the conversation.  if no unit='ms', it returns 1970!
        df = df.rename(columns={"Date": "ts"})
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")

        if dbName != "1m":
            # get rid of time
            df["ts"] = df["ts"].dt.date

        # df.index = pd.DatetimeIndex(df["ts"])
        df.set_index(pd.DatetimeIndex(df["ts"]), inplace=True)
        # df = df.drop(columns="ts")
        df.columns = [col.lower() for col in df.columns]

    return df
