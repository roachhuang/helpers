import yfinance as yf
import pandas as pd

# Download data from yahoo, get 3-4yrs
def download_data(symbol, interval, start, end)->pd.DataFrame:
    stock = yf.Ticker(symbol)

    # valid periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    # valid intervals: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo
    # df.ta.ticker(symbol, period, interval)

    # By default, adjustments are enabled. to do: try period='max'

    # yf.download - Downloads historical price data for multiple tickers at once

    # yf.ticker.history - Downloads historical price data for a single ticker
    # (1m data is only for available for last 7 days, and data interval <1d for the last 60 days) index = Datetime if interval < 1d
    data = stock.history(interval=interval, start=start, end=end)
    return data

