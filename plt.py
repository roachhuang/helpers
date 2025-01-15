import pandas as pd
import matplotlib.pyplot as plt


def plt_kbar(kbar: pd.DataFrame):
    # Convert dictionary to DataFrame
    df = pd.DataFrame(kbar)
    # df['time'] = pd.to_datetime(df['time'])
    # Set the time column as the index for the DataFrame
    # df.set_index('time', inplace=True)

    # # Convert timestamps to datetime (assuming milliseconds)
    # df['ts'] = pd.to_datetime(df['ts'], unit='ms')

    # # Set time column as the index
    # df.set_index('ts', inplace=True)
    # Set labels for the axes

    # Plot the closing price
    # plt.plot(df['Close'])
    ax = df["Close"].plot(title="Stock prices", fontsize=12)
    # Rotate x-axis labels for better readability if many data points
    ax.set_xticklabels(ax.get_xticks(), rotation=45)
    ax.set_xlabel("Time")
    ax.set_ylabel("Closing Price")
    ax.legend(loc="upper left")

    # plt.show()
    return ax


"""
def plot_stats(data_full, stats):
    equity_curve=stats._equity_curve
    aligned_data = data_full.reindex(equity_curve.index)

    bt = Backtest(aligned_data, strat.MomentumStrategy, cash=100000, commission=0.002)
    bt.plot(result=stats)
"""


def plt_data(df, title="Stock prices"):
    ax = df.plot(title=title, fontsize=12)
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    plt.ylim(df.min().min(), df.max().max())  # Ensure y-axis uses the full range
    plt.show()  # must be called to show plots in some env


def normalize_data(df):
    return df / df[0, :]


"""
# Sample time series data
dates = pd.date_range("20230101", periods=6)
data = {"Temperature": [22, 24, 27, 21, 20, 19]}
df = pd.DataFrame(data, index=dates)
print(df)
"""
# df['col1','col2'].plot()


# Plot the data
def plt_signal(df, buy_signals, sell_signals):
    plt.figure(figsize=(14, 7))
    plt.plot(df["Date"], df["Close"], label="Closing Price", color="blue")
    plt.scatter(
        buy_signals["Date"],
        buy_signals["Close"],
        color="green",
        marker="^",
        label="Buy",
        s=100,
    )
    plt.scatter(
        sell_signals["Date"],
        sell_signals["Close"],
        color="red",
        marker="v",
        label="Sell",
        s=100,
    )


def plt_pred_vs_actual(preds, actual):
    # Adding labels and title
    # plt.xlabel("Date")
    # plt.ylabel("Price")
    # plt.title("Stock Closing Price with Buy and Sell Points")
    # # plt.legend()
    # plt.grid()

    # Plot actual vs. predicted values
    plt.figure(figsize=(12, 6))
    plt.plot(actual, label="Actual", color="blue")
    plt.plot(preds, label="Predicted", color="orange")
    plt.title("Actual vs Predicted Stock Prices")
    plt.xlabel("Time")
    plt.ylabel("Scaled Price")
    plt.legend()
    plt.show()


def plt_MACD(df):
    ax = df["Close"].plot(
        legend=True, xlabel="time", ylabel="price", title="Stock prices", fontsize=12
    )
    df["MACD"].plot(legend=True, ax=ax)
    df["Signal"].plot(legend=True, ax=ax)
    df["MACD_Hist"].plot(legend=True, ax=ax)
    plt.show()


def plt_scatter(df):
    for stock in df.columns:
        plt.scatter(x=df.index.values, y=df[stock])
    plt.show()
