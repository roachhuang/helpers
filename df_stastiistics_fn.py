import pandas as pd
import matplotlib as plt
import numpy as np


df = pd.DataFrame()
# median refers to the value in the middle when they are all sorted
df.median()
# mathematically std deviation is the dquare root of variance but more intuitively it is a measure of deviation
# from central Value(mean)
df.std()

ax = df["SPY"].plot(title="SPY rolling mean", label="SPY")


# rolling statistics
# compute bb bands
#    1. compute rolling mean
rm = pd.rolling_mean(df["SPY"], window=20)
#    2. compute rolling std deviation
rstd = pd.rolling_std(df["SPY"], window=20)
#     3. computer upper and lower bands
upper_band = rm + rstd * 2
lower_band = rm - rstd * 2

# plot raw spy values, rolling mean and bb bands
upper_band.plot(lable="upper band", ax=ax)
lower_band.plot(label="lower band", ax=ax)


# add rolling mean to same plot
rm.plot(lable="Rolling mean", ax=ax)  # note ax=ax to add it to same plot
upper_band.plot(lable="upper band", ax=ax)
lower_band.plot(lable="lower band", ax=ax)

# add axis lables and legend
ax.set_xlable("Date")
ax.set_ylabel("Price")
ax.legend(loc="upper left")
plt.show()


# histogram chart (bell curve) mean and std deviation (guass distrubition)
symbols = ["SPY", "XOM"]
# df = get_data(symbols, dates)
dr = df.pct_change()
dr["SPY"].hist(bins=20, label="SPY")  # change # of bins to 20
dr["XOM"].hist(bins=20, label="XOM")
ax.legend(loc="upper left")
# showing which stock has more return and volatitiy
plt.show()


# slop !=correlation
# scatterplot SPY vs XOM
dr.plot(kind="scatter", x="SPY", y="XOM")
beta_XOM, alpha_XOM = np.polyfit(dr["SPY"], dr["XOM"], 1)
plt.plot(dr["SPY"], beta_XOM * dr["SPY"] + alpha_XOM, "-", color="r")
plt.show()
# calculate correlation coefficient
print(dr.corr(method="pearson"))
'''
the distribution of daily returns for stocks and market look very similar to a gaussian
if e.g., daily, monthly or yearly return. if they were really gaussian we'd say the returns
were normally distributed. in many fiancial case, we assume the returns are normally distributed.
but this can be dangerous coz it ignores kurtosis or the probability in the tails.

'''


mean = dr["SPY"].mean()
std = dr["SPY"].std()
plt.axvline(mean, color="w", linestyle="dashed", linewidth=2)
plt.axvline(std, color="r", linestyle="dashed", linewidth=2)
plt.axvline(-std, color="w", linestyle="dashed", linewidth=2)
plt.show()

# cumulative returns
df.cumsum()

# pristine data?
# in reality daa is an amalgamation. there might be gaps or msssing data points
# solution: 1. fill forward, fill backward
df.fillna(method="ffill", inplace=True)
df.fillna(method="bfill", inplace=True)
