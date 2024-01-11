"""
description
"""
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals)
import os
from collections import deque
import pandas
import numpy as np
import backtrader as bt
import arrow
from libs.btrader.fullonfeed import FullonFeed
from libs.database_ohlcv import Database as Database_ohlcv
from libs import settings, log
from typing import Optional
import time

# from libs import settings
logger = log.fullon_logger(__name__)


class FullonSimFeed(FullonFeed):
    """ Fullon Sim for step by step simul, very slow but reliable """

    time_factor: int
    last_date: Optional[arrow.arrow.Arrow] = None
    dataframe = None
    MAX_TRADE_MINUTES = 525600  # bars
    noise = settings.NOISE

    def _load(self):
        """Description"""
        if self._state == self._ST_HISTORY:
            self._fetch_ohlcv()
            self._load_ohlcv()
            return True
        if self._state == self._ST_OVER:
            return False
        return False

    def start(self, count=1):
        super().start()
        self.time_factor = self.get_time_factor()
        self.last_date = self.get_last_date().floor('day').shift(minutes=0)
        #self.last_date = self.get_last_date()
        self.last_moments = self.params.mainfeed.last_date.shift(  # pylint: disable=no-member
            seconds=-self.time_factor)
        self.last_moments = bt.date2num(self.last_moments.datetime)
        seed_value = int(time.time()) + os.getpid()
        np.random.seed(seed_value)

    def _save_to_df(self, rows: list):
        """
        Saves the data to a DataFrame.
        :param rows: The data to be saved
        """
        def _create_dataframe(rows):
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
        try:
            if self.dataframe.empty:
                self.dataframe = _create_dataframe(rows)
        except AttributeError:
            self.dataframe = _create_dataframe(rows)

    def _save_to_pickle(self, fromdate: str):
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
        pre_fix = f"pickle/{self._table}_{self.compression}_{self.feed.period}"
        filename = pre_fix + f"_{arrow.get(fromdate).format('YYYY_MM_DD_HH_mm')}"
        filename += f"_to_{self.last_date.format('YYYY_MM_DD_HH_mm')}.pkl"
        try:
            self.dataframe.to_pickle(filename)
            print(f"saved: {filename}")
        except (FileNotFoundError, OSError):
            os.mkdir('pickle')
            self.dataframe.to_pickle(filename)

    def _load_from_pickle(self, fromdate: str) -> list[tuple[str, float, float, float, float, float]]:
        """Load data from a pickle file and return a Pandas DataFrame.
        Args:
            fromdate (str): The date of the data to load, in the format 'YYYY-MM-DD'.
        Returns:
            pd.DataFrame: The loaded data.
        """
        pre_fix = f"pickle/{self._table}_{self.compression}_{self.feed.period}"
        filename = pre_fix + f"_{arrow.get(fromdate).format('YYYY_MM_DD_HH_mm')}"
        filename += f"_to_{self.last_date.format('YYYY_MM_DD_HH_mm')}.pkl"
        rows = []
        try:
            with open(filename, 'rb') as file:
                self.dataframe = pandas.read_pickle(file)
                x_date = bt.num2date(self.params.mainfeed.fromdate)  # pylint: disable=no-member
                x_date = arrow.get(x_date).shift(
                    seconds=-self.time_factor).format('YYYY-MM-DD HH:mm:ss')
                new_df = self.dataframe[self.dataframe.index >= x_date]
                new_df.reset_index(inplace=True)
                rows = new_df.values.tolist()

        except FileNotFoundError:
            logger.error(f"Pickle file ({filename}) not found")
        return rows

    def _add_gaussian_noise(self, std_scale=0.003):
        """
        Adds Gaussian noise to the 'open', 'high', 'low', 'close' and 'volume' columns.
        :param std_scale: standard deviation scale for noise, default to 5% of the standard deviation of the data.
        """
        noise_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in noise_cols:
            std_dev = self.dataframe[col].std() * std_scale  # standard deviation (5% of the std_dev of the data)
            mean = 0  # mean
            noise = np.random.normal(mean, std_dev, size=len(self.dataframe))  # generate Gaussian noise
            self.dataframe[col] += noise  # add the noise to the dataframe column

    @staticmethod
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
            time.sleep(sleep_time)
            loop_count += 1

        if loop_count >= max_loops:
            raise Exception("Timeout waiting for flagfile to be deleted.")

    @staticmethod
    def _create_empty_flagfile(filename):
        """
        Create an empty flag file with the given filename.
        Parameters:
            filename (str): The path to the flag file.
        """
        with open(filename, 'w'):
            pass

    def fetch_data_from_db(self):
        """
        Returns:
            rows: The fetched data.
        """
        todate = self.last_date
        todate = todate.format('YYYY-MM-DD HH:mm:ss ZZ')
        with Database_ohlcv(exchange=self.feed.exchange_name,
                            symbol=self.symbol) as dbase:
            return dbase.fetch_ohlcv(table=self._table,
                                     compression=self.compression,
                                     period=self.feed.period,
                                     fromdate=self.p.fromdate,
                                     todate=todate)

    def _resample(self):
        # Determine the resampling rule based on the compression and feed period
        if self.compression != 1 and self.feed.period.lower() == 'minutes':
            resampling_rule = f'{self.compression}T'
        elif self.feed.period.lower() in ['days']:
            time_unit = 'D'
            resampling_rule = f'{self.compression}{time_unit}'
        else:
            return  # No resampling needed

        # Resample each column individually
        open_resampled = self.dataframe['open'].resample(resampling_rule).first()
        high_resampled = self.dataframe['high'].resample(resampling_rule).max()
        low_resampled = self.dataframe['low'].resample(resampling_rule).min()
        close_resampled = self.dataframe['close'].resample(resampling_rule).last()
        volume_resampled = self.dataframe['volume'].resample(resampling_rule).sum()

        # Combine the resampled data into a single DataFrame
        self.dataframe = pandas.DataFrame({
            'open': open_resampled,
            'high': high_resampled,
            'low': low_resampled,
            'close': close_resampled,
            'volume': volume_resampled
        })

    def _fetch_ohlcv(self):
        """
        Fetch the OHLCV data for the current instance.
        This method orchestrates the whole process of data fetching,
        including checking for existing data, waiting for flag files,
        and saving the fetched data.
        """
        if self.result:
            return
        pre_fix = f"pickle/{self._table}_{self.compression}_{self.feed.period}"
        filename = f"{pre_fix}_{arrow.get(self.p.fromdate).format('YYYY_MM_DD_HH_mm')}.started"

        if os.path.exists(filename):
            self._wait_for_flagfile(filename)

        pkl_exists = True
        rows = self._load_from_pickle(fromdate=self.p.fromdate)
        if not rows:
            self._create_empty_flagfile(filename)
            pkl_exists = False
            rows = self.fetch_data_from_db()
        if rows:
            self._save_to_df(rows=rows)  # only works if self.dataframe is not set
            if not pkl_exists:
                self._save_to_pickle(fromdate=self.p.fromdate)
                os.remove(filename)
            if self.noise:
                if not self.ismainfeed:
                    # Step 1: Store the original DataFrame
                    orig_df = self.dataframe.copy()
                    # Step 2: Assign mainfeed DataFrame to self.dataframe
                    self.dataframe = self.params.mainfeed.dataframe.copy()
                    # Step 3: Resample self.dataframe. Assuming _resample() returns a resampled DataFrame
                    self._resample()
                    # Step 4: Merge the beginning of orig_df onto self.dataframe
                    # Finding the first common index
                    common_start = orig_df.index.intersection(self.dataframe.index).min()
                    if common_start:
                        overlap = orig_df.index.intersection(self.dataframe.index)
                        orig_df = orig_df.drop(overlap)  # Drop overlapping indices from orig_df
                        self.dataframe = pandas.concat([orig_df, self.dataframe.loc[common_start:]])
                else:
                    self._add_gaussian_noise()
                rows = self.dataframe.reset_index().values.tolist()
            self.last_date = arrow.get(rows[-1][0])
            self.last_moments = self.params.mainfeed.last_date.shift(  # pylint: disable=no-member
                seconds=-self.time_factor)
            self.last_moments = bt.date2num(self.last_moments.datetime)
            self.result = deque(rows)
            if self.compression != 1 and self.feed.period != 'minutes':
                self.adjust_dataframe()
        else:
            self._empty_bar()

    def adjust_dataframe(self):
        """ohlcv need to shift time, so that when calculating the RSI or other indicators 
        is easier to handle dates
        """
        dataframe = self.dataframe
        last_date = dataframe.index[-1]
        last_date = arrow.get(last_date).shift(minutes=self.bar_size_minutes).datetime
        # Ensure the new date is naive
        last_date = last_date.replace(tzinfo=None)
        # Drop the first row, shift the dataframe rows down
        dataframe.loc[last_date] = np.nan
        self.dataframe = dataframe.shift(1).dropna()

    def _empty_bar(self):
        """
        Reset the state of the object to its initial state
        and discard any data that has been collected so far.
        """
        self.result = []
        self._state = self._ST_OVER

    def _load_ohlcv(self):
        """Description"""
        try:
            one_row = self.result.popleft()
        except IndexError:
            self._state = self._ST_OVER
            return False
        except AttributeError as error:
            if 'object has no attribute' in str(error):
                self.result = []
                return False
            raise
        self._load_ohlcv_line(one_row=one_row)
        if len(self.result) == 0:
            self._empty_bar()
        return True
