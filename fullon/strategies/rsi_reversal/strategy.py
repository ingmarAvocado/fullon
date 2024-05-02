"""
Describe strategy
"""
import arrow
from typing import Optional
from libs.strategy import loader
from libs import log
import pandas
import pandas_ta as ta


logger = log.fullon_logger(__name__)

strat = loader.strategy


class Strategy(strat.Strategy):
    """description"""

    params = (
        ('take_profit', 9),
        ('trailing_stop', 4.5),
        ('timeout', 37),
        ('stop_loss', 4.6),
        ('rsi', 12),
        ('entry', 41),
        ('exit', 70),
        ('pre_load_bars', 30),
        ('feeds', 2)
    )

    def local_init(self):
        """description"""
        self.next_open: arrow.Arrow
        self.verbose = False
        self.order_cmd = "spread"
        if self.p.timeout:
            self.p.timeout = self.str_feed[1].bar_size_minutes * self.p.timeout
        if self.p.entry >= self.p.exit:
            logger.error("Entry cannot be greater than exit")
            self.cerebro.runstop()

    def local_next(self):
        """ description """
        if self.entry_signal[0]:
            if self.curtime[0] >= self.next_open:
                self.increase_position(0)
                self.crossed_lower = False
                self.crossed_upper = False

    def set_indicators_df(self):
        if not self.indicators_df.empty:
            if self.indicators_df.index[-1] == self.str_feed[1].dataframe.index[-1]:
                return
        self.indicators_df = self.str_feed[1].dataframe[['close']].copy()
        self.indicators_df['rsi'] = ta.rsi(self.indicators_df['close'], length=self.p.rsi)
        self._set_signals()
        next_date = arrow.get(self.indicators_df.index[-1]).shift(minutes=self.str_feed[1].bar_size_minutes)
        self.indicators_df.loc[next_date.format('YYYY-MM-DD HH:mm:ss')] = None
        new_index = self.indicators_df.index.to_series().shift(-1).ffill().astype('datetime64[ns]')
        self.indicators_df.index = new_index
        self.indicators_df = self.indicators_df.dropna()

    def _set_signals(self):
        buffer_zone = 3  # Adding a buffer zone of x RSI points

        # Create new columns for entry and exit signals, initialized to False
        self.indicators_df['entry'] = False
        self.indicators_df['exit'] = False

        # Conditions for RSI thresholds including buffer zone
        rsi_previously_below_entry = self.indicators_df['rsi'].shift(1) < self.p.entry
        rsi_cross_back_entry = self.indicators_df['rsi'] >= self.p.entry + buffer_zone  # Buffer zone added

        # Define conditions for long entry and exit signals
        long_entry_cond = rsi_previously_below_entry & rsi_cross_back_entry
        long_exit_cond = self.indicators_df['rsi'] > self.p.exit

        # Update the DataFrame with the entry and exit signals based on the conditions
        self.indicators_df.loc[long_entry_cond, 'entry'] = True
        self.indicators_df.loc[long_exit_cond, 'exit'] = True

    def set_indicators(self):
        current_time = self.curtime[1].format('YYYY-MM-DD HH:mm:ss')
        fields = ['entry', 'exit', 'rsi']
        self._this_indicators(current_time=current_time, fields=fields)

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
                    self.entry_signal[0] = "Buy"
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
            if self.pos[0] > 0 and self.indicators.exit:
                res = self.reduce_position(feed=0, reason="strategy")
        if res:
            self.next_open = self.time_to_next_bar(feed=1)
            self.entry_signal[0] = ""
            time_difference = (self.next_open.timestamp() - self.curtime[0].timestamp())
            if time_difference <= 60:  # less than 60 seconds
                self.next_open = self.next_open.shift(minutes=self.str_feed[1].bar_size_minutes)
