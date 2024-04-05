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
        ('entry_hour', 22),
        ('exit_hour', 0),
        ('pre_load_bars', 1),
        ('feeds', 2)
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

    def set_indicators_df(self):
        if not self.indicators_df.empty:
            if self.indicators_df.index[-1] == self.datas[0].dataframe.index[-1]:
                return
        self.indicators_df = self.datas[0].dataframe[['close']].copy().resample('1h').agg({
            'close': 'last',
        })

        self.indicators_df['entry'] = False
        self.indicators_df['exit'] = False
        self._set_signals()

    def _set_signals(self):
        # Set 'entry' to True for rows where the index hour is 22:00
        self.indicators_df.loc[self.indicators_df.index.hour == 22, 'entry'] = True
        # Set 'exit' to True for rows where the index hour is 00:00
        self.indicators_df.loc[self.indicators_df.index.hour == 0, 'exit'] = True

    def set_indicators(self):
        # Use the latest date in the DataFrame's index
        latest_date = self.curtime[1].format('YYYY-MM-DD HH:mm:ss')
        try:
            entry_signal = self.indicators_df.loc[latest_date, 'entry']
            exit_signal = self.indicators_df.loc[latest_date, 'exit']
        except KeyError:
            entry_signal = False
            exit_signal = False

        # Setting the indicators
        self.set_indicator('entry', entry_signal)
        self.set_indicator('exit', exit_signal)  # Update to include the exit signal

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
