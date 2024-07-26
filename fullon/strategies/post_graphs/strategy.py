"""
Describe strategy
"""
from libs.strategy import loader
import time
from libs.database import Database
import pandas
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from libs.messaging.x import Messenger
import arrow
from decimal import Decimal

strat = loader.strategy
MEDIAPATH = '/tmp/fullon_sentiment.png'


class Strategy(strat.Strategy):
    """description"""

    params = (
        ('pre_load_bars', 300),
        ('feeds', 2),
    )

    def local_init(self):
        """description"""
        return None

    def local_next(self):
        """ description """
        self.count = 0
        if self.new_candle[1]:
            self.plot_indicators()
            msg = Messenger()
            txt = 'Automated update on Bitcoin Sentiment. Any suggestions are welcome!'
            msg.post(post=txt, media_path=MEDIAPATH)
        time.sleep(3)

    def set_indicators_df(self):
        """
        builds indicators_df
        """
        # base dataframe with date as index, close and volume columns
        self.indicators_df = self.datas[1].dataframe[['close', 'volume']].copy()
        # now lets get super scores
        with Database() as dbase:
            rows = dbase.get_average_scores(period='day')

        scores_df = pandas.DataFrame(rows, columns=['period', 'openai'])
        scores_df = scores_df.set_index('period', drop=True)
        openai_avg = Decimal(scores_df['openai'].mean())
        scores_df['openai'] = scores_df['openai'] - openai_avg
        scores_df['score'] = scores_df['openai']
        scores_df['sma1'] = scores_df['score'].rolling(window=21).mean()
        scores_df['sma2'] = scores_df['score'].rolling(window=50).mean()
        self.indicators_df = self.indicators_df.merge(scores_df, how='left', left_index=True, right_index=True)

    def plot_indicators(self):
        """
        Plots close and score values with two y-axes, a horizontal line at score 0, and smaller date formats.
        """
        # Ensure that indicators_df is already set up
        if self.indicators_df is None:
            print("Error: indicators_df is not set.")
            return

        sns.set_theme(style="whitegrid")
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)  # Two subplots, sharing the x-axis

        # Plot 'close' on the first subplot
        ax1.plot(self.indicators_df.index, self.indicators_df['close'], color='tab:blue', label='Close')
        ax1.set_ylabel('Price', color='tab:blue')
        ax1.tick_params(axis='y', labelcolor='tab:blue')
        ax1.legend(loc='upper left')
        to_date = arrow.utcnow().format('YYYY-MM-DD')

        ax1.set_title(f"Price and Sentiment Analysis BTC/USD until opening of {to_date}")
        # Plot 'score' on the second subplot
        ax3.plot(self.indicators_df.index, self.indicators_df['score'], color='tab:green', label='Avg Scores')
        ax3.set_ylabel('Sentiment', color='tab:gray')
        ax3.axhline(0, color='red', linestyle='--', linewidth=1, label='Neutral Sentiment')
        ax3.legend(loc='upper left')
        ax2.plot(self.indicators_df.index, self.indicators_df['sma1'], color='tab:cyan', label='SMA21 Avg Scores')
        ax2.plot(self.indicators_df.index, self.indicators_df['sma2'], color='tab:orange', label='SMA50 Avg Scores')
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

        fig.savefig(MEDIAPATH)
        plt.close(fig)
