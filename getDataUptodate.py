import datetime

from mykbar import backFillKbars, readFromDB, sub_N_Days


def getData(symbol:str, interval:str, years:int=12):
    start = sub_N_Days(days=years * 365)
    end = datetime.datetime.today().date()    

    # df = pd.DataFrame()
    backFillKbars( collectionName=symbol, start=start, end=end, interval=interval)
    df = readFromDB(dbName=interval, collectionName=symbol, start=start, end=end)
    # df columns are convered into lower case in readFromDb fn.
    if interval == '1d':
        df.rename(columns={'ts': 'Date'}, inplace=True)
        df.drop(columns=["_id", "stock splits"], inplace=True)
    elif interval == '1h':
        df.rename(columns={"Datetime": "Date"}, inplace=True)
        df.drop(columns=["_id", "stock splits"], inplace=True)

    # df.drop(columns=['_id', 'ts', 'stock splits'], inplace=True)
    new_column_names = {col: col.capitalize() for col in df.columns}
    df.rename(columns=new_column_names, inplace=True)
    if df.index.duplicated().any():
        df = df[~df.index.duplicated(keep="first")]
    return df
