from backtesting import Strategy
from backtesting.test import SMA
import talib
from backtesting.lib import crossover, TrailingStrategy, resample_apply
import pandas_ta as ta


## KD 策略
class KdCross(Strategy):
    """
    fastk: 9-14
    slowd: 2-5
    """

    fastk_period = 9
    # not actually used,stoch calcuates both %K and the basis for %D using the same fastk_period. There's no separate slow period for %K itself.
    slowk_period = 3
    slowd_period = 3

    def init(self):
        self.slowk, self.slowd = self.I(
            talib.STOCH,
            self.data.High,
            self.data.Low,
            self.data.Close,
            self.fastk_period,
            self.slowk_period,
            self.slowd_period,
        )

    def next(self):
        if crossover(self.slowk, self.slowd):  ## K<20 買進
            self.buy()
        elif crossover(self.slowd, self.slowk):  ## K>80 平倉
            self.position.close()


class SmaCross(Strategy):
    """
    當 10 日移動平均往上穿越 20 日移動平均時「買進」
    當 10 日移動平均往下穿越 20 日移動平均時「賣出」
    """

    n1 = 10
    n2 = 20

    def init(self):
        close = self.data.Close
        self.sma1 = self.I(SMA, close, self.n1)
        self.sma2 = self.I(SMA, close, self.n2)

    def next(self):
        if crossover(self.sma1, self.sma2):
            self.buy()
        elif crossover(self.sma2, self.sma1):
            self.sell()


class MaKdCross(Strategy):
    """
    Short-Term Trading:
    Fast MA (10-20), Slow MA (50-100) - Aims to capture short-term trends with potentially more frequent signals.
    Swing Trading: Fast MA (12-20), Slow MA (100-200) - Balances sensitivity and confirmation for potential trend continuation or reversal.
    Positional Trading: Fast MA (20-50), Slow MA (200+) - Focuses on longer-term trends with fewer but potentially stronger signals.
    """

    n1 = 5
    n2 = 10
    # optimize 定義KD週期 for 3703
    # fastk_period=9
    # slowk_period=3
    # slowd_period=4
    # optimize 定義KD週期 for 2371
    fastk_period = 9
    slowk_period = 3
    slowd_period = 2

    def init(self):
        close = self.data.Close
        self.sma1 = self.I(SMA, close, self.n1)
        self.sma2 = self.I(SMA, close, self.n2)
        self.slowk, self.slowd = self.I(
            talib.STOCH,
            self.data.High,
            self.data.Low,
            self.data.Close,
            self.fastk_period,
            self.slowk_period,
            self.slowd_period,
        )

    def next(self):
        if crossover(self.sma1, self.sma2) and crossover(self.slowk, self.slowd):
            self.buy()
            # MA快線低於慢線 並且 K < D
        elif crossover(self.sma2, self.sma1) and crossover(self.slowd, self.slowk):
            if len(self.trades) > 0:
                self.trades[0].close()


# 短均線>長均線做多，短均線<長均線出場
class TwoMA(Strategy):
    # 定義長短天期均線參數
    n1 = 20
    n2 = 60

    # 先算好均線(技術指標)價格
    def init(self):
        self.sma1 = self.I(SMA, self.data.Close, self.n1)
        self.sma2 = self.I(SMA, self.data.Close, self.n2)

    # 一次推進一根 K 棒
    def next(self):
        # 短天期均線較長天期均線高，隔日開盤價買進
        if self.sma1 > self.sma2 and (not self.position.is_long):
            self.buy()
        # 短天期均線較長天期均線低，隔日開盤價賣出
        elif self.sma2 > self.sma1:
            self.position.close()


class RsiMacd(Strategy):
    """
        Fast Moving Average (EMA1):

        Range: Typically between 12 and 26 days.
        Impact: A shorter period reacts faster to price changes, leading to earlier signals (potentially more frequent but also more susceptible to whipsaws).

    Slow Moving Average (EMA2):

        Range: Typically between 26 and 52 days.
        Impact: A longer period reacts slower to price changes but provides a smoother signal, potentially reducing whipsaws.

    Signal Line (EMA of MACD):

        Range: Typically between 5 and 9 days.
        Impact: A shorter period reacts faster to confirmations/rejections of MACD crossovers, while a longer period provides slower but potentially more reliable confirmations.
    """

    # optimize 定義參數 for 2371
    fastPeriod = 12
    slowPeriod = 26
    macdPeriod = 5
    n1 = 14  # rsi 要算幾天的 RSI 值
    n2 = 26  # rsi 低於多少買進
    n3 = 89  # rsi 高於多少賣出

    # 先算好技術指標價格
    def init(self):
        self.rsi = self.I(talib.RSI, self.data.Close, self.n1)
        self.macd, self.macdsignal, self.macdhist = self.I(
            talib.MACD,
            self.data.Close,
            self.fastPeriod,
            self.slowPeriod,
            self.macdPeriod,
        )

    # 一次推進一根 K 棒
    def next(self):
        # 收盤 rsi低於 30 ，隔日開盤價買進
        if (
            rsi_buy(self.rsi, self.n2)
            and crossover(self.macd, self.macdsignal)
            and not (self.position.is_long)
        ):
            self.buy()

        # 收盤 rsi高於 50 ，隔日開盤價賣出
        if (
            rsi_sell(self.rsi, self.n3)
            and crossover(self.macdsignal, self.macd)
            and not (self.position.is_short)
        ):
            self.position.close()


