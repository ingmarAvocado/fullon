from numpy.lib.shape_base import row_stack
import pandas
import pandas_ta as ta
from libs.database_ohlcv import Database as Database_ohlcv
from libs import log
from libs.btrader.fullonfeed import FullonFeed
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, GradientBoostingClassifier, GradientBoostingRegressor
from typing import Tuple, List, Any, Dict
import os
import arrow
from time import sleep
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier
import joblib

#from libs.predictor.xgb import Xgb

logger = log.fullon_logger(__name__)


def _load_from_pickle(feed: FullonFeed,
                      fromdate: str,
                      todate: str) -> pandas.DataFrame:
    """
    Args:
        fromdate (str): The date of the data to load, in the format 'YYYY-MM-DD'.
    Returns:
        pandas.DataFrame: The loaded data.
    """
    pre_fix = f"pickle/{feed._table}_{feed.compression}_{feed.feed.period}"
    pre_fix = pre_fix + f"_{arrow.get(fromdate).format('YYYY_MM_DD_HH_mm')}_"
    filename = pre_fix + f"to_{arrow.get(todate).format('YYYY_MM_DD_HH_mm')}.pkl"
    try:
        with open(filename, 'rb') as file:
            dataframe = pandas.read_pickle(file)
        if isinstance(dataframe, pandas.Series):
            # Convert to DataFrame if the data is a Series
            return dataframe.to_frame()
        return dataframe
    except FileNotFoundError:
        try:
            with open("fullon/"+filename, 'rb') as file:
                dataframe = pandas.read_pickle(file)
            if isinstance(dataframe, pandas.Series):
                # Convert to DataFrame if the data is a Series
                return dataframe.to_frame()
            return dataframe
        except FileNotFoundError:
            logger.error(f"Pickle file ({filename}) not found")
    return pandas.DataFrame()


def _wait_for_flagfile(filename, max_loops=600, sleep_time=0.5):
    """
    Wait until the specified flag file is removed.
    Parameters:
        filename (str): The path to the flag file.
        max_loops (int): The maximum number of loops to wait for. Default is 600.
        sleep_time (float): The time to sleep between each loop. Default is 0.5 seconds.

    Raises:
        Exception: If the file still exists after max_loops.
    """
    loop_count = 0
    while os.path.exists(filename) and loop_count < max_loops:
        sleep(sleep_time)
        loop_count += 1

    if loop_count >= max_loops:
        raise Exception("Timeout waiting for flagfile to be deleted.")

def _create_empty_flagfile(filename):
    """
    Create an empty flag file with the given filename.
    Parameters:
        filename (str): The path to the flag file.
    """
    def pickle_exists():
        """
        if pickle folder doest exist, make it!
        """
        if not os.path.exists("pickle"):
            os.makedirs("pickle")
    if filename.startswith("fullon"):
        pickle_exists()
    else:
        pickle_exists()
    try:
        with open(filename, 'w'):
            return True
    except FileNotFoundError:
        if os.path.exists(filename):
            with open("fullon/"+filename, 'w'):
                return True
    logger.error("Seems There is an issue with creating pickle file, check it")
    return False


def _fetch_data_from_db(feed: FullonFeed,
                        todate: arrow.Arrow,
                        fromdate: arrow.Arrow) -> List[Any]:
    """
    Returns:
        rows: The fetched data.
    """
    with Database_ohlcv(exchange=feed.feed.exchange_name,
                        symbol=feed.symbol) as dbase:
        rows = dbase.fetch_ohlcv(table=feed._table,
                                 compression=feed.compression,
                                 period=feed.feed.period,
                                 fromdate=fromdate.datetime,
                                 todate=todate.shift(microseconds=-1).datetime)
    return rows


def _to_df(rows: List[Any]):
    """
    Creates a DataFrame from the input data
    :param rows: The data to be saved
    """
    dataframe = pandas.DataFrame(rows)
    # Rename the columns
    dataframe.rename(columns={0: "date",
                              1: "open",
                              2: "high",
                              3: "low",
                              4: "close",
                              5: "volume"}, inplace=True)
    # Set the index to the 'date' column
    dataframe.set_index("date", inplace=True)
    # Get the columns to convert to numeric
    columns_to_convert = dataframe.columns.difference(['date'])
    # Convert the columns to numeric
    dataframe[columns_to_convert] = dataframe[columns_to_convert].apply(pandas.to_numeric)
    dataframe.index = pandas.to_datetime(dataframe.index)
    return dataframe


