from libs import settings
from libs.settings_config import fullon_settings_loader
from libs.models.ohlcv_model import Database as DatabaseO
from libs.models.crawler_model import Database as DatabaseC
from run.crawler_manager import CrawlerManager
import pandas
import arrow
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from decimal import Decimal
import numpy as np

settings.LOG_LEVEL = "logging.INFO"
MEDIAPATH = '/tmp/fullon_sentiment.png'
# first lets load into pandas pythons ohlcv


def evaluate_sentiment(df, period=1, long=2, short=1.2, field='score'):
    """
    Add a new column 'sentiment_correct' to the DataFrame to indicate if the sentiment was correct.
    Parameters:
    df (pd.DataFrame): The input DataFrame.
    period (int): Number of periods to look ahead.
    long (float): Percentage threshold for bullish sentiment.
    short (float): Percentage threshold for bearish sentiment.
    """
    df['sentiment_correct'] = None
    high_sent = 2
    low_sent = -1

    for i in range(len(df) - period):
        sentiment = df.iloc[i][field]
        if not pandas.isna(sentiment):
            current_close = df.iloc[i]['close']
            correct = False
            if sentiment <= high_sent and sentiment >= low_sent:
                pass
            elif sentiment > high_sent:
                # Bullish sentiment, check if future high is above long% in any of the periods
                for j in range(1, period + 1):
                    future_high = df.iloc[i + j]['high']
                    if future_high >= current_close * (1 + long / 100):
                        correct = True
                        break
            elif sentiment < low_sent:
                # Bearish sentiment, check if future low is below short% in any of the periods
                for j in range(1, period + 1):
                    future_low = df.iloc[i + j]['low']
                    if future_low <= current_close * (1 - short / 100):
                        correct = True
                        break
            df.at[df.index[i], 'sentiment_correct'] = correct
    return df


def create_dataframe(rows):
    """
    Creates a DataFrame from the input data
    :param rows: The data to be saved
    """
    dataframe = pandas.DataFrame(rows)
    # Rename the columns
    dataframe.rename(columns={0: "date",
                              1: "open",
                              2: "high",
                              3: "low",
                              4: "close",
                              5: "volume"}, inplace=True)
    # Set the index to the 'date' column
    dataframe.set_index("date", inplace=True)
    # Get the columns to convert to numeric
    columns_to_convert = dataframe.columns.difference(['date'])
    # Convert the columns to numeric
    dataframe[columns_to_convert] = dataframe[columns_to_convert].apply(pandas.to_numeric)
    dataframe.index = pandas.to_datetime(dataframe.index)
    return dataframe


with DatabaseO(exchange='kraken', symbol='BTC/USD') as dbase:
    rows = dbase.fetch_ohlcv(table='kraken_btc_usd.trades',
                             compression=1,
                             period='Day',
                             fromdate=arrow.get('2023-01-01').datetime,
                             todate=arrow.utcnow().datetime)

df_ohlcv = create_dataframe(rows=rows)


'''
with DatabaseC() as dbase:
    rows = dbase.get_average_scores(period='day', compression=1, engine='openai', account='PeterLBrandt')

df = pandas.DataFrame(rows, columns=['timestamp', 'score'])

df_openai = df.set_index('timestamp', drop=True)
#df_openai['sma7'] = df_openai['score'].rolling(window=7).mean()
#df_openai['sma14'] = df_openai['score'].rolling(window=14).mean()
'''
totals = []
with DatabaseC() as dbase:
    rows = dbase.get_average_scores(period='Day', compression=1)

df = pandas.DataFrame(rows, columns=['period', 'openai'])
df_perp = df.set_index('period', drop=True)
#vader_avg = Decimal(df_perp['vader'].mean())
#perplexity_avg = Decimal(df_perp['perplexity'].mean())
openai_avg = Decimal(df_perp['openai'].mean())
#df_perp['vader'] = df_perp['vader'] - vader_avg
#df_perp['perplexity'] = df_perp['perplexity'] - perplexity_avg
df_perp['openai'] = df_perp['openai'] - openai_avg
#df_perp['vader_sma1'] = df_perp['vader'].rolling(window=7).mean()
#df_perp['vader_sma2'] = df_perp['vader'].rolling(window=14).mean()
df_perp['openai_sma1'] = df_perp['openai'].rolling(window=18).mean()
df_perp['openai_sma2'] = df_perp['openai'].rolling(window=21).mean()
#df_perp['perplexity_sma1'] = df_perp['perplexity'].rolling(window=7).mean()
#df_perp['perplexity_sma2'] = df_perp['perplexity'].rolling(window=14).mean()
#engines = ['vader', 'perplexity', 'openai']  # List of engine columns
engines = ['openai']  # List of engine columns
#df_perp['score'] = df_perp[engines].mean(axis=1)
df_perp['score'] = df_perp['openai']
df_perp['sma1'] = df_perp['score'].rolling(window=21).mean()
df_perp['sma2'] = df_perp['score'].rolling(window=50).mean()



