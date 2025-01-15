import numpy as np


def optim_func(series):
    if series["# Trades"] < 10:
        return -1
    # how to make most money while in the mkt for the least amt of time
    return series["Equity Final [$]"] / series["Exposure Time [%]"]


def rsi(bt):
    return bt.optimize(
        upper_bound=range(50, 85, 5),
        lower_bound=range(10, 45, 5),
        rsi_window=range(10, 45, 2),
        maximize=optim_func,
        # maximize='Sharp Ratio'
        constraint=lambda p: p.lower_bound < p.upper_bound,
        max_tries=100,  # randmoly result got, this is for save time to optimize if u don't have time or pc too slow
        return_heatmap=True,
    )


def momentum(bt):
    return bt.optimize(
        small_threshold=list(np.arange(0, 1, 0.1)),
        large_threshold=list(np.arange(1, 3, 0.2)),
        maximize="Equity Final [$]",
    )


# optimize for 2 ma
# 「結果(目標)」可以是勝率、最後帳戶總淨值、Sharpe Ratio等等
def two_ma(bt):
    return bt.optimize(
        n1=range(5, 10, 15),
        n2=range(10, 20, 40),
        fastk_period=range(9, 14, 1),
        # slowk_period=range(1, 10,1),
        slowd_period=range(2, 5, 1),
        maximize="Equity Final [$]",
    )


def macd(bt):
    return bt.optimize(
        fastPeriod=range(1, 15, 1),
        slowPeriod=range(1, 20, 1),
        macdPeriod=range(1, 15, 1),
        maximize="Equity Final [$]",
        constraint=lambda p: p.fastPeriod < p.slowPeriod,
    )