def _save_to_pickle(dataframe: pandas.DataFrame,
                    feed: FullonFeed,
                    fromdate: str,
                    todate: str):
    """
    Saves the given rows as a pandas dataframe in a pickle file.
    The file is saved in the 'pickle' directory and is named after t
    he table name, compression, frame and the fromdate.
    If the 'pickle' directory does not exist, it will be created.

    Args:
    fromdate (str): The start date of the data in the format of "YYYY-MM-DD HH:mm:ss".

    Returns:
    bool: Returns True if the file was successfully saved, False otherwise.
    """
    pre_fix = f"pickle/{feed._table}_{feed.compression}_{feed.feed.period}"
    pre_fix = pre_fix + f"_{arrow.get(fromdate).format('YYYY_MM_DD_HH_mm')}_"
    filename = pre_fix + f"to_{arrow.get(todate).format('YYYY_MM_DD_HH_mm')}.pkl"
    try:
        dataframe.to_pickle(filename)
        logger.info(f"saved: {filename}")
    except (FileNotFoundError, OSError):
        dataframe.to_pickle("fullon/"+filename)


def get_oldest_timestamp(feed: FullonFeed) -> str:
    with Database_ohlcv(exchange=feed.feed.exchange_name,
                        symbol=feed.symbol) as dbase:
        oldest = dbase.get_oldest_timestamp()
    if not oldest:
        oldest = ""
    return oldest


def load_dataframe(feed: FullonFeed,
                   todate: str,
                   fromdate: str = '') -> pandas.DataFrame:
    """
    Load data from a pickle file and return a Pandas DataFrame.
    Args:
        filename (str): The name of the pickle file to load.
    Returns:
        DataFrame: The loaded data as a DataFrame.
    """
    oldest = get_oldest_timestamp(feed=feed)
    if fromdate:
        if arrow.get(oldest) > arrow.get(fromdate):
            logger.warning("Cant fetch data older that %s", oldest)
            logger.warning("using %s as fromdate parameter, but maybe you want to check", oldest)
            fromdate = oldest
    else:
        fromdate = fromdate
    _todate = arrow.get(todate)
    pre_fix = f"pickle/{feed._table}_{feed.compression}_{feed.feed.period}"
    filename = f"{pre_fix}_{arrow.get(fromdate).format('YYYY_MM_DD_HH_mm')}.started"
    if os.path.exists(filename):
        _wait_for_flagfile(filename)
    dataframe = _load_from_pickle(feed=feed, fromdate=fromdate, todate=todate)
    if dataframe.empty:
        _create_empty_flagfile(filename)
        rows = _fetch_data_from_db(feed=feed, todate=_todate, fromdate=arrow.get(fromdate))
        dataframe = _to_df(rows=rows)  # only works if self.dataframe is not set
        _save_to_pickle(dataframe=dataframe,
                        feed=feed,
                        fromdate=fromdate,
                        todate=todate)
    try:
        os.remove(filename)
    except FileNotFoundError:
        if os.path.exists("fullon/"+filename):
            os.remove("fullon/"+filename)
    return dataframe


def data_quality_checks(data: pandas.DataFrame) -> bool:
    """
    Perform data quality checks on the given DataFrame and return True if checks pass.

    Args:
        data (pandas.DataFrame): The DataFrame to be checked.

    Returns:
        bool: True if data passes the quality checks, False otherwise.
    """
    # Check for missing values
    missing_values = data.isnull().sum()
    if missing_values.any():
        logger.error("Data check failed: There are missing values.")
        return False

    # Check for duplicate rows
    duplicate_rows = data.duplicated().sum()
    '''
    if duplicate_rows > 0:
        logger.error("Data check failed: There are duplicate rows. Could be due to missing trade dates")
        all_duplicates = data[data.duplicated(keep=False)]
        print(all_duplicates)
        return False
    '''
    return True


