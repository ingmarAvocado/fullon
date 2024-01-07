"""
description
"""
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals)
import itertools
from collections import deque
import pandas
import arrow
import backtrader as bt
from libs.btrader.fullonsimfeed import FullonSimFeed
from typing import Tuple, Optional, Union
from libs.database_ohlcv import Database as Database_ohclv


# from libs import settings


class FullonEventFeed(FullonSimFeed):
    """ Fullon Fast Sim for event base simul, fast but need to double check"""
    event_timeout = None
    timeout = 0
    trailing_stop = None
    razor_dates = []

    def _load(self):
        """Description"""
        # if its a live queue
        if self._state == self._ST_HISTORY:
            self._fetch_ohlcv()
            self._load_ohlcv()
            return True
        if self._state == self._ST_OVER:
            return False
        return False

    def _next_timeout(self, cur_time: str) -> arrow.Arrow:
        """
        Determine the time of the next timeout.

        If a timeout has been set, it will be used. Otherwise, the timeout will
        be set to MAX_TRADE_MINUTES after the current time.

        Parameters:
        - cur_time (str): The current time.

        Returns:
        - arrow.Arrow: The time of the next timeout.
        """
        if self.timeout:
            timeout = arrow.get(self.timeout)
        else:
            # Get the duration of a single bar in the relevant unit (minutes,  days, etc.)
            bar_duration = {self.feed.period: self.compression}
            # calculate the total shift duration for MAX_TRADE_MINUTES
            maxi = self.MAX_TRADE_MINUTES
            total_duration = {self.feed.period: self.compression * maxi}
            timeout = arrow.get(cur_time).shift(**total_duration)
        return timeout

    def get_event_date(self,
                       event: str,
                       price: float,
                       cur_ts: arrow.Arrow,
                       limit: Optional[arrow.Arrow] = None) -> Tuple[arrow.Arrow, float]:
        """
        Get the timestamp of the first occurrence of the given
        event within the specified time range.
        Parameters:
            event (str): The name of the event to check for.
                Can be either "take_profit" or "stop_loss".
            cur_ts (datetime.datetime): The start of the time range in which to
                search for the event.
            limit (str, optional): The end of the time range in which to search
                for the event.   Defaults to the next timeout.
        Returns:
            arrow: The timestamp of the first occurrence of the event
            within the specified time range.
        """
        if not limit:
            alimit = self._next_timeout(cur_time=cur_ts)
        cur_ts = pandas.to_datetime(cur_ts.format('YYYY-MM-DD HH:mm:ss'))
        limit = pandas.to_datetime(alimit.format('YYYY-MM-DD HH:mm:ss'))
        #self._razor_dataframe(timestamp=cur_ts)
        df_ohlcv = self.dataframe.loc[cur_ts:limit].copy()
        #df_ohlcv = self._fetch_ohlcv_as_df(start=cur_ts, end=alimit)
        match event:
            case "take_profit":
                if self.pos > 0:
                    date_ohlcv = df_ohlcv.loc[df_ohlcv['close'] >= price]
                else:
                    date_ohlcv = df_ohlcv.loc[df_ohlcv['close'] < price]
            case "stop_loss":
                if self.pos > 0:  # Stoping a Long
                    date_ohlcv = df_ohlcv.loc[df_ohlcv['close'] <= price]
                else:  # stoping a short
                    date_ohlcv = df_ohlcv.loc[df_ohlcv['close'] > price]
            case "trailing_stop":
                date_ohlcv = self._trailing_stop(df_ohlcv=df_ohlcv.copy(), price=price)
                try:
                    price = date_ohlcv['TrailingStop'].iloc[0]
                except (IndexError, UnboundLocalError):
                    pass
        try:
            return_date = arrow.get(date_ohlcv.index[0])
        except (IndexError, UnboundLocalError):
            # return_date = arrow.get(self.params.mainfeed.result[-2][0])
            # pylint-disable: no-member
            return_date = arrow.get(bt.num2date(self.last_moments))
            if alimit < return_date:
                return_date = alimit
        return (return_date, price)

    def _trailing_stop(self, df_ohlcv: pandas.DataFrame, price: float) -> pandas.DataFrame:
        """
        Calculate and return a DataFrame with trailing stop information.

        Parameters:
        df_ohlcv (pandas.DataFrame): Input DataFrame with OHLCV data.
        price (float): The initial price used for calculating the trailing stop.

        Returns:
        pandas.DataFrame: The original DataFrame with additional columns for
        running max/min, trailing stop, and previous trailing stop. It also filters
        the rows based on whether the close price is lower/higher than the previous trailing stop.
        """
        if self.pos > 0:  # Trailing stop for a Long position
            df_ohlcv.loc[:, 'RunningMax'] = df_ohlcv.loc[:, 'close'].expanding().max()
            df_ohlcv.loc[:, 'TrailingStop'] = df_ohlcv.loc[:, 'RunningMax'] * (1 - self.trailing_stop/100)
        else:  # Trailing stop for a Short position
            df_ohlcv.loc[:, 'RunningMin'] = df_ohlcv.loc[:, 'close'].expanding().min()
            df_ohlcv.loc[:, 'TrailingStop'] = df_ohlcv.loc[:, 'RunningMin'] * (1 + self.trailing_stop/100)


        # Get the previous time's TrailingStop
        df_ohlcv.loc[:, 'PreviousTrailingStop'] = df_ohlcv['TrailingStop'].shift(1)

        # Set the initial stop loss
        df_ohlcv.loc[df_ohlcv.index[0], 'PreviousTrailingStop'] = price

        # Filter rows based on the comparison of 'close' and 'PreviousTrailingStop'
        if self.pos > 0:  # If Long
            df_ohlcv = df_ohlcv[df_ohlcv['close'] < df_ohlcv['PreviousTrailingStop']]
        else:  # If Short
            df_ohlcv = df_ohlcv[df_ohlcv['close'] > df_ohlcv['PreviousTrailingStop']]        
        return df_ohlcv

    def get_max_price(self, start: arrow.Arrow, end: arrow.Arrow) -> Tuple[float, arrow.Arrow]:
        """
        Get the highest price within the specified date range.

        :param start: The start date of the range.
        :param end: The end date of the range.
        :return: The highest price and its date within the range.
        """
        start = pandas.to_datetime(start.format('YYYY-MM-DD HH:mm:ss'))
        end = pandas.to_datetime(end.format('YYYY-MM-DD HH:mm:ss'))
        df_ohlcv = self.dataframe.loc[start:end]
        max_price_row = df_ohlcv.loc[df_ohlcv['close'].idxmax()]
        return max_price_row['close'], arrow.get(max_price_row.name)

    def get_min_price(self, start: arrow.Arrow, end: arrow.Arrow) -> Tuple[float, arrow.Arrow]:
        """
        Get the lowest price within the specified date range.

        :param start: The start date of the range.
        :param end: The end date of the range.
        :return: The lowest price and its date within the range.
        """
        start = pandas.to_datetime(start.format('YYYY-MM-DD HH:mm:ss'))
        end = pandas.to_datetime(end.format('YYYY-MM-DD HH:mm:ss'))
        df_ohlcv = self.dataframe.loc[start:end]
        min_price_row = df_ohlcv.loc[df_ohlcv['close'].idxmin()]
        return min_price_row['close'], arrow.get(min_price_row.name)

    @staticmethod
    def _slice_deque(ddeque: deque, start: int, stop: int) -> deque:
        """
        Given a deque, rotate the deque to the left by the given start
        position, slice the deque from start to stop
        and return the sliced deque.
        """
        ddeque.rotate(-start)
        mslice = list(itertools.islice(ddeque, 0, stop - start))
        mslice.pop()
        return deque(mslice)

    def _load_ohlcv(self):
        """Description"""
        one_row = self._jump_to_next_event()
        self._load_ohlcv_line(one_row=one_row)
        if len(self.result) == 0:
            self._empty_bar()
        return True

    def _razor_dataframe(self, timestamp):
        """
        Cuts the DataFrame at specific intervals based on the target date.

        Razor points are created at 10%, 20%, 30%, etc., of the original DataFrame's length.
        If the target date has passed any of these points, the old dates are cut from the DataFrame.

        :param target_date: The date to compare with the razor points
        :type target_date: datetime-like
        """
        # Number of rows in the original DataFrame
        total_rows = len(self.dataframe)

        # Create razor points if they do not exist
        if not self.razor_dates:
            razor_points = [int(total_rows * x / 100) for x in range(10, 101, 10)]
            for point in razor_points:
                self.razor_dates.append(self.dataframe.index[point-1])

        # Iterate over razor dates to find the cut point
        for razor_date in self.razor_dates:
            if razor_date >= timestamp:
                # Cut the old dates from the DataFrame
                self.dataframe = self.dataframe.loc[razor_date:]
                break

    def _jump_to_next_event(self) -> Optional[list]:
        """
        Determine the next event and jump to it.
        Sometimes this means we do a single step, which is necessary when
        opening and closing a position.

        Returns:
        list: The next event in the queue, or an empty list if the queue is empty.
        """
        # Read the first event in the list
        # Initialize steps to 0
        steps = 0
        event = self.result.popleft()
        if not self.event_timeout:
            return event
        if self.event_timeout.timestamp() < arrow.get(event[0]).timestamp():
            return event
        steps = (self.event_timeout.timestamp() -
                 arrow.get(event[0]).timestamp()) / self.time_factor
        # Get the size of the result_tick list
        size = len(self.result)
        # because we poped an element to the list, we need to account for it.
        # we use int to round down a float. Steps must be int.
        steps = int(steps) - 1
        if steps <= 0:
            return event
        # compression({self._compression}) event({event[0]}) last_event {self.result[-1][0]}")
        if size <= steps:
            return event
        self.event_timeout = None
        self.result = self._slice_deque(self.result, steps, size + 1)
        return self.result.popleft() if self.result else []

    def _fetch_ohlcv_as_df(self,
                           start: Union[str, arrow.Arrow],
                           end: Union[str, arrow.Arrow]) -> pandas.DataFrame:
        """
        Fetch the OHLCV data for the current instance from a given start to end date.

        Parameters:
        - start (Union[str, arrow.Arrow]): The start time for the OHLCV data in
             'YYYY-MM-DD HH:mm:ss ZZ' format or as an arrow.Arrow object.
        - end (Union[str, arrow.Arrow]): The end time for the OHLCV data in
            'YYYY-MM-DD HH:mm:ss ZZ' format or as an arrow.Arrow object.

        Returns:
        - pandas.DataFrame: A pandas DataFrame containing the OHLCV data.
        """
        # If start or end are strings, convert them to arrow.Arrow objects
        if isinstance(start, str):
            start = arrow.get(start)
        if isinstance(end, str):
            end = arrow.get(end)

        with Database_ohclv(exchange=self.feed.exchange_name, symbol=self.symbol) as dbase:
            # Fetch the OHLCV data from the database
            rows = dbase.fetch_ohlcv(table=self._table,
                                     compression=self.compression,
                                     period=self.feed.period,
                                     fromdate=start.format('YYYY-MM-DD HH:mm:ss'),
                                     todate=end.format('YYYY-MM-DD HH:mm:ss'))

        # Convert the fetched data to a pandas DataFrame
        df = pandas.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        # Set timestamp as the index and convert it to a datetime object
        df.set_index('timestamp', inplace=True)
        df.index = pandas.to_datetime(df.index)
        return df
