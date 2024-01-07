"""
Describe strategy
"""
import arrow
from typing import Optional
from libs.strategy import loader
from libs import log
import pandas
import pandas_ta as ta


#from libs.strategy import strategy as strat

logger = log.fullon_logger(__name__)

strat = loader.strategy


class Strategy(strat.Strategy):
    """description"""

    params = (
        ('rsi', 14),
        ('rsi_entry', 65),
        ('rsi_exit', 60),
        ('rsi_weight', 3),
        ('cmf', 18),
        ('cmf_entry', 11),
        ('cmf_exit', 5),
        ('cmf_weight', 1),
        ('vwap_entry', 0.2),
        ('vwap_exit', 0.4),
        ('vwap_weight', 4),
        ('obv', 18),
        ('obv_entry', 1.4),
        ('obv_exit', 0.8),
        ('obv_weight', 3),
        ('macd_entry', 3),
        ('macd_exit', 0),
        ('macd_weight', 2),
        ('stoch_entry', 55),
        ('stoch_exit', 50),
        ('stoch_weight', 4),
        ('pre_load_bars', 200),
        ('entry', 16),
        ('exit', 41),
        ('ema', 21),
        ('feeds', 2)
    )

    next_open: arrow.Arrow

    def local_init(self):
        """description"""
        self.verbose = False
        self.order_cmd = "spread"
        if self.p.timeout:
            self.p.timeout = self.datas[1].bar_size_minutes * self.p.timeout
        if self.p.rsi_exit >= self.p.rsi_entry:
            self.cerebro.runstop()
        total_weights = self.p.rsi_weight + self.p.cmf_weight
        total_weights += self.p.vwap_weight + self.p.obv_weight
        total_weights += self.p.macd_weight + self.p.stoch_weight
        self.myentry = total_weights * self.p.entry/100
        self.myexit = total_weights * self.p.exit/100

    def local_next(self):
        """ description """
        if self.entry_signal[0]:
            if self.curtime[0] >= self.next_open:
                if self.open_pos(0):
                    self.indicators_df.loc[self.curtime[1].format('YYYY-MM-DD HH:mm:ss'), 'exit'] = False
                else:
                    logger.error("Could not open position when i should have")

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
            self.next_open = self.time_to_next_bar(feed=1).shift(minutes=240*0)
            self.entry_signal[0] = ""
            time_difference = (self.next_open.timestamp() - self.curtime[0].timestamp())
            if time_difference <= 60:  # less than 60 seconds
                self.next_open = self.next_open.shift(minutes=self.datas[1].bar_size_minutes)

    def set_indicators_df(self):
        if not self.indicators_df.empty:
            if self.indicators_df.index[-1] == self.datas[1].dataframe.index[-1]:
                return
        # Fetch required data
        self.indicators_df = self.datas[1].dataframe[['open', 'high', 'low', 'close', 'volume']].copy()
        self.indicators_df['ema'] = self.indicators_df['close'].ewm(span=self.p.ema, adjust=False).mean()

        # Compute RSI
        self.indicators_df['rsi'] = ta.rsi(self.indicators_df['close'], length=self.p.rsi)
        # Compute MACD
        macd = ta.macd(self.indicators_df['close'])
        self.indicators_df['macd'] = macd['MACD_12_26_9']
        self.indicators_df['macdsignal'] = macd['MACDs_12_26_9']
        self.indicators_df['macd_histo'] = self.indicators_df['macd'] - self.indicators_df['macdsignal']
        self.indicators_df['macd_histo'] = self.indicators_df['macd_histo'] / 10

        # Compute Stochastic Oscillator
        stochastic = ta.stoch(self.indicators_df['high'], self.indicators_df['low'], self.indicators_df['close'])
        self.indicators_df['stoch_k'] = stochastic['STOCHk_14_3_3']
        self.indicators_df['stoch_d'] = stochastic['STOCHd_14_3_3']
        # Compute Volume Weighted Average Price (VWAP)
        self.indicators_df['vwap'] = ta.vwap(high=self.indicators_df['high'],
                                             low=self.indicators_df['low'],
                                             close=self.indicators_df['close'],
                                             volume=self.indicators_df['volume'])
        self.indicators_df['vwap_diff'] = (self.indicators_df['close'] - self.indicators_df['vwap']) / self.indicators_df['vwap'] * 100
        # Compute On-Balance Volume (OBV)
        self.indicators_df['obv'] = ta.obv(self.indicators_df['close'], self.indicators_df['volume'])
        self.indicators_df['obv_pct_change'] = self.indicators_df['obv'].pct_change() * 100
        self.indicators_df['obv_pct_sma'] = self.indicators_df['obv_pct_change'].rolling(window=int(self.p.obv)).mean()
        # Compute CMF
        self.indicators_df['cmf'] = ta.cmf(self.indicators_df['high'],
                                           self.indicators_df['low'],
                                           self.indicators_df['close'],
                                           self.indicators_df['volume'],
                                           length=self.p.cmf)
        # Remember to update the _set_signals method to include the logic for these new indicators
        self._set_signals()
        self.indicators_df = self.indicators_df.dropna()
        #print(self.indicators_df)

    def _calculate_entry_score(self, row):
        score = 0
        # Add to score based on each indicator and its weight
        score += self.p.rsi_weight * (1 if row['rsi_entry'] else 0)
        score += self.p.cmf_weight * (1 if row['cmf_entry'] else 0)
        score += self.p.vwap_weight * (1 if row['vwap_entry'] else 0)
        score += self.p.obv_weight * (1 if row['obv_entry'] else 0)
        score += self.p.macd_weight * (1 if row['macd_entry'] else 0)
        score += self.p.stoch_weight * (1 if row['stoch_entry'] else 0)
        return score

    def _calculate_exit_score(self, row):
        score = 0
        # Add to score based on each indicator and its weight
        score += self.p.rsi_weight * (1 if row['rsi_exit'] else 0)
        score += self.p.cmf_weight * (1 if row['cmf_exit'] else 0)
        score += self.p.vwap_weight * (1 if row['vwap_exit'] else 0)
        score += self.p.obv_weight * (1 if row['obv_exit'] else 0)
        score += self.p.macd_weight * (1 if row['macd_exit'] else 0)
        score += self.p.stoch_weight * (1 if row['stoch_exit'] else 0)
        return score

    def _set_signals(self):
        # Create new columns for entry and exit signals, initialized to False
        self.indicators_df['entry'] = False
        self.indicators_df['exit'] = False

        # Define conditions for long entry and exit signals for RSI
        self.indicators_df['rsi_entry'] = (self.indicators_df['rsi'] > self.p.rsi_entry) & (self.indicators_df['rsi'] < 75)
        self.indicators_df['rsi_exit'] = self.indicators_df['rsi'] < self.p.rsi_exit

        # Define conditions for long entry and exit signals for CMF
        self.indicators_df['cmf_entry'] = self.indicators_df['cmf']*100 > self.p.cmf_entry
        self.indicators_df['cmf_exit'] = self.indicators_df['cmf']*100 < self.p.cmf_exit

        # define conditions for long entry and exit signals for VWAP
        self.indicators_df['vwap_entry'] = self.indicators_df['vwap_diff'] > self.p.vwap_entry
        self.indicators_df['vwap_exit'] = self.indicators_df['vwap_diff'] < self.p.vwap_exit*-1

        # Define conditions for entry and exit signals for OBV
        self.indicators_df['obv_entry'] = self.indicators_df['obv_pct_sma'] > self.p.obv_entry
        self.indicators_df['obv_exit'] = self.indicators_df['obv_pct_sma'] < self.p.obv_exit

        # Define conditions for entry and exit signals by MACD
        self.indicators_df['macd_entry'] = self.indicators_df['macd_histo'] > self.p.macd_entry
        self.indicators_df['macd_exit'] = self.indicators_df['macd_histo'] < self.p.macd_exit*-1

        # Define conditions for entry and exit for Stoch
        bullish_momentum_condition = (
            (self.indicators_df['stoch_k'] > self.p.stoch_entry) &
            (self.indicators_df['stoch_d'] > self.p.stoch_entry)
        )
        bullish_crossover = (
            (self.indicators_df['stoch_k'].shift(1) < self.indicators_df['stoch_d'].shift(1)) &
            (self.indicators_df['stoch_k'] > self.indicators_df['stoch_d'])
        )
        self.indicators_df['stoch_entry'] = bullish_momentum_condition & bullish_crossover

        # PEP 8 compliant version
        bearish_momentum_condition = (
            (self.indicators_df['stoch_k'] < self.p.stoch_exit) &
            (self.indicators_df['stoch_d'] < self.p.stoch_exit)
        )
        bearish_crossover = (
            (self.indicators_df['stoch_k'].shift(1) > self.indicators_df['stoch_d'].shift(1)) &
            (self.indicators_df['stoch_k'] < self.indicators_df['stoch_d'])
        )
        self.indicators_df['stoch_exit'] = bearish_momentum_condition & bearish_crossover

        self.indicators_df['entry_score'] = self.indicators_df.apply(self._calculate_entry_score, axis=1)
        self.indicators_df['exit_score'] = self.indicators_df.apply(self._calculate_exit_score, axis=1)

        # Define entry condition based on score
        self.indicators_df['entry'] = (
            (self.indicators_df['entry_score'] >= self.myentry) &
            (self.indicators_df['close'] > self.indicators_df['ema'])
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
                    self.entry_signal[0] = "Buy"
        except KeyError:
            pass

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