def set_target(data: pandas.DataFrame,
               target: str,
               steps: int) -> Tuple[pandas.DataFrame, pandas.DataFrame]:
    """
    Gets the target from a dataframe, shifts N steps to look ahead in prediction.
    """
    steps = int(steps)
    try:
        future = (data[target].shift(-steps) > 0)
        data = data.drop(columns=[target])
        return future.dropna(), data
    except KeyError:
        logger.error("Target (%s) not found in data", target)
        return pandas.DataFrame(), data


def scale_data(data: pandas.DataFrame) -> Tuple[pandas.DataFrame, MinMaxScaler]:
    """
    Scale the numerical features in the DataFrame, excluding boolean features.

    Args:
        data (pandas.DataFrame): The DataFrame with numerical features to be scaled.

    Returns:
        pandas.DataFrame: The DataFrame with scaled features.
    """
    scaler = MinMaxScaler()
    # Selecting numerical columns to scale, excluding booleans
    numerical_cols = data.select_dtypes(include=['float64', 'int64']).columns
    bool_cols = data.select_dtypes(include=['bool']).columns
    cols_to_scale = [col for col in numerical_cols if col not in bool_cols]
    if cols_to_scale:
        data[cols_to_scale] = scaler.fit_transform(data[cols_to_scale])
        return data, scaler
    return data, None


def rescale_data(data: pandas.DataFrame, scaler: MinMaxScaler) -> pandas.DataFrame:
    """
    Scale the numerical features in the DataFrame, excluding boolean features.

    Args:
        data (pandas.DataFrame): The DataFrame with numerical features to be scaled.
        scaler (MinMaxScaler): The scaler to use

    Returns:
        pandas.DataFrame: The DataFrame with scaled features.
    """
    # Selecting numerical columns to scale, excluding booleans
    if scaler:
        numerical_cols = data.select_dtypes(include=['float64', 'int64']).columns
        bool_cols = data.select_dtypes(include=['bool']).columns
        cols_to_scale = [col for col in numerical_cols if col not in bool_cols]
        data[cols_to_scale] = scaler.fit_transform(data[cols_to_scale])
    return data


def save_scaler(fromdate: str,
                todate: str,
                feed: FullonFeed,
                scaler: object) -> bool:
    """
    Saves a given scaler object to a file, constructing the filename based on provided parameters.
    The filename includes the strategy name, symbol, compression, period, and the date range.
    This allows for easy identification and retrieval of the specific scaler for future use.
    Parameters:
    - fromdate (str): The start date for the data range the scaler is associated with.
    - todate (str): The end date for the data range the scaler is associated with.
    - feed (FullonFeed): An object containing details about the trading feed, including the strategy name, symbol, compression, and period.
    - scaler (object): The scaler object to be saved. This should be a fitted scaler instance from scikit-learn or a similar library.

    The function constructs a filename and uses joblib to save the scaler object to this file. If an error occurs during saving,
    it prints an error message.

    Returns:
    bool
    """
    scaler_file = ''
    try:
        symbol = feed.symbol.replace('/', '_')
        pre_fix = f"scaler_{feed.strategy_name}_{symbol}_{feed.compression}_{feed.period}"
        scaler_file = f"predictors/{pre_fix}_{fromdate}_to_{todate}.joblib"
        scaler_file = scaler_file.replace(' ', '_')
        joblib.dump(scaler, scaler_file)
        return True
    except FileNotFoundError:
        logger.error(f"The directory for {scaler_file} was not found.")
    except PermissionError:
        logger.error(f"Permission denied: unable to write to {scaler_file}.")
    except IOError as e:
        logger.error(f"Failed to save scaler due to an I/O error: {e}.")
    return False


