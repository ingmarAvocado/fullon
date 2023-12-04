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
    delta_time: int
    bars: int
    bar_size_minutes: int = 0

    def prepare(self,
                data: DataBase,
                bars: int,
                timeframe: Any,
                compression: int,
                fromdate: str,
                exchange: str,
                symbol: str) -> DataBase:
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
        setattr(data, 'exchange', exchange)
        setattr(data, 'symbol', symbol)
        setattr(data, 'table', self._get_table(exchange=exchange, symbol=symbol))

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
        return data

    def _set_bar_size(self, timeframe: int, compression: int) -> int:
        bar_size_minutes = 0
        match timeframe:
            case bt.TimeFrame.Minutes:
                bar_size_minutes = compression
            case bt.TimeFrame.Hours:
                bar_size_minutes = compression*60
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
            rows = dbase.fetch_ohlcv(table=self._data.table,
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
        Appends the current data line to the internal DataFrame.
        """
        from_date = self._data.dataframe.index[-1]
        to_date = arrow.get(from_date).shift(minutes=self.delta_time)
        if arrow.utcnow() < arrow.get(to_date):
            return
        # Fetch new rows from the database.
        to_date = to_date + pd.Timedelta(microseconds=-1)
        with DataBase_ohclv(exchange=self._data.exchange,
                            symbol=self._data.symbol) as dbase:
            rows = dbase.fetch_ohlcv(table=self._data.table,
                                     compression=self._data.compression,
                                     period=self._period,
                                     fromdate=from_date,
                                     todate=to_date)
            # Get the rows as a DataFrame.
        next_date = arrow.get(rows[0][0]).shift(minutes=self.delta_time).format('YYYY-MM-DD HH:mm:ss')
        ohlcv_values = rows[0][1:6]
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
        dataframe = pd.DataFrame(rows)
        dataframe.rename(columns={0: "date",
                                  1: "open",
                                  2: "high",
                                  3: "low",
                                  4: "close",
                                  5: "volume"}, inplace=True)
        dataframe.set_index("date", inplace=True)
        columns_to_convert = dataframe.columns.difference(['date'])
        dataframe[columns_to_convert] = dataframe[columns_to_convert].apply(pd.to_numeric)
        dataframe.index = pd.to_datetime(dataframe.index)
        # Calculate the new date for the last row
        last_two_dates = dataframe.index[-2:]
        try:
            self.delta_time = (last_two_dates[1] - last_two_dates[0]).total_seconds() / 60
        except IndexError:
            return pd.DataFrame()
        last_date = arrow.get(last_two_dates[1]).shift(minutes=self.delta_time).datetime
        # Ensure the new date is naive
        last_date = last_date.replace(tzinfo=None)
        dataframe.loc[last_date] = np.nan
        # Drop the first row, shift the dataframe rows down
        dataframe = dataframe.shift(1).dropna()
        dataframe = dataframe.dropna()
        return dataframe
