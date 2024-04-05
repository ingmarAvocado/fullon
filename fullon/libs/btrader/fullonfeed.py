"""
description
"""
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals)
from typing import List, Union, Any, Literal, Optional
from collections import deque
from backtrader.feed import DataBase
import backtrader as bt
import arrow
from libs.database_ohlcv import Database as DataBase_ohclv
from libs import cache
import time


class FullonFeed(DataBase):
    """
    A data feed class that supports loading historical and live data from a database.

    Attributes:
        params (tuple): A tuple of parameter values for the data feed.
        feed (object): The data feed object.
        symbol (str): The symbol being traded.
        dbase (object): The database connection object.
        helper (object): The helper object.
        pos (int): The position in the market.
        broker (object): The broker object.
        dataframe (object): The pandas DataFrame object.
        pairs (bool): A flag indicating whether pairs trading is enabled.
        exit (bool): A flag indicating whether to exit the program.
        compression (int): The compression value for the data feed.
        _last_id (str): The last processed trade ID for ohlcv data.
        result (deque): A deque of ohlcv data rows.
        timeframe (int): The timeframe for the data feed.
        _todate (str): The todate value for the data feed.
        _ST_LIVE (int): The state value for the live data state.
        _ST_OVER (int): The state value for the finished data state.
        _state (int): The current state of the data feed.
        feed2 (object): Another instance of the data feed object.

    Methods:
        __init__: Initializes a new instance of the FullonFeed class.
        __del__: Destroys the FullonFeed object.
        start: Starts the data feed.
        _load: Loads data from the database.
        _fetch_tick: Fetches tick data from the cache.
        _get_table: Gets the table name for the data feed.
        get_last_date: Gets the last timestamp for the data feed.
        _load_ticks: Loads tick data.
        _get_time_factor: Gets the time factor for the data feed.
        _set_to_date: Sets the todate value for the data feed.
        _fetch_ohlcv: Fetches ohlcv data from the database.
        _empty_bar: Fills the data feed with empty data.
        _load_ohlcv_line: Loads one row of ohlcv data.
        _load_ohlcv: Loads ohlcv data.
        haslivedata: Checks if the data feed has live data.
        islive: Checks if the data feed is live.
    """

    params = (
        ('feed', ''),
        ('helper', ''),
        ('broker', ''),
        ('mainfeed', None),
        ('fromdate', ''),
        ('fromdate2', ''),
        ('compression', 0),
        ('timeframe', bt.TimeFrame.Ticks),
    )

    _ST_LIVE: int = 0
    _ST_HISTORY: int = 1
    _ST_OVER: int = 2
    _state: int = 0
    _table: str = ""
    _last_id: str = ""
    symbol: str = ""
    helper: object = None
    last_moments: Optional[float] = None
    bar_size_minutes: int = 0
    ismainfeed = False

    def __init__(self):
        """
        Initializes a new instance of the FullonFeed class.
        """
        self.feed = self.params.feed  # pylint: disable=E1101
        self.symbol = self.feed.symbol  # pylint: disable=E1101
        self.helper = self.params.helper  # pylint: disable=E1101
        self.bot_id = self.params.helper.id
        self.pos = 0
        self.broker = self.params.broker  # pylint: disable=E1101
        self.exit = False
        self.compression = int(self.params.compression)  # pylint: disable=E1101
        self.result = None
        self.timeframe = self.params.timeframe  # pylint: disable=E1101
        self._todate = None
        self._set_bar_size()
        if self.params.mainfeed is None:  # pylint: disable=E1101
            self.params.mainfeed = self
            self.ismainfeed = True

    def __del__(self):
        """
        Destroys the FullonFeed object.
        """
        try:
            del self.helper
        except AttributeError:
            pass

    def start(self, count: int = 5) -> None:   # pylint: disable=W0613
        """
        Starts the data feed.

        Args:
            count (int): The number of rows to process.
        """
        DataBase.start(self)
        self._state = self._ST_HISTORY
        self._table = self._get_table()

    def _load(self) -> bool:
        """
        Loads data from the database.
        """
        res = False
        if self._state == self._ST_LIVE:
            res = self._load_ticks()
            return res
        if self._state == self._ST_HISTORY:
            self._fetch_ohlcv()
            res = self._load_ohlcv()
            return res
        return res

    def _set_bar_size(self):
        """
        Sets the bar size in minutes based on the feed period and compression.

        The feed period can be 'minutes', 'days', or 'weeks',
        and the bar size is calculated accordingly.

        :attribute self.feed.period: Feed period, must be one of 'minutes', 'days', or 'weeks'
        :type self.feed.period: str
        :attribute self.compression: Compression factor to multiply with the base period
        :type self.compression: int
        :attribute self.bar_size_minutes: Resulting bar size in minutes
        :type self.bar_size_minutes: int
        """
        match self.feed.period.lower():
            case 'minutes':
                self.bar_size_minutes = self.compression
            case 'days':
                self.bar_size_minutes = self.compression*24*60
            case 'weeks':
                self.bar_size_minutes = self.compression*24*60*7

    def _fetch_tick(self, rest: float = 1.0) -> Any:
        """
        Fetches tick data from the cache.

        Args:
            rest (float): The time to rest between requests.

        Returns:
            tuple: A tuple containing the tick data.
        """
        try:
            with cache.Cache() as mem:
                res = mem.get_ticker(exchange=self.feed.exchange_name,
                                     symbol=self.symbol)
                time.sleep(rest)
            utc_now = arrow.utcnow().format('YYYY-MM-DD HH:mm:ss.SSS')
            if res[0] == 0:
                time.sleep(1)
                return self._fetch_tick(rest=rest+rest)
            res = (utc_now, res[0], res[0], res[0], res[0], res[0])
            return res
        except KeyboardInterrupt:
            return None

    def _get_table(self) -> str:
        """
        Gets the table name for the data feed.

        Returns:
            str: The table name.
        """
        table = self.feed.exchange_name + "_" + self.symbol
        table = table.replace('/', '_')
        table = table.replace('-', '_')
        with DataBase_ohclv(exchange=self.feed.exchange_name,
                            symbol=self.symbol) as dbase:
            if dbase.table_exists(schema=table, table="trades"):
                return table + ".trades"
            if dbase.table_exists(schema=table, table="candles1m"):
                return table + ".candles1m"
            raise ValueError(f"_get_table: Error, cant continue: \
                tables for schema {table} dont exist")

    def get_last_date(self) -> arrow.arrow.Arrow:
        """
        Gets the last date in the database.

        Returns:
            Arrow: The last date.
        """
        with DataBase_ohclv(exchange=self.feed.exchange_name,
                            symbol=self.symbol) as dbase:
            row = dbase.get_latest_timestamp(table2=self._table)
        return arrow.get(row)

    def _load_ticks(self) -> bool:
        """
        Loads tick data from the database.

        Returns:
            bool: True if data was loaded successfully, False otherwise.
        """
        tick = self._fetch_tick()
        if not tick:
            self._state = self._ST_OVER
            return False
        tstamp, topen, thigh, tlow, tclose, tvolume = tick
        self._last_id = tstamp
        self.params.fromdate = tstamp
        self.lines.datetime[0] = bt.date2num(arrow.get(tstamp))
        self.lines.open[0] = float(topen)
        self.lines.high[0] = float(thigh)
        self.lines.low[0] = float(tlow)
        self.lines.close[0] = float(tclose)
        self.lines.volume[0] = float(tvolume)
        return True

    def get_time_factor(self) -> int:
        """
        Gets the time factor for the data feed.

        Returns:
            int: The time factor.
        """
        period_map = {
            "ticks": 1,
            "minutes": 60,
            "days": 86400,
            "weeks": 604800,
            "months": 2629746  # assuming 30.44 days per month
        }
        period = self.feed.period.lower()
        return self.compression * period_map.get(period, 0)

    def _empty_bar(self):
        """
        Fills the bar with NaN values.
        """
        if self._state == self._ST_LIVE:
            self.result = []
            self._last_id = ''

    def _fetch_ohlcv(self) -> None:
        """
        Fetches OHLCV data from the database.
        """
        if self.result:
            return
        todate = arrow.utcnow().datetime
        # Here i must call with compression 1 and minutes, why? resampler
        # but fullon_resampler makes its own query to timescaledb, so
        # loads from database directy rather than here, however doesnt
        # work if this doesnt load some data, to try to feed into the resampler,
        # so we send at least to periods of data. For now we use 2 full days,
        # but if one of the feeds is into the weekly this might not work as it
        # will need  2 weeks
        with DataBase_ohclv(exchange=self.feed.exchange_name,
                            symbol=self.symbol) as dbase:
            rows = dbase.fetch_ohlcv(table=self._table,
                                     compression=1,
                                     period='Minutes',
                                     fromdate=self.p.fromdate2.datetime,   # pylint: disable=E1101
                                     todate=todate)
        if rows:
            self._last_id = rows[-1][0]
            self.result = deque(rows)
        else:
            self._empty_bar()

    def _load_ohlcv_line(self, one_row: List[Union[str, float]], num: int = 0) -> None:
        """
        Loads one row of OHLCV data into the data feed.

        Args:
            one_row (List[Union[str, float]]): The row of OHLCV data.
            num (int): The index of the row to load (default: 0).
        """
        self.params.fromdate = one_row[0]
        self.lines.datetime[num] = bt.date2num(arrow.get(one_row[0]).datetime)
        self.lines.open[num] = float(one_row[1])
        self.lines.high[num] = float(one_row[2])
        self.lines.low[num] = float(one_row[3])
        self.lines.close[num] = float(one_row[4])
        self.lines.volume[num] = float(one_row[5])
        self.lines.openinterest[num] = 0

    def _load_ohlcv(self) -> bool:
        """
        Loads OHLCV data into the data feed.

        Returns:
            bool: Whether or not the loading was successful.
        """
        try:
            one_row = self.result.popleft()
            self._load_ohlcv_line(one_row=one_row)
        except AttributeError as error:
            if 'object has no attribute' in str(error):
                self.result = []
                self._state = self._ST_LIVE  # set state to _ST_LIVE
                return False
            raise
        except TypeError as error:
            if 'NoneType' in str(error):
                # so here i should make it so that we read (not pop) the next value.
                # if its noll null, we use its contents to fix bad_row and then
                # self._load_ohlcv_line(bad_row) and one_row
                # if its still null we loop until we find one row that is not n
                for res in self.result:
                    if res[1] is not None:
                        one_row = list(one_row)  # Convert tuple to list
                        for n in range(1, 5):
                            one_row[n] = res[n]
                        self._load_ohlcv_line(one_row=tuple(one_row))
                        break
            raise
        if len(self.result) == 0:
            self._state = self._ST_LIVE
        return True

    def haslivedata(self) -> bool:
        """
        Returns whether or not the data feed has live data.
        """
        return self._state == self._ST_LIVE

    def islive(self) -> bool:
        '''Returns ``True`` to notify ``Cerebro`` that preloading and runonce
        should be deactivated'''
        return self._state == self._ST_LIVE