def try_loading(fromdate: str,
                todate: str,
                feed: FullonFeed,
                predictor: str,
                saved: bool = True) -> Tuple[Any, str, Any, str]:
    """
    Attempts to load a trained model from a specified file path.
    If the file exists, it returns the loaded model and its filename.
    Otherwise, it returns None and the expected filename.

    Parameters:
    - data (pandas.DataFrame): The DataFrame containing the
                               data associated with the model.
    - feed (FullonFeed): The feed object containing details like symbol,
                         compression, and period used to construct the filename
    - predictor (str): The name of the predictor model,
                       used as part of the filename.
    - saved (bool): weather to use the saved one or create a new one.

    Returns:
    Tuple[Any, str]: A tuple containing the loaded model (or None if not found) and the constructed filename for the model.
    """
    symbol = feed.symbol.replace('/', '_')
    pre_fix = f"reg_{feed.strategy_name}_{symbol}_{feed.compression}_{feed.period}"
    regressor_file = f"predictors/{pre_fix}_{predictor}.joblib"
    regressor_file = regressor_file.replace(' ', '_')
    regressor = None
    if os.path.exists(regressor_file) and saved:
        regressor = joblib.load(regressor_file)
    else:
        regressor_file = f"predictors/{pre_fix}_{fromdate}_to_{todate}_{predictor}.joblib"
        regressor_file = regressor_file.replace(' ', '_')
        if os.path.exists(regressor_file) and saved:
            regressor = joblib.load(regressor_file)
    pre_fix = f"scaler_{feed.strategy_name}_{symbol}_{feed.compression}_{feed.period}"
    scaler_file = f"predictors/{pre_fix}.joblib"
    scaler_file = scaler_file.replace(' ', '_')
    scaler = None
    if os.path.exists(scaler_file) and saved:
        scaler = joblib.load(scaler_file)
    else:
        scaler_file = f"predictors/{pre_fix}_{fromdate}_to_{todate}.joblib"
        scaler_file = scaler_file.replace(' ', '_')
        if os.path.exists(scaler_file) and saved:
            scaler = joblib.load(scaler_file)
    return (regressor, regressor_file, scaler, scaler_file)


def train_regressors(data: pandas.DataFrame,
                     target: pandas.DataFrame,
                     filenames: Dict,
                     regressors: List) -> Dict:
    """
    Trains a variety of regression and classification models specified in the
    'regressors' list.
    Each model is fitted on the provided data and target, then saved to a file
    specified in the 'filenames' dictionary.

    Parameters:
    - data (pd.DataFrame): The feature data used for training the models.
    - target (pd.DataFrame): The target labels or values for the models.
    - filenames (Dict): A dictionary mapping regressor names to filenames where
    the trained models will be saved.
    - regressors (Dict): A dictionary where keys are the names of the
    regressors and values are any additional parameters (currently unused).

    Returns:
    Dict: A dictionary of the trained regressor models,
    keyed by the regressor names.
    """
    X_train, _, y_train, _ = train_test_split(data,
                                              target,
                                              test_size=0.001,
                                              random_state=42)
    predictors: Dict = {}
    for regressor in regressors:
        predictor = None
        match regressor:
            case 'RandomForestClassifier':
                predictor = RandomForestClassifier(n_estimators=100,
                                                   random_state=42)
            case 'GradientBoostingClassifier':
                predictor = GradientBoostingClassifier(n_estimators=100,
                                                       random_state=42)
            case 'RandomForestRegressor':
                predictor = RandomForestRegressor(n_estimators=100,
                                                  random_state=42)
            case 'XGBClassifier':
                predictor = XGBClassifier(n_estimators=100,
                                          random_state=42)
            case 'LGBMClassifier':
                predictor = LGBMClassifier(n_estimators=100,
                                           random_state=42)
            case 'CatBoostClassifier':
                predictor = CatBoostClassifier(n_estimators=1000,
                                               random_state=42,
                                               verbose=0)
            case 'MLPClassifier':
                predictor = MLPClassifier(random_state=42,
                                          max_iter=1000)
            case _:
                return {}
        predictor.fit(X_train, y_train)
        joblib.dump(predictor, filenames[regressor])
        predictors[regressor] = predictor
    return predictors


def inverse_scale(predictions, scaler) -> pandas.DataFrame:
    """
    Inverse scale the predictions using the given MinMaxScaler.

    Args:
        predictions (array-like): The predictions to be inverse scaled.
        scaler (MinMaxScaler): The scaler used for original scaling.

    Returns:
        pandas.DataFrame: DataFrame containing the unscaled predictions.
    """
    # Reshape the predictions to match the shape expected by the scaler
    predictions_reshaped = predictions.reshape(-1, 1)

    # Inverse transform the predictions
    unscaled_predictions = scaler.inverse_transform(predictions_reshaped)

    # Create a DataFrame from the unscaled predictions
    unscaled_predictions_df = pandas.DataFrame(unscaled_predictions, columns=['predictions'])
    return unscaled_predictions_df


