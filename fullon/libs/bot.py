from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals
)
import sys
import time
import importlib
import arrow
import backtrader as bt
from libs import cache, log, strategy
from libs.database import Database
from libs.database_ohlcv import Database as Database_ohlcv
from libs.btrader.fullonbroker import FullonBroker
from libs.btrader.basebroker import BaseBroker
from libs.btrader.fullonresampler import FullonFeedResampler
from typing import Optional, Any
from setproctitle import setproctitle

FEED_CLASSES = {
    "FullonFeed": "libs.btrader.fullonfeed.FullonFeed",
    "FullonSimFeed": "libs.btrader.fullonsimfeed.FullonSimFeed",
    "FullonEventFeed": "libs.btrader.fulloneventfeed.FullonEventFeed"
}

logger = log.fullon_logger(__name__)


class Bot:

    test = False

    def __init__(self, bot_id: int, bars: int = 0) -> None:
        """
        Initialize the bot instance.

        :param bot_id: The ID of the bot.
        :param bars: The number of bars used in the bot. Defaults to 0.
        """
        with Database() as dbase:
            try:
                bot = dbase.get_bot_list(bot_id=bot_id)[0]
            except IndexError:
                self.id = None
                logger.warning(f"Bot id {bot_id} not found or not active")
                return None
            self.bars = bars
            self.strategy = dbase.get_str_name(bot_id=bot_id)
            self.uid = bot.uid
            self.id = bot.bot_id
            self.bot_name = bot.name
            self.dry_run = bot.dry_run
            self.start_time = arrow.utcnow()
            self.simulresults = {}
            self.str_params = self._str_set_params(dbase=dbase)
            self.cache = cache.Cache()
            self.str_feeds = self._set_feeds(
                dbase.get_bot_feeds(bot_id=bot.bot_id), dbase=dbase)
            if not self.str_feeds:
                logger.error(
                    "__init__: It is not possible to run a simulation without feeds")
                exit("bye")

    def __del__(self) -> None:
        """
        Clean up the bot instance before deleting.
        """
        pass

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['cache']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.cache = cache.Cache()

    def _set_feeds(self, feeds, dbase) -> list:
        """
        Set the feeds for the bot.

        :param feeds: A list of feeds to be used by the bot.
        :return: A list of modified feeds.
        """
        ret_feeds = []
        exchanges = dbase.get_exchange(user_id=self.uid)
        tradeable = {}
        exch_dict = {}
        for exch in exchanges:
            _exch = exch.to_dict()
            exch_dict[_exch['cat_name']] = _exch['name']
        for feed in feeds:
            try:
                if tradeable[feed.exchange_name][feed.symbol] is True:
                    setattr(feed, 'trading', False)
            except KeyError:
                setattr(feed, 'trading', True)
                if feed.exchange_name not in tradeable.keys():
                    tradeable[feed.exchange_name] = {}
                tradeable[feed.exchange_name][feed.symbol] = True
            setattr(feed, 'user_ex_name', exch_dict[feed.exchange_name])
            ret_feeds.append(feed)
        return ret_feeds

    def _str_set_params(self, dbase) -> dict:
        """
        Set the strategy parameters for the bot.

        :return: A dictionary of strategy parameters.
        """
        def convert_value(value):
            try:
                if '.' in value:  # If '.' is in the string, try parsing as float
                    return float(value)
                else:  # Else try parsing as int
                    return int(value)
            except ValueError:  # If both float and int casting fail, keep as string
                return value

        strs = dbase.get_str_params(bot_id=self.id)
        if not strs:
            logger.error("Can't continue without params, make sure your bot has params")
            exit()
        params = {}
        for s in strs:
            name = s[0]
            value = s[1]
            params[name] = convert_value(value)
        base_params = vars(dbase.get_base_str_params(bot_id=self.id))
        for p, k in base_params.items():
            if k is not None:
                params[p] = convert_value(str(k))
        params['helper'] = self
        return params

    def extend_str_params(self, test_params: dict) -> None:
        """
        Extend the strategy parameters with additional test parameters.

        :param test_params: A dictionary containing additional test parameters.
        """
        if test_params:
            for key, value in test_params.items():
                self.str_params[key] = value

    def _set_timeframe(self, period: str) -> bt.TimeFrame:
        """
        Convert a string representation of a time frame to the corresponding constant value in the backtrader library.
        """
        # define a dictionary that maps the period strings to the corresponding constants
        period_map = {
            "ticks": bt.TimeFrame.Ticks,
            "minutes": bt.TimeFrame.Minutes,
            "days": bt.TimeFrame.Days,
            "weeks": bt.TimeFrame.Weeks,
            "months": bt.TimeFrame.Months
        }
        # convert the period to lowercase to ensure it matches the keys in the dictionary
        period = period.lower()
        # return the corresponding constant from the dictionary, or None if the period is not in the dictionary
        return period_map.get(period)

    def backload_from(self, bars: int = 100) -> arrow.Arrow:
        """
        Shift the current time by a certain amount, based on the 'frame' and 'compression' parameters.
        Returns a new Arrow object with the shifted time.
        """
        # define a dictionary that maps each period string to the corresponding time unit for Arrow
        period_map = {
            "ticks": "minutes",
            "minutes": "minutes",
            "hours": "hours",
            "days": "days",
            "weeks": "weeks",
            "months": "months"
        }
        # get the feed for the last data and calculate the time shift based on the compression and simul_backtest
        feed = self.str_feeds[-1]
        timeframe = self._set_timeframe(period=feed.period)
        time_unit = period_map.get(feed.period.lower())
        if time_unit is None:
            raise ValueError("Unrecognized period: {}".format(feed.period))
        shift_args = {time_unit: -feed.compression * bars}
        # shift the current time by the specified amount and set the time to midnight
        if timeframe >= 5:
            return arrow.utcnow().shift(**shift_args).floor('day')
        else:
            return arrow.utcnow().shift(**shift_args).floor('minute')

    def _pair_feeds(self, cerebro: bt.Cerebro) -> bool:
        """
        Pair up the data feeds in the Cerebro object by setting the 'feed2' attribute of each feed to the
        corresponding feed in the pair.
        """
        # Determine the number of data feeds in the Cerebro object
        num_feeds = len(cerebro.datas)
        # If there is an odd number of data feeds, raise an error
        if num_feeds % 2 != 0:
            msg = f"Number of data feeds must be even, current num feeds {num_feeds}"
            logger.error(msg)
            return False
        # Determine the number of pairs of data feeds
        num_pairs = num_feeds // 2
        # Loop over each pair of data feeds and pair them up
        for i in range(num_pairs):
            # Set the 'feed2' attribute of the first feed to be the second feed in the pair
            cerebro.datas[i].feed2 = cerebro.datas[i + num_pairs]
            # Set the 'feed2' attribute of the second feed to be the first feed in the pair
            cerebro.datas[i + num_pairs].feed2 = cerebro.datas[i]
        return True

    def _sim_feeds_can_start(self, feed: object, fromdate: arrow.Arrow) -> bool:
        """
        Checks if all feeds in `self.str_feeds` can start. A feed can start if the following conditions are met:
        - Checks that the feed exists and has enough data to start from requested date
        Returns:
            bool: `True` if all feeds can start, `False` otherwise.
        """
        with Database_ohlcv(
                exchange=feed.exchange_name, symbol=feed.symbol) as dbase:
            first_date = dbase.get_oldest_timestamp()
        if first_date:
            if fromdate <= arrow.get(first_date):
                mesg = f"Can't start apparently no data availabe at from date {fromdate}, for {feed.symbol}"
                logger.error(mesg)
                return False
        else:
            mesg = "Can't start apparently no data availabe for feed {feed.symbol}"
            logger.error(mesg)
            return False
        return True

    def _feeds_can_start(self, stop_signal, retries=20) -> bool:
        """
        Checks if all feeds can start based on certain conditions.
        It will check for the conditions for a number of times defined by 'retries' before giving up.

        Args:
            retries (int): The number of times to retry if any condition is not met. Default to 20.

        Returns:
            bool: `True` if all feeds can start, `False` otherwise.
        """
        for feed in self.str_feeds:
            with cache.Cache() as store:
                # Check if the OHLCV process for the feed is 'Synced' and its timestamp is not older than 120 seconds.
                if not self.check_ohlcv(feed, store):
                    return self.retry_or_fail(retries, f"OHLCV for {feed.exchange_name}:{feed.symbol} is not synced", stop_signal)

                # Check if the ticker for the feed is running and its timestamp is not older than 120 seconds.
                if not self.check_ticker(feed, store):
                    return self.retry_or_fail(retries, f"Ticker for {feed.exchange_name}:{feed.symbol} doesn't seem to be working", stop_signal)

                # Check if the account associated with `self.uid` is being updated and its timestamp is not older than 120 seconds.
                if not self.check_account(store):
                    return self.retry_or_fail(retries, f"Account {self.uid} is not being updated", stop)

        return True

    def check_ohlcv(self, feed, store) -> bool:
        """
        Checks if the OHLCV process for a feed is 'Synced' and its timestamp is not older than 120 seconds.

        Args:
            feed: The feed to check.
            store: The cache store.

        Returns:
            bool: `True` if the OHLCV process for the feed is 'Synced' and its timestamp is not older than 120 seconds, `False` otherwise.
        """
        res = store.get_process(tipe='ohlcv', key=f'{feed.exchange_name}:{feed.symbol}')
        return res and 'Synced' in res['message'] and arrow.get(res['timestamp']).shift(seconds=120) > arrow.utcnow()

    def check_ticker(self, feed, store) -> bool:
        """
        Checks if the ticker for a feed is running and its timestamp is not older than 120 seconds.

        Args:
            feed: The feed to check.
            store: The cache store.

        Returns:
            bool: `True` if the ticker for the feed is running and its timestamp is not older than 120 seconds, `False` otherwise.
        """
        res = store.get_ticker(exchange=feed.exchange_name, symbol=feed.symbol)
        return arrow.get(res[1]).shift(seconds=600) > arrow.utcnow()

    def check_account(self, store) -> bool:
        """
        Checks if the account associated with `self.uid` is being updated and its timestamp is not older than 120 seconds.

        Args:
            store: The cache store.

        Returns:
            bool: `True` if the account associated with `self.uid` is being updated and its timestamp is not older than 120 seconds, `False` otherwise.
        """
        for feed in self.str_feeds:
            res = store.get_process(tipe="account", key=feed.user_ex_name)
            try:
                if arrow.get(res['timestamp']).shift(seconds=120) < arrow.utcnow():
                    return False
            except KeyError:
                logger.error("Account component not started for this account")
                exit()
        return True

    def retry_or_fail(self, retries: int, message: str, stop_signal) -> bool:
        """
        Logs a message and retries `_feeds_can_start()` or returns `False` if no more retries are left.

        Args:
            retries (int): The number of times left to retry.
            message (str): The message to log.
            stop_signal (event): proces stop signal

        Returns:
            bool: The result of `_feeds_can_start()` if there are retries left, `False` otherwise.
        """
        logger.info(message + " will retry a few times")
        if retries == 0:
            return False
        for i in range(0, 15):
            if stop_signal.is_set():
                retries = 1
                break
            time.sleep(1)
        return self._feeds_can_start(retries=retries-1, stop_signal=stop_signal)

    def _load_feeds(self, cerebro: bt.Cerebro,
                    warm_up: int,
                    event: bool,
                    ofeeds: list) -> bool:
        """
        Loads the feeds into the cerebro instance for backtesting.

        Parameters:
        - cerebro: A `backtrader.Cerebro` instance.
        - warm_up: The number of bars to warm up the strategy with.
        - event: A boolean indicating whether to use the event feed or the simulation feed.

        Returns:
        - None
        """
        # Initialize the first feed as None
        feed0 = None
        # Loop through all the feeds and add them to the cerebro instance
        for num, feed in enumerate(self.str_feeds):
            # Clear the simulation results list for this feed
            self.simulresults[num] = []
            # Set the timeframe for the feed
            timeframe = self._set_timeframe(period=feed.period)
            if feed.period.lower() == "ticks":
                self.str_feeds[num].period = "minutes"
                feed.period = "minutes"
            compression = feed.compression
            try:
                compression = ofeeds[num]['compression']
            except KeyError:
                pass
            try:
                period = ofeeds[num]['period']
            except KeyError:
                pass
            # Adjust the start date if the feed has compression > 1
            if compression > 1:
                fromdate = self.backload_from(bars=self.bars+warm_up).floor('day')
            else:
                # Set the start date for the backtest
                fromdate = self.backload_from(bars=self.bars).floor('day')
            if not self._sim_feeds_can_start(feed=feed, fromdate=fromdate):
                logger.error("Feeds can't start, exiting bot startup")
                return False
            # Choose the feed class based on the event parameter
            feed_name = "FullonEventFeed" if event else "FullonSimFeed"
            # Get the feed class object dynamically
            feed_class = FEED_CLASSES[feed_name]
            feed_module, feed_class_name = feed_class.rsplit(".", 1)
            FeedClass = getattr(importlib.import_module(feed_module), feed_class_name)
            # Create a new broker object for this feed
            # Create a new data object using the chosen feed class
            data = FeedClass(
                feed=feed,
                timeframe=timeframe,
                compression=int(compression),
                helper=self,
                fromdate=fromdate,
                mainfeed=feed0)
            # Add the data object to the cerebro instance
            cerebro.adddata(data, name=f'{num}')
            # Store the first feed object for later use
            if num == 0:
                feed0 = data
            del data
        return True

    def run_simul_loop(self,
                       feeds: dict = {},
                       visual: bool = False,
                       test_params: dict = {},
                       warm_up: int = 0,
                       event: bool = False) -> Any:
        """
        Run a simulation loop.

        :param feeds: A dictionary containing feeds. Defaults to an empty dictionary.
        :param visual: A flag indicating whether to enable visualization. Defaults to False.
        :param test_params: A dictionary containing test parameters. Defaults to an empty dictionary.
        :param warm_up: Warm-up period for the simulation. Defaults to 0.
        :param event: A flag indicating whether it's an event. Defaults to False.
        :return: Simulation results or an error message.
        """
        if not self.id:
            return False

        self.extend_str_params(test_params)
        cerebro = bt.Cerebro()

        if event:
            strategy.STRATEGY_TYPE = "event"
        else:
            strategy.STRATEGY_TYPE = "backtest"
        broker = self.get_broker(dry=True)
        cerebro.setbroker(broker)

        module = importlib.import_module(
            'strategies.' + self.strategy + '.strategy',
            package='Strategy')
        self.str_params['size'] = None
        cerebro.addstrategy(module.Strategy, **self.str_params)
        if not self._load_feeds(cerebro=cerebro, warm_up=warm_up, event=event, ofeeds=feeds):
            return False
        if not self._pair_feeds(cerebro=cerebro):
            return False

        r = []
        try:
            r = cerebro.run(live=True)
        except:
            raise
        '''
        except (TypeError, KeyError) as error:
            logger.warning(
                "Error can't run Bot, probably loading a parameter that the bot does not have: %s", str(error))
            return ["ERROR Can't run bot"]
        except ValueError as error:
            if 'Cant continue without funds' in  str(error):
                return ['Error: ran out of funds']
        '''

        if r == []:
            return [
                "ERROR: Either nothing happened or could not pass strategy __init__, check log"]
        imgtitle = ""
        if visual:
            now = arrow.utcnow().format('YYYY-MM-DD_HH:mm:ss')
            p = ""
            for key, value in test_params.items():
                p = p + str(key) + "_" + str(value) + "_"
            imgtitle = "tmp/simul_" + self.strategy + "_" + p + "_" + now + ".png"
            cerebro.plot(style='candles', saveimg=imgtitle)
        self.str_params.pop('helper')
        self.str_params.pop('pre_load_bars')
        for num in range(0, len(self.simulresults)):
            self.simulresults[num].append({"strategy": self.strategy,
                                           "params": self.str_params,
                                           "symbol": self.str_feeds[num].symbol,
                                           "imgtitle": imgtitle})
        del cerebro
        return self.simulresults

    def _load_live_feeds(self, cerebro: bt.Cerebro, bars: int):
        """
        Loads the feeds into the cerebro instance for backtesting.

        Parameters:
        - cerebro: A `backtrader.Cerebro` instance.
        Returns:
        - None
        """
        # Initialize the first feed as None
        feed0 = None
        fromdate = self.backload_from(bars=bars)
        feed_map = {}
        for num, feed in enumerate(self.str_feeds):
            compression = int(feed.compression)
            period = feed.period
            timeframe = self._set_timeframe(period=period)
            # Choose the feed class based on the event parameter
            feed_class = FEED_CLASSES['FullonFeed']
            feed_module, feed_class_name = feed_class.rsplit(".", 1)
            FeedClass = getattr(importlib.import_module(feed_module), feed_class_name)
            # Create a new broker object for this feed
            # Create a new data object using the chosen feed class
            #  Since when the database should load
            if timeframe == bt.TimeFrame.Ticks:
                data = FeedClass(feed=feed,
                                 timeframe=1,
                                 compression=1,
                                 helper=self,
                                 fromdate=fromdate,
                                 mainfeed=None)
                cerebro.adddata(data, name=f'{num}')
                try:
                    feed_map[feed.exchange_name].update({feed.symbol: data})
                except KeyError:
                    feed_map[feed.exchange_name] = {feed.symbol: data}
            else:
                try:
                    parent_data = feed_map[feed.exchange_name][feed.symbol]
                except KeyError:
                    logger.error('Resampled feed %s symbol does not match main feed symbol', num)
                    return
                resampled_data = cerebro.resampledata(parent_data,
                                                      timeframe=timeframe,
                                                      compression=compression,
                                                      name=f'{num}')
                sampler = FullonFeedResampler()
                sampler.prepare(data=resampled_data,
                                bars=bars,
                                timeframe=timeframe,
                                compression=compression,
                                exchange=feed.exchange_name,
                                fromdate=fromdate,
                                symbol=feed.symbol)

    def get_broker(self, dry=False) -> bt.brokers.BackBroker:
        """
        Initializes and sets the brokers for each data feed.

        Returns:
            None
        """
        if self.dry_run or dry:
            broker = BaseBroker()
            broker.setcash(10000)
            broker.setcommission(
                commission=0.0002,
                margin=None,
                mult=1,
                interest=.001
            )
        else:
            broker = FullonBroker(feed=self.str_feeds[0])
        return broker

    def run_loop(self, stop_signal, test: Optional[bool] = False) -> None:
        """
        Run the bot's main loop until the stop_signal is set.

        Parameters:
            test (Optional[bool]): Whether to run the bot in test mode. Defaults to False.
            stop_signal (Optional[threading.Event]): An event object to signal the loop to stop. Defaults to None.
        """
        setproctitle(f"Fullon Bot {self.id}")
        if not self._feeds_can_start(stop_signal=stop_signal):
            logger.error("Feeds can't start, exiting bot startup")
            return
        self.test = test
        cerebro = bt.Cerebro()
        if self.dry_run:
            strategy.STRATEGY_TYPE = "drylive"
        else:
            strategy.STRATEGY_TYPE = "live"
        if test:
            strategy.STRATEGY_TYPE = "testlive"
        broker = self.get_broker()
        cerebro.setbroker(broker)

        module = importlib.import_module(
            'strategies.' + self.strategy + '.strategy',
            package='Strategy')

        if stop_signal:
            self.str_params['stop_signal'] = stop_signal

        cerebro.addstrategy(module.Strategy, **self.str_params)
        self._load_live_feeds(cerebro=cerebro, bars=self.str_params['pre_load_bars'])
        logger.info("Starting Bot...")
        # print(len(cerebro.datas))
        #try:
        cerebro.run(live=True)
        #except KeyboardInterrupt:
        #    exit()
