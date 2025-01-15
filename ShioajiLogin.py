import time
from typing import List, Dict
import shioaji as sj
from shioaji import TickSTKv1, Exchange
import shioaji.order as stOrder
from shioaji.constant import (
    OrderState,
    ACTION_BUY,
    ACTION_SELL,
    STOCK_ORDER_LOT_INTRADAY_ODD,
    STOCK_ORDER_LOT_COMMON,
)
import logging
import pandas as pd
import datetime
from dotenv import load_dotenv
import os
from pathlib import Path
import sys

# Get the helpers directory
helpers_dir = Path(__file__).resolve().parent.parent / "helpers"
# Add to sys.path
sys.path.insert(0, str(helpers_dir))
######################################################
try:
    import ShioajiLogin as mysj  # import shioajiLogin, get_snapshots
    import misc
    import yf_data as yfin
except ImportError as e:
    print(f"ImportError: {e}")

print(sj.__version__)
# .env file on helpers


def shioajiLogin(simulation=True):
    load_dotenv()
    person_id = os.getenv("PERSON_ID")
    api_key = os.getenv("API_KEY")
    secret_key = os.getenv("SECRET_KEY")
    CA_passwd = os.getenv("CA_passwd")
    api = sj.Shioaji(simulation=simulation)
    api.login(
        api_key=api_key,
        secret_key=secret_key,
        # contracts_timeout=10000,
        # contracts_cb=lambda security_type: print(
        #     f"{repr(security_type)} fetch done.")
    )
    if os.name == "nt":
        CA = "c:\ekey\\551\\" + person_id + "\\S\\Sinopac.pfx"
    elif os.name == "posix":
        CA = "~/ekey/551/A125841482/S/Sinopac.pfx"

    result = api.activate_ca(
        ca_path=CA,
        ca_passwd=CA_passwd,
        person_id=person_id,
    )
    assert result, "ca error"
    print(api.usage())
    return api