def set_ohlcv_bull_features(data):
    # Define functions for each candle type
    def is_bullish_marubozu(row):
        # No or very small wicks
        return row['close'] > row['open'] and min(row['high'] - row['close'], row['open'] - row['low']) < 0.1 * (row['close'] - row['open'])

    def is_hammer(row):
        # Long lower wick, short upper wick, small body
        body = abs(row['close'] - row['open'])
        wick_lower = min(row['close'], row['open']) - row['low']
        return row['close'] > row['open'] and wick_lower > 2 * body and (row['high'] - max(row['close'], row['open'])) < body

    def is_inverted_hammer(row):
        # Long upper wick, short lower wick, small body
        body = abs(row['close'] - row['open'])
        wick_upper = row['high'] - max(row['close'], row['open'])
        return row['close'] > row['open'] and wick_upper > 2 * body and (min(row['close'], row['open']) - row['low']) < body

    def is_bullish_engulfing(row, prev_row):
        # Current candle's body completely engulfs the previous candle's body
        return row['close'] > row['open'] and prev_row['open'] > prev_row['close'] and row['open'] < prev_row['close'] and row['close'] > prev_row['open']

    def is_piercing_line(row, prev_row):
        # Similar to bullish engulfing but doesn't completely engulf the previous candle
        return row['close'] > row['open'] and prev_row['open'] > prev_row['close'] and row['open'] < prev_row['close'] and row['close'] > prev_row['open'] and row['close'] < (prev_row['open'] + prev_row['close']) / 2

    def is_bullish_harami(row, prev_row):
        # Previous candle is bearish and larger, current candle is bullish and fully within the range of the previous candle
        return row['close'] > row['open'] and prev_row['open'] > prev_row['close'] and row['open'] > prev_row['close'] and row['close'] < prev_row['open']

    # Apply the functions to create binary features
    data['Bullish_Marubozu'] = data.apply(is_bullish_marubozu, axis=1)
    data['Hammer'] = data.apply(is_hammer, axis=1)
    data['Inverted_Hammer'] = data.apply(is_inverted_hammer, axis=1)
    # For patterns that depend on the previous row, use shift to align the previous row with the current row for comparison
    shifted_data = data.shift(1)
    data['Bullish_Engulfing'] = data.apply(lambda row: is_bullish_engulfing(row, shifted_data.loc[row.name]), axis=1)
    data['Piercing_Line'] = data.apply(lambda row: is_piercing_line(row, shifted_data.loc[row.name]), axis=1)
    data['Bullish_Harami'] = data.apply(lambda row: is_bullish_harami(row, shifted_data.loc[row.name]), axis=1)
    return data


def set_ohlcv_bear_features(data):
    # Define functions for each candle type
    def is_bearish_marubozu(row):
        body = abs(row['close'] - row['open'])
        wick_upper = row['high'] - max(row['close'], row['open'])
        wick_lower = min(row['close'], row['open']) - row['low']
        return row['close'] < row['open'] and min(wick_upper, wick_lower) < 0.1 * body

    def is_hanging_man(row, prev_row):
        body = abs(row['close'] - row['open'])
        wick_lower = min(row['close'], row['open']) - row['low']
        return body > 0 and wick_lower > 2 * body and row['close'] < row['open'] and prev_row['close'] > prev_row['open']

    def is_shooting_star(row, prev_row):
        body = abs(row['close'] - row['open'])
        wick_upper = row['high'] - max(row['close'], row['open'])
        return body > 0 and wick_upper > 2 * body and row['close'] < row['open'] and prev_row['close'] > prev_row['open']

    def is_bearish_engulfing(row, prev_row):
        return row['close'] < row['open'] and prev_row['open'] < prev_row['close'] and row['open'] > prev_row['close'] and row['close'] < prev_row['open']

    def is_evening_star(data, index):
        if index < 2:
            return False
        first = data.iloc[index - 2]
        second = data.iloc[index - 1]
        third = data.iloc[index]
        return first['close'] > first['open'] and second['close'] > second['high'] and third['open'] < third['close'] and third['close'] < first['close']

    def is_bearish_harami(row, prev_row):
        return row['close'] < row['open'] and prev_row['open'] < prev_row['close'] and row['open'] < prev_row['close'] and row['close'] > prev_row['open']

    # Apply the functions to create binary features
    data['Bearish_Marubozu'] = data.apply(is_bearish_marubozu, axis=1)
    shifted_data = data.shift(1)
    data['Hanging_Man'] = data.apply(lambda row: is_hanging_man(row, shifted_data.loc[row.name]), axis=1)
    data['Shooting_Star'] = data.apply(lambda row: is_shooting_star(row, shifted_data.loc[row.name]), axis=1)
    data['Bearish_Engulfing'] = data.apply(lambda row: is_bearish_engulfing(row, shifted_data.loc[row.name]), axis=1)
    data['Evening_Star'] = [is_evening_star(data, index) for index in range(data.shape[0])]
    data['Bearish_Harami'] = data.apply(lambda row: is_bearish_harami(row, shifted_data.loc[row.name]), axis=1)
    return data

