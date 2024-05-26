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
from astral import moon
import time


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
        ('vwap_entry', 0.4),
        ('macd_entry', 2.5),
        ('mfi_entry', 60),
        ('pre_load_bars', 200),
        ('sma', 200),
        ('prediction_steps', 1),
        ('feeds', 2),
        ('threshold', 0.48)
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
            self.next_open = self.time_to_next_bar(feed=1).shift(days=1)
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
        preds['entry'] = preds['score'] > self.p.threshold*len(self.regressors)
        # Get the probability predictions for the class of interest (assumed to be the second class)
        self.indicators_df['exit'] = False
        indicators = ['sma_long', 'rsi_entry', 'cmf_entry',
                      'vwap_entry', 'macd_entry']
        self.indicators_df['entry'] = preds['entry']
        self.indicators_df['score'] = preds['score']
        # Create a mask where 'entry' is True AND all of the indicators are False
        mask = self.indicators_df['entry'] & (self.indicators_df[indicators] == False).all(axis=1)
        # Apply the mask to set 'entry' to False where the condition is met
        self.indicators_df.loc[mask, 'entry'] = False
        self.indicators_df['sma'] = self.indicators_df['close'].rolling(window=int(self.p.sma)).mean()
        self.indicators_df['entry'] = self.indicators_df['entry'] & (self.indicators_df['close'] > self.indicators_df['sma'])
        self.indicators_df['exit'] = self.indicators_df['score'] < (self.p.threshold/2)*len(self.regressors)
        self.adjust_index(feed_num=1)

    def set_indicators(self):
        """
        This happens on each loop, it sets indicators in variable self.indicator
        changed during each loop.

        printed when verbose is true in simuls
        """
        current_time = self.curtime[1].format('YYYY-MM-DD HH:mm:ss')
        '''
        for indicator in ['entry', 'exit', 'score', 'adsoc',
                          'ema_long', 'rsi_entry', 'cmf_entry',
                          'vwap_entry', 'macd_entry']:
        '''
        for indicator in ['entry', 'exit']:
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
        #todate = arrow.utcnow().floor('week')
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
        data['sma1'] = data['close'].rolling(window=5).mean()
        data['sma2'] = data['close'].rolling(window=21).mean()
        data['sma3'] = data['close'].rolling(window=50).mean()
        # Compute RSI
        data['rsi'] = ta.rsi(data['close'], length=self.p.rsi)
        data['rsi_sma'] = data['rsi'].rolling(window=10).mean()
        # Compute MACD
        macd = ta.macd(data['close'])
        data['macd'] = macd['MACD_12_26_9']
        data['macdsignal'] = macd['MACDs_12_26_9']
        data['macd_histo'] = data['macd'] - data['macdsignal']
        data['macd_histo'] = data['macd_histo'] / 10

        # Compute Volume Weighted Average Price (VWAP)
        data['vwap'] = ta.vwap(high=data['high'],
                               low=data['low'],
                               close=data['close'],
                               volume=data['volume'])
        data['vwap_diff'] = (data['close'] - data['vwap']) / data['vwap'] * 100

        data['efi'] = ta.efi(
            close=data['close'],
            volume=data['volume'],
            length=14  # period for the EFI
        )

        # Calculate MFI using pandas-ta
        data['mfi'] = ta.mfi(
            high=data['high'],
            low=data['low'],
            close=data['close'],
            volume=data['volume'],
            length=14  # period for the MFI
        )


        # Compute CMF
        data['cmf'] = ta.cmf(data['high'],
                             data['low'],
                             data['close'],
                             data['volume'],
                             length=self.p.cmf)
        data['moon'] = data.index.to_series().apply(moon.phase)
        data['change_pct'] = ((data['close'] - data['open']) / data['open']) * 100
        data['roc'] = data['close'].pct_change(periods=19) * 100
        data['go_long'] = data['change_pct'] > 0
        data = self.set_ta_features(data=data)
        columns_to_drop = ['open', 'high', 'low', 'volume', 'change_pct', 'macd']
        data = data.drop(columns=columns_to_drop)
        data = data.dropna()
        return data

    def set_ta_features(self, data: pandas.DataFrame) -> pandas.DataFrame:
        """
        mmm
        """
        # Define conditions for long entry and exit signals for RSI
        data['sma_long'] = (data['sma1'] > data['sma2']) & (data['sma2'] > data['sma3'])
        columns_to_drop = ['sma1', 'sma2', 'sma3']
        data = data.drop(columns=columns_to_drop)
        data = data.dropna()
        # Define conditions for long entry and exit signals for RSI
        data['rsi_entry'] = (data['rsi'] > self.p.rsi_entry) & (data['rsi'] < 80)
        data['rsi_sma_entry'] = (data['rsi'] > data['rsi_sma'])
        # Define conditions for long entry and exit signals for CMF
        data['cmf_entry'] = data['cmf']*100 > self.p.cmf_entry
        # define conditions for long entry and exit signals for VWAP
        columns_to_drop = ['cmf', 'rsi', 'rsi_sma']
        data = data.drop(columns=columns_to_drop)
        data['vwap_entry'] = data['vwap_diff'] > self.p.vwap_entry
        columns_to_drop = ['vwap', 'vwap_diff']
        data = data.drop(columns=columns_to_drop)
        # Define conditions for entry and exit signals for ADSOC
        data['efi_entry'] = data['efi'] > 0
        data['mfi_entry'] = data['mfi'] > self.p.mfi_entry
        data['macd_entry'] = data['macd_histo'] > self.p.macd_entry
        # Define conditions for entry and exit for Stoch
        columns_to_drop = ['macdsignal', 'macd_histo']
        data = data.drop(columns=columns_to_drop)
        data = data.dropna()
        return data
