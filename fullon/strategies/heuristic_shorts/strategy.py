"""
Describe strategy
"""
from functools import total_ordering
from multiprocessing import Value
import backtrader as bt
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
        ('rsi', 14),
        ('rsi_entry', 45),
        ('rsi_exit', 45),
        ('rsi_weight', 4),
        ('rsi_sma', 18),
        ('rsi_sma_weight', 1),
        ('macd_entry', -1),
        ('macd_exit', -2),
        ('macd_weight', 1),
        ('vwap_entry', -2),
        ('vwap_exit', -2),
        ('vwap_weight', 1),
        ('pre_load_bars', 50),
        ('entry', 18),
        ('exit', 56),
        ('ema', 30),
        ('feeds', 2)
    )

    next_open: arrow.Arrow

    def local_init(self):
        """description"""
        self.verbose = False
        self.order_cmd = "spread"
        if self.p.timeout:
            self.p.timeout = self.datas[1].bar_size_minutes * self.p.timeout
        total_weights = self.p.rsi_weight + self.p.macd_weight + self.p.vwap_weight + self.p.rsi_sma_weight
        self.myentry = total_weights * self.p.entry/100
        self.myexit = total_weights * self.p.exit/100
        if self.p.rsi_entry > self.p.rsi_exit:
            self.cerebro.runstop()

    def local_next(self):
        """ description """
        if self.entry_signal[0]:
            if self.curtime[0] >= self.next_open:
                self.open_pos(0)
                self.indicators_df.loc[self.curtime[1].format('YYYY-MM-DD HH:mm:ss'), 'exit'] = False

    def set_indicators_df(self):
        if not self.indicators_df.empty:
            if self.indicators_df.index[-1] == self.datas[1].dataframe.index[-1]:
                return
        # Fetch required data
        self.indicators_df = self.datas[1].dataframe[['open', 'high', 'low', 'close', 'volume']].copy()
        self.indicators_df['ema'] = self.indicators_df['close'].ewm(span=self.p.ema, adjust=False).mean()

        # Compute RSI
        self.indicators_df['rsi'] = ta.rsi(self.indicators_df['close'], length=self.p.rsi)
        self.indicators_df['rsi_sma'] = self.indicators_df['rsi'].rolling(window=int(self.p.rsi_sma)).mean()
        # Compute MACD
        macd = ta.macd(self.indicators_df['close'])
        self.indicators_df['macd'] = macd['MACD_12_26_9']
        self.indicators_df['macdsignal'] = macd['MACDs_12_26_9']
        self.indicators_df['macd_histo'] = self.indicators_df['macd'] - self.indicators_df['macdsignal']
        self.indicators_df['macd_histo'] = self.indicators_df['macd_histo'] / 10

        # vwap
        self.indicators_df['vwap'] = ta.vwap(high=self.indicators_df['high'],
                                             low=self.indicators_df['low'],
                                             close=self.indicators_df['close'],
                                             volume=self.indicators_df['volume'])
        self.indicators_df['vwap_diff'] = (self.indicators_df['close'] - self.indicators_df['vwap']) / self.indicators_df['vwap'] * 100
        self._set_signals()
        self.indicators_df = self.indicators_df.dropna()

    def _calculate_entry_score(self, row):
        score = 0
        # Add to score based on each indicator and its weight
        score += self.p.rsi_weight * (1 if row['rsi_entry'] else 0)
        score += self.p.macd_weight * (1 if row['macd_entry'] else 0)
        score += self.p.vwap_weight * (1 if row['vwap_entry'] else 0)
        score += self.p.rsi_sma_weight * (1 if row['rsma_entry'] else 0)
        return score

    def _calculate_exit_score(self, row):
        score = 0
        # Add to score based on each indicator and its weight
        score += self.p.rsi_weight * (1 if row['rsi_exit'] else 0)
        score += self.p.macd_weight * (1 if row['macd_exit'] else 0)
        score += self.p.vwap_weight * (1 if row['vwap_exit'] else 0)
        score += self.p.rsi_sma_weight * (1 if row['rsma_exit'] else 0)
        return score

    def _set_signals(self):
        # Create new columns for entry and exit signals, initialized to False
        self.indicators_df['entry'] = False
        self.indicators_df['exit'] = False

        # Define conditions for short entry and exit signals for RSI
        self.indicators_df['rsi_entry'] = (self.indicators_df['rsi'] < self.p.rsi_entry) & (self.indicators_df['rsi'] > 25)
        self.indicators_df['rsi_exit'] = self.indicators_df['rsi'] > self.p.rsi_exit

        self.indicators_df['rsma_entry'] = (self.indicators_df['rsi_sma'] < self.indicators_df['rsi'])
        self.indicators_df['rsma_exit'] = (self.indicators_df['rsi_sma'] > self.indicators_df['rsi'])

        # Define conditions for entry and exit signals by MACD
        self.indicators_df['macd_entry'] = self.indicators_df['macd_histo'] < self.p.macd_entry
        self.indicators_df['macd_exit'] = self.indicators_df['macd_histo'] > self.p.macd_exit

        # define conditions for long entry and exit signals for VWAP
        self.indicators_df['vwap_entry'] = self.indicators_df['vwap_diff'] > self.p.vwap_entry
        self.indicators_df['vwap_exit'] = self.indicators_df['vwap_diff'] < self.p.vwap_exit*-1

        self.indicators_df['entry_score'] = self.indicators_df.apply(self._calculate_entry_score, axis=1)
        self.indicators_df['exit_score'] = self.indicators_df.apply(self._calculate_exit_score, axis=1)

        # Define entry condition based on score
        self.indicators_df['entry'] = (
            (self.indicators_df['entry_score'] > self.myentry) &
            (self.indicators_df['close'] < self.indicators_df['ema'])
        )
        self.indicators_df['exit'] = self.indicators_df['exit_score'] >= self.myexit

    def set_indicators(self):
        """
        """
        current_time = self.curtime[1].format('YYYY-MM-DD HH:mm:ss')
        for indicator in ['entry', 'exit']:
            try:
                value = self.indicators_df.loc[current_time, indicator]
                self.set_indicator(indicator, value)
            except KeyError:
                self.set_indicator(indicator, False)

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
            self.next_open = self.time_to_next_bar(feed=1).shift(minutes=0)
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