@staticmethod
def set_ohlcv_features(data):
    """
    """
    data['Price_Range'] = data['high'] - data['low']
    data['Mid_Price'] = (data['high'] + data['low']) / 2
    data['Typical_Price'] = (data['high'] + data['low'] + data['close']) / 3
    data['Price_Change'] = data['close'] - data['open']
    data['Directional'] = data.apply(lambda row: 1 if row['close'] > row['open'] else (-1 if row['close'] < row['open'] else 0), axis=1)
    # Cast 'Directional' to a specific type, e.g., int64 or float64
    data['Directional'] = data['Directional'].astype('float64')
    data['OC_Midpoint'] = (data['open'] + data['close']) / 2
    return data


"""
if not data.empty:
    if data_quality_checks(data=data):
        data = set_features(data=data)
        print(data)
        target, data = set_target(data=data, steps=1)
        data, scaler = scale_data(data=data)
        #target, scaler_y = scale_data(data=data)
        X_train, X_test, y_train, y_test = train_test_split(data, target, test_size=0.2, random_state=42)
        regressor = RandomForestClassifier(n_estimators=100, random_state=42)
        regressor.fit(X_train, y_train)
        y_pred_proba = regressor.predict_proba(X_test)[:, 1]  # Get probabilities for the class 'True'
        threshold = 0.5
        y_pred_bool = y_pred_proba > threshold  # Convert probabilities to boolean

        y_pred_df = pandas.DataFrame({'Predicted': y_pred_bool, 'Actual': y_test}, index=X_test.index)
        y_pred_df = y_pred_df.sort_index()
        print(y_pred_df.tail(60))
        true_predictions = y_pred_df['Predicted']
        pred_count = true_predictions.sum()
        print("Attempts: ", pred_count)
        true_positives = true_predictions & (y_pred_df['Actual'] == True)
        number_of_true_positives = true_positives.sum()
        # Print the Result
        print(f"Number of True Positives: {number_of_true_positives}")
        print("Hit rate: ", number_of_true_positives/pred_count)


        '''
        regressor = RandomForestRegressor(n_estimators=100, random_state=42)

        regressor.fit(X_train, y_train)
        y_pred = regressor.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        print(f"Mean Squared Error: {mse}")

        # Step 1: Ensure y_test is a Series with the appropriate index
        # If y_test is not already a Series with the date index, you may need to adjust this part
        y_test_series = pandas.Series(y_test, index=X_test.index)

        # Step 2: Create a DataFrame from y_pred
        y_pred_df = pandas.DataFrame(y_pred, index=X_test.index, columns=['Predicted'])

        # Step 3: Add the actual values to the DataFrame
        y_pred_df['Actual'] = y_test_series

        print(y_pred_df.head(20))


        date_index = X_test.index
        y_pred_df = pandas.DataFrame(y_pred, index=date_index, columns=['Predicted'])
        print(y_pred_df)


        #now y_pred is like a series... how can i get it as a pandas with date as index?
        '''



"""