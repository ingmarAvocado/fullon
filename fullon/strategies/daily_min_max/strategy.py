"""
Describe strategy
"""
import arrow
from typing import Optional
from libs.strategy import loader
import pandas


#from libs.strategy import strategy as strat

# logger = log.setup_custom_logger('pairtrading1a', settings.STRTLOG)

strat = loader.strategy


class Strategy(strat.Strategy):
    """description"""

    params = (
        ('days', 10),
        ('pre_load_bars', 11),
        ('feeds', 3)
    )

    def local_init(self):
        """description"""
        self.verbose = False
        self.order_cmd = "spread"
        self.p.timeout = None
        self.p.trailing_stop = None
        self.p.stop_loss = None

    def local_next(self):
        """ description """
        if self.entry_signal[0]:
            self.open_pos(0)

    """
    ''' For UTC '''
    def set_indicators_df(self):
        if not self.indicators_df.empty:
            if self.indicators_df.index[-1] == self.datas[2].dataframe.index[-1]:
                return
        # Proceed to update indicators_df with the new data
        self.indicators_df = self.datas[2].dataframe[['close']].copy()

        # Calculate the max and min of the past self.p.days days, including today
        self.indicators_df['max_10d'] = self.indicators_df['close'].rolling(window=self.p.days).max()
        self.indicators_df['min_10d'] = self.indicators_df['close'].rolling(window=self.p.days).min()

        # Call _set_signals to determine entry and exit points
        self._set_signals()

        # Drop rows with NaN values that may have been created during the rolling calculation
        self.indicators_df = self.indicators_df.dropna()
        print(self.indicators_df)
    """

    ''' For CET '''
    def set_indicators_df(self):
        if not self.indicators_df.empty:
            if self.indicators_df.index[-1] == self.datas[2].dataframe.index[-1]:
                return
        daily_df = self.datas[2].dataframe[['close']].copy()
        hourly_df = self.datas[1].dataframe[['close']].copy()

        # Filter hourly data to only include 22:00 entries
        hourly_22_df = hourly_df[hourly_df.index.hour == 20]
        # Shift the hourly 22:00 dataframe's index by 2 hours
        hourly_22_df.index += pandas.Timedelta(hours=4)
        daily_df['close_CET'] = hourly_22_df['close']

        # Initialize a DataFrame to store the combined data with necessary columns
        self.indicators_df = pandas.DataFrame(index=daily_df.index, columns=['close', 'close_CET', 'max_10d', 'min_10d', 'entry', 'exit'])

        # Update 'close' and 'close_CET_prev_day' in self.indicators_df
        self.indicators_df['close'] = daily_df['close']
        self.indicators_df['close_CET'] = daily_df['close_CET']
        # Calculate 'max_10d' and 'min_10d' using the efficient method
        self.indicators_df['max_10d'] = self.indicators_df['close'].rolling(window=self.p.days).max()
        self.indicators_df['min_10d'] = self.indicators_df['close'].rolling(window=self.p.days).min()
        #self.indicators_df = self.indicators_df.dropna()
        # Adjust 'max_10d' based on 'close_CET'
        self.indicators_df['max_10d'] = self.indicators_df.apply(lambda row: max(row['max_10d'], row['close_CET']), axis=1)
        # Adjust 'min_10d' based on 'close_CET'
        self.indicators_df['min_10d'] = self.indicators_df.apply(lambda row: min(row['min_10d'], row['close_CET']), axis=1)
        self._set_signals()
        self.indicators_df = self.indicators_df.dropna()
        self.indicators_df.index -= pandas.Timedelta(hours=2)

    def _set_signals(self):
        # Reset 'entry' column to False
        self.indicators_df['entry'] = False
        self.indicators_df['exit'] = True
        # Vectorized condition checks for entry signals
        entry_condition = (self.indicators_df['close'] >= self.indicators_df['max_10d']) | \
                          (self.indicators_df['close'] <= self.indicators_df['min_10d'])
        # Apply entry condition
        self.indicators_df['entry'] = entry_condition
        self.indicators_df['exit'] = ~self.indicators_df['entry']

    def set_indicators(self):
        # Use the latest date in the DataFrame's index
        latest_date = self.curtime[1].format('YYYY-MM-DD HH:mm:ss')
        try:
            entry_signal = self.indicators_df.loc[latest_date, 'entry']
            max_10d = self.indicators_df.loc[latest_date, 'max_10d']
            min_10d = self.indicators_df.loc[latest_date, 'min_10d']
            # Set exit signal based on the entry signal
            exit_signal = self.indicators_df.loc[latest_date, 'entry']
        except KeyError:
            entry_signal = False
            exit_signal = True  # Default to True if entry signal cannot be determined
            max_10d = None
            min_10d = None

        # Setting the indicators
        self.set_indicator('entry', entry_signal)
        self.set_indicator('exit', exit_signal)  # Update to include the exit signal
        self.set_indicator('max_10d', max_10d)
        self.set_indicator('min_10d', min_10d)

    def get_entry_signal(self):
        """
        """
        try:
            self.entry_signal[0] = ""
            if self.indicators.entry:
                self.entry_signal[0] = "Buy"
        except KeyError:
            pass

    def local_nextstart(self):
        """ Only runs once, before local_next"""
        self.next_open = self.curtime[0]

    def risk_management(self):
        """
        Handle risk management for the strategy.
        This function checks for stop loss and take profit conditions,
        and closes the position if either of them are met.

        only works when there is a position, runs every tick
        """
        # Check for stop loss
        res = self.check_exit()
        if not res:
            if self.pos[0] > 0 and self.indicators.exit:
                res = self.close_position(feed=0, reason="strategy")
        if res:
            self.next_open = self.time_to_next_bar(feed=1)
            self.entry_signal[0] = ""
            time_difference = (self.next_open.timestamp() - self.curtime[0].timestamp())
            if time_difference <= 60:  # less than 60 seconds
                self.next_open = self.next_open.shift(minutes=self.datas[1].bar_size_minutes)

    def event_in(self) -> Optional[arrow.Arrow]:
        """
        Find the date of the next buy or sell signal based on the current time.
        """
        curtime = pandas.to_datetime(self.next_open.format('YYYY-MM-DD HH:mm:ss'))

        # Filter based on conditions and time
        mask = (self.indicators_df['entry'] == True) \
                & (self.indicators_df.index >= curtime)

        filtered_df = self.indicators_df[mask]

        # Check if the filtered dataframe has any rows
        if not filtered_df.empty:
            return arrow.get(str(filtered_df.index[0]))
        # If the function hasn't returned by this point, simply return None

    def event_out(self) -> Optional[arrow.Arrow]:
        """
        take profit and stop_loss are automatic
        """
        curtime = pandas.to_datetime(self.curtime[1].format('YYYY-MM-DD HH:mm:ss'))

        # Check the position before proceeding
        # Filter based on conditions and time for long exit
        mask = (self.indicators_df['exit'] == True) & (self.indicators_df.index >= curtime)

        filtered_df = self.indicators_df[mask]

        # Check if the filtered dataframe has any rows
        if not filtered_df.empty:
            return arrow.get(str(filtered_df.index[0]))