class Bot:
    def __init__(self, symbols: List, sim=False):
        logging.basicConfig(
            filename="capm_zero_beta.log",
            level=logging.INFO,
            format="%(asctime)s %(levelname)s: %(message)s",  # auto insert current time, and logging level, just as INFO, DEBUG...
        )
        self.logging = logging
        self.bought_prices = {}
        self.sell_price = {}
        self.pos = {}
        self.snapshots = {}
        self.trades = {}
        self.tick_value = {}
        self.previous_close_prices = {}
        self.contracts = {}
        self.tax_rate={}
        self.taken_profit = 0
        self.symbols = symbols
    
        self.api = sj.Shioaji(simulation=sim)
        self.login()
        # for tick value
        self.snapshots = self.get_snapshots(symbols)

        for symbol in self.symbols:
            self.contracts[symbol] = self.api.Contracts.Stocks[symbol]            
            self.tax_rate[symbol] = 1 / 1000 if self.api.Contracts.Stocks.TSE[symbol].category == "00" else 3 / 1000
            # close price of last trading day
            self.previous_close_prices[symbol] = self.contracts[symbol].reference
            self.tick_value[symbol] = misc.get_tick_unit(self.snapshots[symbol].close)
        # contract = self.api.Contracts.Indexs.TSE.TSE001
        # end_date = misc.get_today()
        # start_date = misc.sub_N_Days(15)
        # pd = yfin.download_data("^TWII", interval="1d", start=start_date, end=end_date)
        # self.previous_close_index = pd.Close.iloc[-1]
        self.api.set_order_callback(self.order_cb)

    # 處理訂單成交的狀況,用來更新交割款
    # order_cb confirmed ok.
    def order_cb(self, stat, msg: Dict):
        # print(f"stat: {stat}, msg:{msg}")
        # OrderState.StockDeal is a dict name
        if stat == OrderState.StockDeal:
            print(f"stk deal: {stat.StockDeal.value}, msg:{msg}")
            # global g_settlement
            code = msg["code"]
            action = msg["action"]
            price = msg["price"]
            quantity = msg["quantity"] * 1000 if msg["order_lot"] == "Common" else msg["quantity"]
            if code in self.symbols:
                if action == ACTION_BUY:
                    self.bought_prices[code] = price
                elif action == ACTION_SELL:
                    self.taken_profit += misc.calculate_profit(
                        buy_price=self.bought_prices[code],
                        sell_price=price,
                        quantity=quantity,
                        tax_rate=self.tax_rate[code]
                    )
                # self.msglist.append(msg)
                # s = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logging.info(f"Deal: {action} {code} {quantity} @ {price}")

            # with self.mutexstat:
            #     self.statlist.append(stat)
        elif stat == OrderState.StockOrder:
            # print(f"ord_cb: stat: {stat}, msg:{msg}")
            pass

    def login(self):
        load_dotenv()
        person_id = os.getenv("PERSON_ID")
        api_key = os.getenv("API_KEY")
        secret_key = os.getenv("SECRET_KEY")
        CA_passwd = os.getenv("CA_passwd")

        self.api.login(api_key=api_key, secret_key=secret_key)
        if os.name == "nt":
            CA = "c:\ekey\\551\\" + person_id + "\\S\\Sinopac.pfx"
        elif os.name == "posix":
            CA = "~/ekey/551/A125841482/S/Sinopac.pfx"

        result = self.api.activate_ca(
            ca_path=CA,
            ca_passwd=CA_passwd,
            person_id=person_id,
        )
        assert result, "ca error"
        print(self.api.usage())

    def get_position_qty(self, symbol) -> int:
        try:
            positions = self.api.list_positions(self.api.stock_account, unit=sj.constant.Unit.Share)
            return next((pos.quantity for pos in positions if pos.code == symbol), 0)
        except sj.error.TokenError as e:
            self.logging.error(f"Token error: {e.detail}")
            return 0

    def buy(self, symbol, price, quantity):
        return self.place_flexible_order(symbol=symbol, action=ACTION_BUY, price=price, qty=quantity)

    def sell(self, symbol, price, quantity):
        return self.place_flexible_order(symbol=symbol, action=ACTION_SELL, price=price, qty=quantity)

    def place_flexible_order(self, symbol, price, qty, action):
        # Determine the number of regular lots and odd lot quantity
        common_lot_qty = qty // 1000  # Regular lots (1 lot = 1000 shares)
        odd_lot_qty = qty % 1000  # Remaining odd lot quantity
        contract = self.api.Contracts.Stocks[symbol]
        # Place regular lot orders if applicable
        if common_lot_qty > 0:
            order = self.api.Order(
                price=price,  # contract.limit_down,
                quantity=int(common_lot_qty),  # Total quantity in regular lots
                action=action,
                # price_type="MKT",
                price_type="LMT",
                # order_type="IOC",
                order_type="ROD",
                order_lot=STOCK_ORDER_LOT_COMMON,  # Regular lot
                account=self.api.stock_account,
            )
            trade = self.api.place_order(contract, order)
            print(f"Placed regular lot {action} order for {symbol}: {common_lot_qty} lot(s) @{price}")
            # print("status:", trade.status.status)
        # if qty like 1300 shares, and you want to place it all, change elif to if!!!
        elif odd_lot_qty > 0:
            order = self.api.Order(
                price=price,  # contract.limit_down,
                quantity=int(odd_lot_qty),  # Remaining odd lot quantity
                action=action,
                price_type="LMT",
                # ROC is the only available ord type for intraday odd lot.
                order_type="ROD",
                order_lot=STOCK_ORDER_LOT_INTRADAY_ODD,
                account=self.api.stock_account,
            )
            trade = self.api.place_order(contract, order)
            print(f"Placed odd lot {action} order for {symbol}: {odd_lot_qty} shares @{price}")
        # log the most crucial info for record
        self.logging.info(f"trade: {trade}")
        print("trade:", trade)
        return trade
        # print("status:", trade.status.status)

    def wait_till_filled(self):
        while not all(trade.status.status == "Filled" for trade in self.trades.values()):
            for trade in self.trades.values():
                # trade status will be updated automatically
                self.api.update_status(self.api.stock_account, trade=trade)
                print(f"{trade.contract.code}/{trade.status.status}")
            time.sleep(20)

    def cancelOrders(self) -> None:
        # Before obtaining the Trade status, it must be updated with update_status!!!
        self.api.update_status(self.api.stock_account)
        tradelist = self.api.list_trades()
        trades_to_cancel = [
            trade
            for trade in tradelist
            if trade.status.status
            not in {
                stOrder.Status.Cancelled,
                stOrder.Status.Failed,
                stOrder.Status.Filled,
            }
            and trade.contract.code in self.symbols
        ]

        if len(trades_to_cancel) == 0:
            # nothing to cancell
            return

        for trade in trades_to_cancel:
            try:
                self.api.cancel_order(trade=trade)
                # wait till the order is cancelled.
                # while trade.status.status != "Cancelled":
                #     trade = self.api.update_status(
                #         account=self.api.stock_account)
                self.api.update_status(self.api.stock_account)
                self.logging.info(
                    f"order cancelled: {trade.contract.code}/{trade.status.status}, cqty {trade.status.cancel_quantity}"
                )
            except Exception as e:
                self.logging.error(f"Error canceling order {e}")

    # shioajiLogin(simulation=True)
    def get_snapshots(self, symbols: List) -> dict:
        """Fetches the latest stock prices for the given symbols.
        snapshots:, {'2330': Snapshot(ts=1735655400000000000, code='2330', exchange='TSE', open=1080.0, high=1085.0, low=1075.0, close=1075.0, tick_type=<TickType.Sell: 'Sell'>, change_price=-15.0, change_rate=-1.38, change_type=<ChangeType.Down: 'Down'>, average_price=1077.68, volume=12, total_volume=28375, amount=12900000, total_amount=30579040000, yesterday_volume=23926.0, buy_price=1075.0, buy_volume=4583.0, sell_price=1080.0, sell_volume=64, volume_ratio=1.19)
        """
        snapshots = self.api.snapshots([self.api.Contracts.Stocks[symbol] for symbol in symbols])
        # df = pd.DataFrame(s.__dict__ for s in snapshots)
        # df.ts = pd.to_datetime(df.ts)
        return {snapshot.code: snapshot for snapshot in snapshots}

    def get_theory_prices(self, betas, snapshots):
        contract = self.api.Contracts.Indexs.TSE.TSE001
        TSE001_snapshot = self.api.snapshots([contract])
        # current_index = TSE001_snapshot[0].close
        TSE001_change_rate = TSE001_snapshot[0].change_rate/100
        diffs = {}
        theory_prices = {}
        # mkt_ret_pct = ((current_index - self.previous_close_index) / self.previous_close_index) * 100
        # snapshots = self.get_snapshots(self.symbols)
        for symbol in self.symbols:
            diffs[symbol] = snapshots[symbol].change_rate - betas[symbol + "_tw"] * TSE001_change_rate
            # self.previous_close_prices[symbol]
            theory_prices[symbol] = self.previous_close_prices[symbol] * (
                1 + (betas[symbol + "_tw"] * TSE001_change_rate)
            )

        return {k: round(v, 2) for k, v in theory_prices.items()}

    def logout(self) -> None:
        self.api.logout


