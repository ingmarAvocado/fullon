"""
Describe strategy
"""
import arrow
from typing import Optional
from libs.strategy import loader
from libs import log
import libs.predictor.predictor_tools as PredictorTools
import pandas
import pandas_ta as ta
import backtrader as bt


logger = log.fullon_logger(__name__)

strat = loader.strategy


class Strategy(strat.Strategy):
    """description"""

    params = (
        ('trailing_stop', 11),
        ('take_profit', 20),
        ('rsi', 14),
        ('rsi_entry', 65),
        ('cmf', 18),
        ('cmf_entry', 11),
        ('vwap_entry', 0.6),
        ('obv', 18),
        ('obv_entry', 1.4),
        ('macd_entry', 3),
        ('stoch_entry', 50),
        ('pre_load_bars', 50),
        ('ema', 40),
        ('prediction_steps', 1),
        ('feeds', 2),
        ('threshold', 0.25)
    )

    next_open: arrow.Arrow

    def local_init(self):
        """description"""
        self.verbose = False
        self.order_cmd = "spread"
        if self.p.timeout:
            self.p.timeout = self.datas[1].bar_size_minutes * self.p.timeout
        self.regressors: dict = {}
        self.scaler: object = None
        self.set_predictor()

    def local_next(self):
        """ description """
        if self.entry_signal[0]:
            if self.curtime[0] >= self.next_open:
                if self.open_pos(0):
                    self.crossed_lower = False
                    self.crossed_upper = False
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
            #self.next_open = self.time_to_next_bar(feed=1).shift(minutes=240*0)
            self.next_open = self.time_to_next_bar(feed=1).shift(days=0)
            self.entry_signal[0] = ""
            time_difference = (self.next_open.timestamp() - self.curtime[0].timestamp())
            if time_difference <= 60:  # less than 60 seconds
                self.next_open = self.next_open.shift(minutes=self.datas[1].bar_size_minutes)

    def set_indicators_df(self):
        """
        sets indidcator_df to use during the strategies, it works on every loop with real trading
        but only once when simulating
        """
        data = self.datas[1].dataframe[['open', 'high', 'low', 'close', 'volume']].copy()
        data = self.set_features(data=data)
        self.indicators_df = data.copy()
        data = PredictorTools.set_target(data=data,
                                         target="go_long",
                                         steps=int(self.p.prediction_steps))[1]
        data_scaled = PredictorTools.rescale_data(data=data, scaler=self.scaler)
        preds = pandas.DataFrame(index=data.index)

        for key in self.regressors.keys():
            predictions = self.regressors[key].predict_proba(data_scaled)[:, 1]
            # Convert probabilities to boolean based on the threshold
            preds[f'score_{key}'] = predictions
        preds['score'] = preds[[f'score_{key}' for key in self.regressors.keys()]].sum(axis=1)
        #import ipdb
        #ipdb.set_trace()
        preds['entry'] = preds['score'] > self.p.threshold*len(self.regressors)


        # Get the probability predictions for the class of interest (assumed to be the second class)
        #self.indicators_df = pandas.DataFrame(index=data.index)
        self.indicators_df['exit'] = False  # ~self.indicators_df['entry']
        indicators = ['ema_long', 'rsi_entry', 'cmf_entry',
                      'vwap_entry', 'macd_entry', 'stoch_entry',
                      'breakout']

        self.indicators_df['entry'] = preds['entry']
        self.indicators_df['score'] = preds['score']
        # Create a mask where 'entry' is True AND all of the indicators are False
        mask = self.indicators_df['entry'] & (self.indicators_df[indicators] == False).all(axis=1)
        # Apply the mask to set 'entry' to False where the condition is met
        self.indicators_df.loc[mask, 'entry'] = False

    def set_indicators(self):
        """
        This happens on each loop, it sets indicators in variable self.indicator
        changed during each loop.

        printed when verbose is true in simuls
        """
        current_time = self.curtime[1].format('YYYY-MM-DD HH:mm:ss')
        for indicator in ['entry', 'exit', 'score', 'macd', 'obv', 'obv_pct_change',
                          'ema_long', 'rsi_entry', 'cmf_entry',
                          'vwap_entry', 'macd_entry', 'stoch_entry', 'breakout']:
            try:
                value = self.indicators_df.loc[current_time, indicator]
                self.set_indicator(indicator, value)
            except KeyError:
                self.set_indicator(indicator, None)

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

    def set_predictor(self):
        """
        sets a predictor
        """
        # Define the end date of the data and start date based on the oldest available data
        regressors = ['GradientBoostingClassifier', 'CatBoostClassifier']
        todate = arrow.get(bt.num2date(self.datas[0].fromdate)).floor('week')  # floor month?
        fromdate = PredictorTools.get_oldest_timestamp(feed=self.datas[1])
        filenames: dict = {}
        for regressor in regressors:
            _regressor, _file, _scaler, _ = PredictorTools.try_loading(
                                                fromdate=fromdate,
                                                todate=todate.format(),
                                                predictor=regressor,
                                                feed=self.datas[1].feed)

            filenames[regressor] = _file
            self.regressors[regressor] = _regressor
            if not self.scaler:
                self.scaler = _scaler

        # Check if all models were pre-loaded
        self.pre_loaded = all(model is not None for model in self.regressors.values())
        # If not all models are pre-loaded, additional logic for retraining would go here
        if self.pre_loaded and self.scaler:
            return
        _data = PredictorTools.load_dataframe(feed=self.datas[1],
                                              fromdate=fromdate,
                                              todate=todate.format())

        if _data.empty:
            logger.error("Cant load dataframe, exiting")
            return self.cerebro.runstop()
        if not PredictorTools.data_quality_checks(data=_data):
            logger.error("Dataframe loaded, but has quality check issues")
            return self.cerebro.runstop()
        _data = self.set_features(data=_data)
        data, scaler = PredictorTools.scale_data(data=_data)
        saved_scaler = PredictorTools.save_scaler(fromdate=fromdate,
                                                  todate=todate.format(),
                                                  feed=self.datas[1].feed,
                                                  scaler=scaler)
        if not saved_scaler:
            logger.error("Could not save scaler")
            self.cerebro.runstop()
        self.scaler = scaler
        target, data = PredictorTools.set_target(data=data,
                                                 target="go_long",
                                                 steps=self.p.prediction_steps)
        if target.empty:
            logger.error("Target was not set")
            return self.cerebro.runstop()
        self.regressors = PredictorTools.train_regressors(data=data,
                                                          target=target,
                                                          filenames=filenames,
                                                          regressors=regressors)
        if self.regressors == {}:
            logger.error("One or more of the regressors came back empty")
            self.cerebro.runstop()

    def set_features(self, data: pandas.DataFrame) -> pandas.DataFrame:
        """
        data: OHLCV data
        """
        data['ema1'] = data['close'].ewm(span=8, adjust=False).mean()
        data['ema2'] = data['close'].ewm(span=21, adjust=False).mean()
        data['ema3'] = data['close'].ewm(span=34, adjust=False).mean()
        data['ema4'] = data['close'].ewm(span=50, adjust=False).mean()
        data['ema5'] = data['close'].ewm(span=100, adjust=False).mean()
        data['ema6'] = data['close'].ewm(span=200, adjust=False).mean()
        # Compute RSI
        data['rsi'] = ta.rsi(data['close'], length=self.p.rsi)
        data['rsi_sma'] = data['rsi'].rolling(window=14).mean()
        # Compute MACD
        macd = ta.macd(data['close'])
        data['macd'] = macd['MACD_12_26_9']
        data['macdsignal'] = macd['MACDs_12_26_9']
        data['macd_histo'] = data['macd'] - data['macdsignal']
        data['macd_histo'] = data['macd_histo'] / 10

        # Compute Stochastic Oscillator
        stochastic = ta.stoch(data['high'], data['low'], data['close'])
        data['stoch_k'] = stochastic['STOCHk_14_3_3']
        data['stoch_d'] = stochastic['STOCHd_14_3_3']
        # Compute Volume Weighted Average Price (VWAP)
        data['vwap'] = ta.vwap(high=data['high'],
                               low=data['low'],
                               close=data['close'],
                               volume=data['volume'])
        data['vwap_diff'] = (data['close'] - data['vwap']) / data['vwap'] * 100
        # Compute On-Balance Volume (OBV)
        data['obv'] = ta.obv(data['close'], data['volume'])
        data['obv_pct_change'] = data['obv'].pct_change() * 100
        data['obv_pct_sma'] = data['obv_pct_change'].rolling(window=int(self.p.obv)).mean()
        # Compute CMF
        data['cmf'] = ta.cmf(data['high'],
                             data['low'],
                             data['close'],
                             data['volume'],
                             length=self.p.cmf)

        data['change_pct'] = ((data['close'] - data['open']) / data['open']) * 100
        data['go_long'] = data['change_pct'] > 0
        data = self.set_ta_features(data=data)
        data = self.check_breakouts(data=data)
        columns_to_drop = ['open', 'high', 'low', 'volume', 'change_pct']
        data = data.drop(columns=columns_to_drop)
        data = data.dropna()
        return data

    def check_breakouts(self, data: pandas.DataFrame) -> pandas.DataFrame:
        """
        Check for breakouts from the Keltner Channel using a vectorized approach.
        """
        temp = data.copy()
        # Calculate EMA for the midline of the Keltner Channel
        temp['ema21'] = data['close'].ewm(span=self.p.ema, adjust=False).mean()
        # Calculate the true range components
        high_low = temp['high'] - temp['low']
        high_close = (temp['high'] - temp['close'].shift()).abs()
        low_close = (temp['low'] - temp['close'].shift()).abs()

        # Combine the components to get the true range
        temp['tr'] = high_low.combine(high_close, max).combine(low_close, max)

        # Calculate the 14-period ATR
        temp['atr14'] = temp['tr'].rolling(window=14).mean()

        # Calculate Keltner Channels
        temp['keltner_mid'] = temp['ema21']
        temp['keltner_upper_1'] = temp['ema21'] + temp['atr14']
        temp['keltner_lower_1'] = temp['ema21'] - temp['atr14']
        temp['keltner_upper_2'] = temp['ema21'] + 2 * temp['atr14']
        temp['keltner_lower_2'] = temp['ema21'] - 2 * temp['atr14']
        temp['keltner_upper_3'] = temp['ema21'] + 3 * temp['atr14']
        temp['keltner_lower_3'] = temp['ema21'] - 3 * temp['atr14']

        # Determine where the close price crosses above the upper 3rd Keltner Channel
        crossover = (temp['close'].shift(1) <= temp['keltner_upper_3'].shift(1)) & (temp['close'] > temp['keltner_upper_3'])
        # Assign the crossover detection to the 'breakout' column
        data['breakout'] = crossover
        return data

    def set_ta_features(self, data: pandas.DataFrame) -> pandas.DataFrame:
        """
        mmm
        """
        # Define conditions for long entry and exit signals for RSI
        data['ema_long'] = (data['ema1'] > data['ema2']) & (data['ema2'] > data['ema3']) & \
                           (data['ema3'] > data['ema4']) & (data['ema4'] > data['ema5']) & \
                           (data['ema5'] > data['ema6'])
        columns_to_drop = ['ema1', 'ema2', 'ema3', 'ema4', 'ema5', 'ema6']
        data = data.drop(columns=columns_to_drop)
        data = data.dropna()
        # Define conditions for long entry and exit signals for RSI
        data['rsi_entry'] = (data['rsi'] > self.p.rsi_entry) & (data['rsi'] < 80)
        data['rsi_sma_entry'] = (data['rsi'] > data['rsi_sma'])

        #rsi_control = data['rsi'].rolling(window=14, min_periods=1).mean()
        #data['rsi_control'] = (data['rsi'] > rsi_control)
        # Define conditions for long entry and exit signals for CMF
        data['cmf_entry'] = data['cmf']*100 > self.p.cmf_entry
        # define conditions for long entry and exit signals for VWAP
        columns_to_drop = ['cmf', 'rsi', 'rsi_sma']
        data = data.drop(columns=columns_to_drop)
        data['vwap_entry'] = data['vwap_diff'] > self.p.vwap_entry
        columns_to_drop = ['vwap', 'vwap_diff']
        data = data.drop(columns=columns_to_drop)
        # Define conditions for entry and exit signals for OBV
        data['obv_entry'] = data['obv_pct_sma'] > self.p.obv_entry
        # Define conditions for entry and exit signals by MACD
        columns_to_drop = ['obv_pct_sma', 'obv_entry']
        data = data.drop(columns=columns_to_drop)
        data['macd_entry'] = data['macd_histo'] > self.p.macd_entry
        # Define conditions for entry and exit for Stoch
        columns_to_drop = ['macdsignal', 'macd_histo']
        data = data.drop(columns=columns_to_drop)

        bullish_momentum_condition = (
            (data['stoch_k'] > self.p.stoch_entry) &
            (data['stoch_d'] > self.p.stoch_entry)
        )
        bullish_crossover = (
            (data['stoch_k'].shift(1) < data['stoch_d'].shift(1)) &
            (data['stoch_k'] > data['stoch_d'])
        )
        data['stoch_entry'] = bullish_momentum_condition & bullish_crossover
        columns_to_drop = ['stoch_k', 'stoch_d']
        data = data.drop(columns=columns_to_drop)
        data = data.dropna()
        return data

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