df_ohlcv.index = pandas.to_datetime(df_ohlcv.index)
df_perp.index = pandas.to_datetime(df_perp.index)
df_ohlcv_close = df_ohlcv[['close']]
#df_perp_smas = df_perp[['openai', 'vader', 'perplexity', 'score', 'sma1', 'sma2']]
df_perp_smas = df_perp[['openai', 'score', 'sma1', 'sma2']]
merged_df = df_ohlcv.join(df_perp_smas, how='inner')

N = 11
merged_df['low_next'] = merged_df['low'].rolling(window=N, min_periods=1).min().shift(-N+1)
merged_df['high_next'] = merged_df['high'].rolling(window=N, min_periods=1).max().shift(-N+1)
merged_df['close_next'] = merged_df['close'].shift(-N)


merged_df['price_down'] = np.where(
    merged_df['sma2'] >= 0,
    100 - (merged_df['close'] / merged_df['low_next']) * 100,
    100 - (merged_df['low_next'] / merged_df['close']) * 100
)

merged_df['price_up'] = np.where(
    merged_df['sma2'] >= 0,
    ((merged_df['high_next'] / merged_df['close']) * 100) - 100,
    ((merged_df['close'] / merged_df['high_next']) * 100) - 100
)




'''

for i in range(1,35):
    merged_df2 = merged_df.copy()
    merged_df2[f'close_shifted_{i}d'] = merged_df2['close'].shift(-i)
    merged_df2 = merged_df2.dropna()
    correlation_shifted = merged_df2[[f'close_shifted_{i}d', 'openai', 'score', 'sma1', 'sma2']].corr()
    print(f"Days ahead {i}")
    print(correlation_shifted)


n_values = [16, 17, 18, 19, 20]
x_values = [4.5, 4.75, 5, 5.5, 6, 6.6, 7]
y_values = [1, 1.25, 1.5, 1.75, 2]

'''


'''
result = df_ohlcv.join(df_perp)
rates = []
for n in n_values:
    for x in x_values:
        for y in y_values:
            try:
                _result = evaluate_sentiment(result.copy(), period=n, long=x, short=y, field='sma1')
                true_count = _result['sentiment_correct'].sum()
                false_count = _result['sentiment_correct'].count() - true_count  # Total - True = False
                rate = true_count / (false_count + true_count)
                # Print the result
                if rate > .59:
                    print(f"Period ({n}) Long ({x}) Short ({y}): {rate:.2f}")
                # Append the rate to the list
                rates.append(rate)
            except Exception as e:
                print(f"Error processing Period ({n}) Long ({x}) Short ({y}): {e}")
finrate = sum(rates) / len(rates)
print("f: ", finrate)
'''

# Create the figure and axes
sns.set_theme(style="whitegrid")
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)  # Two subplots, sharing the x-axis

# Plot 'close' on the first subplot
ax1.plot(df_ohlcv.index, df_ohlcv['close'], color='tab:blue', label='Close')
ax1.set_ylabel('Price', color='tab:blue')
ax1.tick_params(axis='y', labelcolor='tab:blue')
ax1.legend(loc='upper left')
to_date = arrow.utcnow().format('YYYY-MM-DD')

ax1.set_title(f"Price and Sentiment Analysis BTC/USD until opening of {to_date}")

# Plot 'score' on the second subplot
#ax2.plot(df_perp.index, df_perp['vader_sma1'], color='tab:blue', label='Sentiment1 openai')
#ax2.plot(df_perp.index, df_perp['openai_sma1'], color='tab:purple', label='Sentiment1 perp')
#ax2.plot(df_perp.index, df_perp['perplexity_sma1'], color='tab:green', label='Sentiment1 vader')
ax3.plot(df_perp.index, df_perp['score'], color='tab:green', label='Avg Scores')
ax3.set_ylabel('Sentiment', color='tab:gray')
ax3.axhline(0, color='red', linestyle='--', linewidth=1, label='Neutral Sentiment')
ax3.legend(loc='upper left')
ax2.plot(df_perp.index, df_perp['sma1'], color='tab:cyan', label='SMA21 Avg Scores')
ax2.plot(df_perp.index, df_perp['sma2'], color='tab:orange', label='SMA50 Avg Scores')
ax2.axhline(0, color='red', linestyle='--', linewidth=1, label='Neutral Sentiment')
ax2.set_ylabel('Sentiment', color='tab:red')
ax2.tick_params(axis='y', labelcolor='tab:red')
ax2.legend(loc='upper left')

# Format the x-axis dates
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%y-%m-%d'))
ax2.tick_params(axis='x', labelsize=8)  # Adjust the font size for the x-axis

# Format the x-axis dates
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%y-%m-%d'))
ax3.tick_params(axis='x', labelsize=8)  # Adjust the font size for the x-axis

plt.xticks(rotation=45, ha='right')
# how do i plot rigt here instead of saving the i media

#fig.savefig(MEDIAPATH)
plt.show()
plt.close(fig)