class CandleStickBuilder:
    def __init__(self, period, symbol, api):
        self.period = period
        self.symbol = symbol
        self.api = api
        self.contract = self.api.Contracts.Stocks[symbol]
        self.data = pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])
        self.current_candle_start = None
        self.api.quote.subscribe(
            self.contract, quote_type=sj.constant.QuoteType.Tick, version=sj.constant.QuoteVersion.v1
        )
        self.api.quote.set_on_tick_stk_v1_callback(self.on_tick)

    def on_tick(self, exchange: Exchange, tick: TickSTKv1):
        time = tick.datetime
        # price = float(tick["close"])
        # volume = int(tick["volume"])
        price = tick.close
        volume = tick.volume
        self.update_candle(time, price, volume)

    def update_candle(self, time, price, volume):
        if self.current_candle_start is None or time >= self.current_candle_start + datetime.timedelta(
            minutes=self.period
        ):
            # Create a new candle
            self.current_candle_start = time - datetime.timedelta(minutes=time.minute % self.period)
            new_row = pd.DataFrame(
                {
                    "time": [self.current_candle_start],
                    "open": [price],
                    "high": [price],
                    "low": [price],
                    "close": [price],
                    "volume": [volume],
                }
            )
            # Exclude empty or all-NA rows before concatenation
            if not new_row.dropna(how="all").empty:
                self.data = pd.concat([self.data, new_row], ignore_index=True)
        else:
            # Update the existing candle
            self.data.loc[self.data.index[-1], "close"] = price
            self.data.loc[self.data.index[-1], "high"] = max(self.data.loc[self.data.index[-1], "high"], price)
            self.data.loc[self.data.index[-1], "low"] = min(self.data.loc[self.data.index[-1], "low"], price)
            self.data.loc[self.data.index[-1], "volume"] += volume
