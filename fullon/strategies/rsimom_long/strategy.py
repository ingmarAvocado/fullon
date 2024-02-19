"""
Describe strategy
"""
import arrow
from typing import Optional, Tuple
from libs.strategy import loader
from libs import log
import libs.predictor.predictor_tools as PredictorTools
import pandas
import pandas_ta as ta
import backtrader as bt
from astral import moon


logger = log.fullon_logger(__name__)

strat = loader.strategy


class Strategy(strat.Strategy):
    """description"""

    params = (
        ('trailing_stop', 11),
        ('take_profit', 20),
        ('rsi', 14),
        ('entry', 65),
        ('exit', 60)
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
        sets indicator_df to use during the strategies, it works on every loop with real trading
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

    def set_indicators(self):
        """
        This happens on each loop, it sets indicators in variable self.indicator
        changed during each loop.

        printed when verbose is true in simuls
        """
        current_time = self.curtime[1].format('YYYY-MM-DD HH:mm:ss')
        ind_list = ['entry', 'exit']
        for indicator in ind_list:
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
                    self.entry_signal[0] = "Sell"
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
                                                 target="go_short",
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
        Calculates and sets features for a short momentum-based trading strategy on the given OHLCV data.
        Parameters:
        - data (pd.DataFrame): The OHLCV data.

        Returns:
        pd.DataFrame: The data with calculated features, tailored for identifying short opportunities.
        """

        # Compute RSI directly on hourly data
        data['1h_rsi'] = ta.rsi(data['close'], length=self.p.rsi)

        # Helper function to resample and calculate RSI for a given timeframe
        def resample_and_calc_rsi(data, timeframe, label_prefix):
            resampled_df = data.resample(timeframe).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })
            # Calculate RSI on resampled data
            rsi = ta.rsi(resampled_df['close'], length=self.p.rsi)
            # Create a temporary DataFrame to hold resampled RSI values with the original index
            temp_df = pandas.DataFrame(index=data.index)
            temp_df[label_prefix + '_rsi'] = rsi.reindex(data.index, method='ffill')
            temp_df[label_prefix + '_close'] = resampled_df['close'].reindex(data.index, method='ffill')
            return temp_df

        # Define timeframes for resampling
        timeframes = {
            '4H': '4h',
            '8H': '8h',
            '12H': '12h',
            'D': '1D'
        }

        # Process each timeframe
        for label, tf in timeframes.items():
            temp_df = resample_and_calc_rsi(data, tf, label)
            data = pandas.concat([data, temp_df], axis=1)


        print(data)
        import ipdb
        ipdb.set_trace()

        data['rsi_sma'] = data['rsi'].rolling(window=10).mean()
        #data['moon'] = data.index.to_series().apply(moon.phase)
        data['change_pct'] = ((data['close'] - data['open']) / data['open']) * 100
        #data['roc'] = data['close'].pct_change(periods=19) * 100
        # Modify this to suit the condition for shorting
        data['go_long'] = data['change_pct'] > 1

        # Further feature engineering and breakout checks
        data = self.set_ta_features(data=data)  # Adjust this method for shorts

        # Drop unnecessary columns
        columns_to_drop = ['open', 'high', 'low', 'volume', 'change_pct']
        data = data.drop(columns=columns_to_drop)

        # Remove any remaining NaN values
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
