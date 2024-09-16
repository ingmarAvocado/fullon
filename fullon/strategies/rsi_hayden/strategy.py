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



import pandas as pd
import numpy as np
from ta import add_all_ta_features
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator, WMAIndicator, MACD
from ta.volatility import BollingerBands
from sklearn.preprocessing import StandardScaler

def create_advanced_features(df):
    # Ensure DataFrame has 'open', 'high', 'low', 'close', and 'volume' columns
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    if not all(col in df.columns for col in required_columns):
        raise ValueError("DataFrame must have 'open', 'high', 'low', 'close', and 'volume' columns")

    # Add all technical analysis features
    df = add_all_ta_features(df, open="open", high="high", low="low", close="close", volume="volume")

    # Custom RSI and Moving Average features
    rsi = RSIIndicator(close=df['close'], window=14)
    df['rsi'] = rsi.rsi()
    df['sma_9'] = SMAIndicator(close=df['close'], window=9).sma_indicator()
    df['wma_45'] = WMAIndicator(close=df['close'], window=45).wma_indicator()
    df['rsi_sma_9'] = SMAIndicator(close=df['rsi'], window=9).sma_indicator()
    df['rsi_wma_45'] = WMAIndicator(close=df['rsi'], window=45).wma_indicator()

    # Trend
    df['trend'] = np.where((df['sma_9'] > df['wma_45']) & (df['rsi_sma_9'] > df['rsi_wma_45']), 1,
                  np.where((df['sma_9'] < df['wma_45']) & (df['rsi_sma_9'] < df['rsi_wma_45']), -1, 0))

    # Short and Long signals
    df['short_signal'] = ((df['rsi'] > 70) & (df['rsi'].shift(1) <= 70) & 
                          (df['close'] > df['sma_9']) & (df['sma_9'] > df['wma_45'])).astype(int)
    df['long_signal'] = ((df['rsi'] < 30) & (df['rsi'].shift(1) >= 30) & 
                         (df['close'] < df['sma_9']) & (df['sma_9'] < df['wma_45'])).astype(int)

    # RSI Range Shift
    df['rsi_range_shift'] = ((df['rsi'] > 60) & (df['rsi'].shift(1) <= 60) & (df['trend'].shift(1) == -1)) | \
                            ((df['rsi'] < 40) & (df['rsi'].shift(1) >= 40) & (df['trend'].shift(1) == 1))
    df['rsi_range_shift'] = df['rsi_range_shift'].astype(int)

    # Divergence
    df['price_higher_high'] = (df['close'] > df['close'].shift(1)) & (df['close'].shift(1) > df['close'].shift(2))
    df['rsi_lower_high'] = (df['rsi'] < df['rsi'].shift(1)) & (df['rsi'].shift(1) < df['rsi'].shift(2))
    df['bearish_divergence'] = (df['price_higher_high'] & df['rsi_lower_high']).astype(int)
    
    df['price_lower_low'] = (df['close'] < df['close'].shift(1)) & (df['close'].shift(1) < df['close'].shift(2))
    df['rsi_higher_low'] = (df['rsi'] > df['rsi'].shift(1)) & (df['rsi'].shift(1) > df['rsi'].shift(2))
    df['bullish_divergence'] = (df['price_lower_low'] & df['rsi_higher_low']).astype(int)

    # Additional Features
    df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    df['volatility'] = df['log_return'].rolling(window=14).std()
    
    # MACD
    macd = MACD(close=df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_diff'] = macd.macd_diff()

    # Bollinger Bands
    bollinger = BollingerBands(close=df['close'])
    df['bollinger_high'] = bollinger.bollinger_hband()
    df['bollinger_low'] = bollinger.bollinger_lband()
    df['bollinger_pct'] = (df['close'] - df['bollinger_low']) / (df['bollinger_high'] - df['bollinger_low'])

    # Market cap and trading volume features (if available)
    if 'market_cap' in df.columns:
        df['log_market_cap'] = np.log(df['market_cap'])
    df['volume_change'] = df['volume'].pct_change()

    # Time-based features
    df['day_of_week'] = pd.to_datetime(df.index).dayofweek
    df['month'] = pd.to_datetime(df.index).month

    # Remove rows with NaN values
    df.dropna(inplace=True)

    # Select features for the model
    feature_columns = [col for col in df.columns if col not in ['open', 'high', 'low', 'close', 'volume', 'market_cap']]

    # Normalize features
    scaler = StandardScaler()
    df[feature_columns] = scaler.fit_transform(df[feature_columns])

    return df, feature_columns

# Assuming you have a DataFrame 'bitcoin_df' with OHLCV data
# bitcoin_df = pd.read_csv('bitcoin_data.csv', index_col='date', parse_dates=True)

# Apply the feature engineering
bitcoin_df_features, feature_columns = create_advanced_features(bitcoin_df)

# Display the first few rows with the new features
print(bitcoin_df_features[feature_columns].head())

# Now you can use 'bitcoin_df_features' and 'feature_columns' for your XGBoost model




from sklearn.model_selection import train_test_split
import xgboost as xgb

# Prepare target variable (example: next day's closing price)
bitcoin_df_features['target'] = bitcoin_df_features['close'].shift(-1)
bitcoin_df_features.dropna(inplace=True)

X = bitcoin_df_features[feature_columns]
y = bitcoin_df_features['target']

# Split the data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Create and train the model
model = xgb.XGBRegressor(n_estimators=100, learning_rate=0.08, gamma=0, subsample=0.75,
                         colsample_bytree=1, max_depth=7)

model.fit(X_train, y_train)

# Make predictions
predictions = model.predict(X_test)

# Evaluate the model
from sklearn.metrics import mean_squared_error, r2_score
mse = mean_squared_error(y_test, predictions)
r2 = r2_score(y_test, predictions)

print(f"Mean Squared Error: {mse}")
print(f"R2 Score: {r2}")



import pandas as pd
import pandas_ta as ta
import numpy as np

def add_hayden_signals(df):
    # Calculate RSI
    df.ta.rsi(close='close', length=14, append=True)
    
    # Calculate Moving Averages
    df.ta.sma(close='close', length=9, append=True)
    df.ta.wma(close='close', length=45, append=True)
    df['rsi_sma_9'] = df['RSI_14'].rolling(window=9).mean()
    df['rsi_wma_45'] = df.ta.wma(close='RSI_14', length=45)
    
    # 1. Trend Signal
    df['trend'] = np.where((df['SMA_9'] > df['WMA_45']) & (df['rsi_sma_9'] > df['rsi_wma_45']), 'uptrend',
                  np.where((df['SMA_9'] < df['WMA_45']) & (df['rsi_sma_9'] < df['rsi_wma_45']), 'downtrend',
                  np.where(df['SMA_9'] > df['WMA_45'], 'sideways_up', 'sideways_down')))
    
    # 2. Short Signal
    df['short_signal'] = ((df['RSI_14'] > 70) & (df['RSI_14'].shift(1) <= 70) & 
                          (df['close'] > df['SMA_9']) & (df['SMA_9'] > df['WMA_45']))
    
    # 3. Long Signal
    df['long_signal'] = ((df['RSI_14'] < 30) & (df['RSI_14'].shift(1) >= 30) & 
                         (df['close'] < df['SMA_9']) & (df['SMA_9'] < df['WMA_45']))
    
    # 4. Other Signals
    # RSI Range Shift
    df['rsi_range_shift'] = ((df['RSI_14'] > 60) & (df['RSI_14'].shift(1) <= 60) & (df['trend'].shift(1) == 'downtrend')) | \
                            ((df['RSI_14'] < 40) & (df['RSI_14'].shift(1) >= 40) & (df['trend'].shift(1) == 'uptrend'))
    
    # Divergence (simplified)
    df['price_higher_high'] = (df['close'] > df['close'].shift(1)) & (df['close'].shift(1) > df['close'].shift(2))
    df['rsi_lower_high'] = (df['RSI_14'] < df['RSI_14'].shift(1)) & (df['RSI_14'].shift(1) < df['RSI_14'].shift(2))
    df['bearish_divergence'] = df['price_higher_high'] & df['rsi_lower_high']
    
    df['price_lower_low'] = (df['close'] < df['close'].shift(1)) & (df['close'].shift(1) < df['close'].shift(2))
    df['rsi_higher_low'] = (df['RSI_14'] > df['RSI_14'].shift(1)) & (df['RSI_14'].shift(1) > df['RSI_14'].shift(2))
    df['bullish_divergence'] = df['price_lower_low'] & df['rsi_higher_low']
    
    return df

# Assuming you have a DataFrame 'bitcoin_df' with OHLCV data
# bitcoin_df = pd.read_csv('bitcoin_data.csv')  # Uncomment and use your data source

# Apply the signals
bitcoin_df_with_signals = add_hayden_signals(bitcoin_df)

# Display the first few rows with the new signals
print(bitcoin_df_with_signals[['close', 'RSI_14', 'trend', 'short_signal', 'long_signal', 'rsi_range_shift', 'bearish_divergence', 'bullish_divergence']].head())






