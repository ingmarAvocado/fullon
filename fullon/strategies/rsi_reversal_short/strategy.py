"""
Describe strategy
"""
import arrow
from typing import Optional
from libs.strategy import loader
import pandas
import pandas_ta as ta


#from libs.strategy import strategy as strat

# logger = log.setup_custom_logger('pairtrading1a', settings.STRTLOG)

strat = loader.strategy


class Strategy(strat.Strategy):
    """description"""

    params = (
        ('take_profit', 9),
        ('trailing_stop', 4.5),
        ('timeout', 37),
        ('stop_loss', 4.6),
        ('rsi', 12),
        ('entry', 64),
        ('exit', 62),
        ('pre_load_bars', 30),
        ('feeds', 2)
    )

    next_open: arrow.Arrow

    def local_init(self):
        """description"""
        self.verbose = False
        self.order_cmd = "spread"
        if self.p.timeout:
            self.p.timeout = self.datas[1].bar_size_minutes * self.p.timeout
        #if self.p.exit >= self.p.entry:
        #    self.cerebro.runstop()

    def local_next(self):
        """ description """
        if self.entry_signal[0]:
            if self.curtime[0] >= self.next_open:
                self.open_pos(0)
                self.crossed_lower = False
                self.crossed_upper = False

    def set_indicators_df(self):
        if not self.indicators_df.empty:
            if self.indicators_df.index[-1] == self.datas[1].dataframe.index[-1]:
                return
        self.indicators_df = self.datas[1].dataframe[['close']].copy()
        # Compute RSI
        self.indicators_df['rsi'] = ta.rsi(self.indicators_df['close'], length=self.p.rsi)

        self._set_signals()
        self.indicators_df = self.indicators_df.dropna()

    def _set_signals(self):
        # Existing code for entry and exit signals initialization
        self.indicators_df['entry'] = False
        self.indicators_df['exit'] = False

        # Conditions for long positions (existing code)
        # ...

        # Define condition for RSI previously rising above the exit threshold
        rsi_previously_above_entry = self.indicators_df['rsi'].shift(1) > self.p.entry

        # Define condition for RSI crossing back down through the exit threshold
        rsi_cross_back_entry = self.indicators_df['rsi'] <= self.p.entry

        # Define conditions for short entry and exit signals
        short_entry_cond = rsi_previously_above_entry & rsi_cross_back_entry
        short_exit_cond = self.indicators_df['rsi'] < self.p.exit

        # Update the DataFrame with the short entry signals based on the conditions
        self.indicators_df.loc[short_entry_cond, 'entry'] = True
        self.indicators_df.loc[short_exit_cond, 'exit'] = True

    def set_indicators(self):
        try:
            short_entry = self.indicators_df.loc[self.curtime[1].format('YYYY-MM-DD HH:mm:ss'), 'entry']
        except KeyError:
            short_entry = None
        try:
            short_exit = self.indicators_df.loc[self.curtime[1].format('YYYY-MM-DD HH:mm:ss'), 'exit']
        except KeyError:
            short_exit = None
        self.set_indicator('rsi', self.indicators_df.loc[self.curtime[1].format('YYYY-MM-DD HH:mm:ss'), 'rsi'])
        self.set_indicator('entry', short_entry)
        self.set_indicator('exit', short_exit)

    def local_nextstart(self):
        """ Only runs once, before local_next"""
        self.next_open = self.curtime[0]

    def get_entry_signal(self):
        """
        blah
        """
        try:
            if self.curtime[0] >= self.next_open:
                self.entry_signal[0] = ""
                if self.indicators.entry:
                    self.entry_signal[0] = "Sell"
        except KeyError:
            pass

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
            if self.pos[0] != 0 and self.indicators.exit:
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
