import pandas as pd
from backtrader.feed import DataBase
import backtrader as bt
from pandas_ta.volatility import pdist
from libs.database_ohlcv import Database as DataBase_ohclv
import arrow
from typing import Any
import numpy as np


class FullonFeedResampler:
    """ this class can prepare DataBase resampled feed to add mehtods aparameters """

    _data: DataBase
    _period: str
    feed: object
    delta_time: int
    bars: int
    bar_size_minutes: int = 0

    def prepare(self,
                data: DataBase,
                bars: int,
                timeframe: Any,
                compression: int,
                fromdate: str,
                feed: str) -> DataBase:
        """
        Prepares the data feed by adding necessary attributes and methods.

        :param data: The data feed to prepare.
        :return: The prepared data feed.
        """
        self._data = data
        self._bars = bars
        # Define the DataFrame columns
        columns = {0: "date", 1: "open", 2: "high", 3: "low", 4: "close", 5: "volume"}
        dataframe = pd.DataFrame(columns=columns.values())

        # Set the index to the 'date' column
        dataframe.set_index("date", inplace=True)

        # set time frame and period in case is needed
        setattr(data, 'timeframe', timeframe)
        setattr(data, 'compression', compression)
        setattr(data, 'exchange', feed.exchange_name)
        setattr(data, 'symbol', feed.symbol)
        setattr(data, '_table', self._get_table(exchange=data.exchange,
                                                symbol=data.symbol))

        # Set the dataframe and append_row method as attributes of the data feed
        setattr(data, 'dataframe', dataframe)
        setattr(data, 'append_row', self.append_row.__get__(data))

        # Wrap the originalnext method and set the wrapped version as an attribute of data
        original_next = data.next
        setattr(data, 'next', self._custom_next(original_next))
        bar_size = self._set_bar_size(timeframe=timeframe, compression=compression)
        setattr(data, 'bar_size_minutes', bar_size)
        self._period = self._get_timeframe(self._data.timeframe)
        self.fill_starting_dataframe(fromdate=fromdate)
        setattr(data, 'feed', feed)
        return data

    def _set_bar_size(self, timeframe: int, compression: int) -> int:
        bar_size_minutes = 0
        match timeframe:
            case bt.TimeFrame.Minutes:
                bar_size_minutes = compression
            case bt.TimeFrame.Days:
                bar_size_minutes = compression*24*60
            case bt.TimeFrame.Weeks:
                bar_size_minutes = compression*24*60*7
        return bar_size_minutes

    def fill_starting_dataframe(self, fromdate: str) -> None:
        """
        Fills starting DataFrame.
        """
        to_date = arrow.utcnow()
        with DataBase_ohclv(exchange=self._data.exchange,
                            symbol=self._data.symbol) as dbase:
            rows = dbase.fetch_ohlcv(table=self._data._table,
                                     compression=self._data.compression,
                                     period=self._period,
                                     fromdate=arrow.get(fromdate).datetime,  # Convert fromdate string to datetime
                                     todate=to_date.datetime)

        last_date = arrow.get(rows[-1][0])
        if to_date > last_date:
            del rows[-1]
        self._data.dataframe = self._create_dataframe(rows=rows)

    def append_row(self) -> None:
        """
        Appends a new row of OHLCV (Open, High, Low, Close, Volume) data to the internal DataFrame.

        This method calculates the appropriate time range for the new data row, fetches the corresponding
        OHLCV data from the database, and appends it to the internal DataFrame. The method ensures that
        the new data is only appended if the current time is beyond the 'to_date' of the OHLCV data, 
        indicating that the latest period has completed and new data is available.
        """

        # Calculate the 'from_date' for the new data row.
        # This is based on the last date in the DataFrame, shifted by 'delta_time' minutes.
        # 'delta_time' represents the time interval of each OHLCV data point.
        from_date = arrow.get(self._data.dataframe.index[-1]).shift(minutes=self.delta_time)

        # Calculate the 'to_date' for the new data row.
        # This is 'from_date' shifted by 'delta_time' minutes, minus one microsecond,
        # to accurately represent the closing time of the OHLCV data.
        to_date = arrow.get(from_date).shift(minutes=self.delta_time, microseconds=-1)

        # Check if the current time is before 'to_date'.
        # If it is, the latest OHLCV period has not completed, so we do not append new data yet.
        if arrow.utcnow() < to_date:
            return

        # Fetch the new OHLCV data row from the database for the time range between 'from_date' and 'to_date'.
        with DataBase_ohclv(exchange=self._data.exchange, symbol=self._data.symbol) as dbase:
            rows = dbase.fetch_ohlcv(table=self._data._table,
                                     compression=self._data.compression,
                                     period=self._period,
                                     fromdate=from_date,
                                     todate=to_date)

        # Extract the OHLCV values from the fetched data.
        # The first element of the row contains the timestamp, and the next five elements are OHLCV.
        next_date = arrow.get(rows[0][0]).format('YYYY-MM-DD HH:mm:ss')
        ohlcv_values = rows[0][1:6]

        # Append the new OHLCV data to the internal DataFrame.
        # The new data is indexed by the 'next_date' and contains the OHLCV values.
        self._data.dataframe.loc[next_date, ['open', 'high', 'low', 'close', 'volume']] = ohlcv_values

    def _custom_next(self, original_next):
        """
        Wraps the original _next method to call append_row before returning its result.

        :param original_next: The original _load method of the data feed.
        :return: The wrapped _load method.
        """
        def wrapper(*args, **kwargs):
            result = original_next()
            if result:
                self.append_row()
            return result
        return wrapper

    def _get_table(self, exchange, symbol) -> str:
        """
        Gets the table name for the data feed.

        Returns:
            str: The table name.
        """
        table = exchange + "_" + symbol
        table = table.replace('/', '_')
        table = table.replace('-', '_')
        with DataBase_ohclv(exchange=exchange,
                            symbol=symbol) as dbase:
            if dbase.table_exists(schema=table, table="trades"):
                return table + ".trades"
            if dbase.table_exists(schema=table, table="candles1m"):
                return table + ".candles1m"
            raise ValueError(f"_get_table: Error, cant continue: \
                tables for schema {table} dont exist")

    def _get_timeframe(self, period: int) -> str:
        '''
        returns timeframe in string
        '''
        period_map = {
            bt.TimeFrame.Ticks: 'ticks',
            bt.TimeFrame.Minutes: 'minutes',
            bt.TimeFrame.Days: 'days',
            bt.TimeFrame.Weeks: 'weeks',
            bt.TimeFrame.Months: 'months',
        }
        return period_map[period]

    def _create_dataframe(self, rows: list) -> pd.DataFrame:
        """
        Creates a DataFrame from a list of OHLCV data rows.

        This method takes a list of OHLCV (Open, High, Low, Close, Volume) data rows,
        converts them into a properly formatted DataFrame, sets the appropriate column
        names, and ensures that all data types are correct. It also calculates the time
        delta between the last two data points to determine the interval of the OHLCV data.

        Args:
            rows (list): A list of lists, where each inner list contains OHLCV data.

        Returns:
            pd.DataFrame: A DataFrame containing the OHLCV data with a datetime index.
        """

        # Create a DataFrame from the provided rows
        dataframe = pd.DataFrame(rows)

        # Rename columns for readability and set the 'date' column as the index
        dataframe.rename(columns={0: "date", 1: "open", 2: "high", 3: "low", 4: "close", 5: "volume"}, inplace=True)
        dataframe.set_index("date", inplace=True)

        # Convert all columns except 'date' to numeric values
        columns_to_convert = dataframe.columns.difference(['date'])
        dataframe[columns_to_convert] = dataframe[columns_to_convert].apply(pd.to_numeric)

        # Convert the index to datetime format
        dataframe.index = pd.to_datetime(dataframe.index)

        # Calculate the time delta between the last two data points
        # This is used to determine the interval of the OHLCV data
        last_two_dates = dataframe.index[-2:]
        try:
            self.delta_time = (last_two_dates[1] - last_two_dates[0]).total_seconds() / 60
        except IndexError:
            # If there are not enough data points to calculate the delta, return an empty DataFrame
            return pd.DataFrame()
        return dataframe
