"""
Describe strategy
"""
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
        ('take_profit', 9),
        ('trailing_stop', 4.5),
        ('timeout', 37),
        ('stop_loss', 4.6),
        ('rsi', 12),
        ('rsi_entry', 64),
        ('rsi_exit', 62),
        ('cmf', 20),
        ('cmf_entry', 20),
        ('cmf_exit', 20),
        ('vwap_entry', 64),
        ('vwap_exit', 62),
        ('ad_line', 62),
        ('ad_line_entry', 62),
        ('ad_line_exit', 62),
        ('obv', 62),
        ('obv_entry', 62),
        ('obv_exit', 62),
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
        if self.p.rsi_exit >= self.p.rsi_entry:
            self.cerebro.runstop()

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
        # Fetch required data
        #self.indicators_df = self.datas[1].dataframe[['open', 'high', 'low', 'close', 'volume']].copy()
        self.indicators_df = self.datas[1].dataframe[['close', 'volume']].copy()

        # Compute RSI
        #self.indicators_df['rsi'] = ta.rsi(self.indicators_df['close'], length=self.p.rsi)

        '''
        # Compute MACD
        macd = ta.macd(self.indicators_df['close'])
        self.indicators_df['macd'] = macd['MACD_12_26_9']
        self.indicators_df['macdsignal'] = macd['MACDs_12_26_9']

        # Compute Stochastic Oscillator
        stochastic = ta.stoch(self.indicators_df['high'], self.indicators_df['low'], self.indicators_df['close'])
        self.indicators_df['stoch_k'] = stochastic['STOCHk_14_3_3']
        self.indicators_df['stoch_d'] = stochastic['STOCHd_14_3_3']

        # Compute ATR
        self.indicators_df['atr'] = ta.atr(self.indicators_df['high'], self.indicators_df['low'], self.indicators_df['close'], length=14)

        # Compute Bollinger Bands
        bollinger = ta.bbands(self.indicators_df['close'])

        self.indicators_df['bollinger_lband'] = bollinger['BBL_5_2.0']
        self.indicators_df['bollinger_mavg'] = bollinger['BBM_5_2.0']
        self.indicators_df['bollinger_hband'] = bollinger['BBU_5_2.0']
        self.indicators_df['bollinger_bwidth'] = bollinger['BBB_5_2.0']
        self.indicators_df['bollinger_%b'] = bollinger['BBP_5_2.0']

        # Compute Volume Weighted Average Price (VWAP)
        self.indicators_df['vwap'] = ta.vwap(high=self.indicators_df['high'],
                                             low=self.indicators_df['low'],
                                             close=self.indicators_df['close'],
                                             volume=self.indicators_df['volume'])
        self.indicators_df['vwap_diff'] = (self.indicators_df['close'] - self.indicators_df['vwap']) / self.indicators_df['vwap'] * 100
        '''
        # Compute On-Balance Volume (OBV)
        self.indicators_df['obv'] = ta.obv(self.indicators_df['close'], self.indicators_df['volume'])
        self.indicators_df['obv_mom'] = self.indicators_df['obv'].diff()
        self.indicators_df['obv_mom_sma'] = self.indicators_df['obv_mom'].rolling(window=self.p.obv).mean()

        # Compute Accumulation/Distribution Line (A/D Line)
        '''

        self.indicators_df['ad_line'] = ta.ad(high=self.indicators_df['high'], low=self.indicators_df['low'], close=self.indicators_df['close'], volume=self.indicators_df['volume'])
        self.indicators_df['ad_line_mom'] = self.indicators_df['ad_line'].diff()
        self.indicators_df['ad_line_mom_sma'] = self.indicators_df['ad_line_mom'].rolling(window=int(self.p.ad_line)).mean()

        self.indicators_df['cmf'] = ta.cmf(self.indicators_df['high'],
                                           self.indicators_df['low'],
                                           self.indicators_df['close'],
                                           self.indicators_df['volume'],
                                           length=self.p.cmf)


        # Remember to update the _set_signals method to include the logic for these new indicators
        '''
        self._set_signals()
        self.indicators_df = self.indicators_df.dropna()

    def _set_signals(self):
        # Create new columns for entry and exit signals, initialized to False
        self.indicators_df['entry'] = False
        self.indicators_df['exit'] = False


        #long_entry_cond = (self.indicators_df['rsi'] > self.p.entry) & (self.indicators_df['cmf']*100 > self.p.cmf_entry)
        #long_exit_cond = (self.indicators_df['rsi'] < self.p.exit) | (self.indicators_df['cmf']*100 < self.p.cmf_exit)

        # Define conditions for long entry and exit signals for RSI
        #long_entry_cond = self.indicators_df['rsi'] > self.p.rsi_entry
        #long_exit_cond = self.indicators_df['rsi'] < self.p.rsi_exit

        # Define conditions for long entry and exit signals for CMF
        #long_entry_cond = self.indicators_df['cmf']*100 > self.p.cmf_entry
        #long_exit_cond =  self.indicators_df['cmf']*100 < self.p.cmf_exit

        # define conditions for long entry and exit signals for VWAP
        #long_entry_cond = self.indicators_df['vwap_diff'] > self.p.vwap_entry
        #long_exit_cond = self.indicators_df['vwap_diff'] < self.p.vwap_exit*-1

        # Define conditions for entry and exit signals for ad_line
        #long_entry_cond = self.indicators_df['ad_line_mom_sma'] > self.p.ad_line_entry
        #long_exit_cond = self.indicators_df['ad_line_mom_sma'] < self.p.ad_line_exit

        # Define condtions for entry and exit signals for OBV

        long_entry_cond = self.indicators_df['obv_mom_sma'] > self.p.obv_entry
        long_exit_cond = self.indicators_df['obv_mome_sma'] < self.p.obv_exit


        # Update the DataFrame with the entry and exit signals based on the conditions
        self.indicators_df.loc[long_entry_cond, 'entry'] = True
        self.indicators_df.loc[long_exit_cond, 'exit'] = True

    def set_indicators(self):
        current_time = self.curtime[1].format('YYYY-MM-DD HH:mm:ss')

        try:
            long_entry = self.indicators_df.loc[current_time, 'entry']
        except KeyError:
            long_entry = None
        try:
            long_exit = self.indicators_df.loc[current_time, 'exit']
        except KeyError:
            long_exit = None
    # Fetching and setting each indicator
        '''
        lista = ['rsi', 'macd', 'macdsignal', 'stoch_k', 'stoch_d', 'atr',
                      'bollinger_lband', 'bollinger_mavg', 'bollinger_hband',
                      'bollinger_bwidth', 'bollinger_%b', 'vwap', 'obv',
                      'ad_line', 'cmf']
        for indicator in ['cmf','rsi']:
            try:
                value = self.indicators_df.loc[current_time, indicator]
                self.set_indicator(indicator, value)
            except KeyError:
                value = None
        '''
        
        self.set_indicator('entry', long_entry)
        self.set_indicator('exit', long_exit)

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