class Rsi(Strategy):
    # optimize 定義參數 for 2371
    rsi_window = 14  # rsi 要算幾天的 RSI 值
    upper_bound = 50  # rsi 低於多少買進
    lower_bound = 30  # rsi 高於多少賣出

    # 先算好技術指標價格
    def init(self):
        # diff timeframe
        self.daily_rsi = self.I(talib.RSI, self.data.Close, self.rsi_window)
        self.weekly_rsi = resample_apply(
            "W-FRI", talib.RSI, self.data.Close, self.rsi_window
        )

    # 一次推進一根 K 棒
    def next(self):
        price = self.data.Close[-1]
        # 收盤 rsi低於 30 ，隔日開盤價買進
        if (
            crossover(self.daily_rsi, self.upper_bound and self.weekly_rsi[-1])
            > self.upper_bound
        ):
            if self.position.is_long:
                print(self.position.size)
                print(self.position.pl_pct)
                self.position.close()
                self.sell()

        # 收盤 rsi高於 50 ，隔日開盤價賣出
        # elif self.lower_bound > self.daily_rsi[-1]:
        elif (
            crossover(self.lower_bound, self.daily_rsi)
            and self.weekly_rsi[-1] < self.lower_bound
            and self.daily_rsi[-1] < self.weekly_rsi[-1]
            and self.daily_rsi[-2] < self.weekly_rsi[-1]
        ):
            if self.position.is_short or not self.position:
                self.position.close()
                self.buy(size=1, tp=1.15 * price, sl=0.95 * price)


class OneMA(Strategy):
    n1 = 60  # 預設的均線參數

    def init(self):  # 初始化會用到的參數和指標，告知要如何計算
        self.sma1 = self.I(SMA, self.data.Close, self.n1)

    def next(self):  # 回測的時候每一根K棒出現什麼狀況要觸發進出場
        # 如果收盤價>sma1(也就是60ma)，而且目前沒有多單部位
        if (self.data.Close > self.sma1) and (not self.position.is_long):
            self.buy()  # 做多
        # 如果收盤價<sma1(也就是60ma)
        elif self.data.Close < self.sma1:
            self.position.close()  # 部位出場
            # 如果要做空就用self.sell()


def indicator(data):
    # data is going to be our OHLCV
    # data.Close.s -> pd series
    # help(ta.bbands) in cmd line
    bbands = ta.bbands(close=data.Close.s, std=1)
    # print(bbands.to_numpy)
    return bbands.to_numpy().T[:3]  # get 1st 3 returned values


class BbandStrategy(Strategy):
    def init(self):
        # return np.ndarray
        self.bbands = self.I(indicator, self.data)

    def next(self):
        lower_band = self.bbands[0]  #
        upper_band = self.bbands[2]

        if self.position:
            if self.data.Close[-1] > upper_band[-1]:
                self.position.close()
        else:
            if self.data.Close[-1] < lower_band[-1]:
                self.buy()


def indicator(data):
    # pandas series
    return data.Close.s.pct_change(periods=7) * 100


class MomentumStrategy(Strategy):
    small_threshold = 0
    large_threshold = 3  # 3%

    def momentum(self, data):
        return data.pct_change(periods=7).to_numpy() * 100

    def init(self):
        self.pct_change_long = resample_apply("1h", indicator, self.data.Close.s)
        # 10m
        self.pct_change_short = resample_apply("10T", indicator, self.data.Close.s)
        # self.pct_change = self.I(indicator, self.data)
        print(self.pct_change)

    def next(self):
        # take most recent value
        change_long = self.pct_change_long[-1]
        change_short = self.pct_change_long[-1]
        if self.position:
            # check whether we should close
            if self.position.is_long and change_short < self.small_threshold:
                self.position.close()
            elif self.position.is_short and change_short > -1 * self.small_threshold:
                self.position.close()
        else:
            # check whether we should go long/short
            if change_long > self.large_threshold and change_short > self.small_threshold:
                price = self.data.Close[-1]
                # stopLoss, takeProfit
                self.buy(size=1, sl=price - 10, tp=price + 20)
            elif change_long < -1*self.large_threshold and change_short < -1*self.small_threshold:
                self.sell()

class Strat(TrailingStrategy):
    def init(self):
        super().init()
        super().set_trailing_sl(5)

    def next(self):
        super().next()
        if self.position:
            pass
        else:
            price = self.data.Close[-1]
            # stopLoss, takeProfit
            self.buy(size=1, sl=price - 10, tp=price + 20)
