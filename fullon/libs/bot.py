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
from libs.btrader.observers import CashInterestObserver
from typing import Optional, Any, Tuple
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
            self.uid = bot.uid
            self.id = bot.bot_id
            self.bot_name = bot.name
            self.dry_run = bot.dry_run
            self.start_time = arrow.utcnow()
            self.pre_load_bars = 0
            self.str_params = self._str_set_params(dbase=dbase)
            self.cache = cache.Cache()
            self.str_feeds = self._set_feeds(dbase=dbase)
            self.noise = False
            if not self.str_feeds:
                logger.error(
                    "__init__: It is not possible to run a simulation without feeds")
                exit("bye")
            self.simulresults = {}
            for str_id in self.str_feeds.keys():
                self.simulresults[str_id] = {}

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

    def _set_feeds(self, dbase) -> dict:
        """
        Set the feeds for the bot.

        :param feeds: A list of feeds to be used by the bot.
        :return: A list of modified feeds.
        """
        feeds = dbase.get_bot_feeds(bot_id=self.id)
        ret_feeds = {}
        exchanges = dbase.get_exchange(user_id=self.uid)
        tradeable = {}
        exch_dict = {}
        for exch in exchanges:
            _exch = exch.to_dict()
            exch_dict[_exch['cat_name']] = _exch['name']
        for feed in feeds:
            ret_feeds[feed.str_id] = []
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
            setattr(feed, 'strategy_name', self.str_params[feed.str_id]['cat_name'])
            ret_feeds[feed.str_id].append(feed)
        return ret_feeds

    def _str_set_params(self, dbase) -> dict:
        """
        Set the strategy parameters for the bot.

        :return: A list of dictionaries with enhanced strategy parameters.
        """
        def convert_value(value):
            try:
                if '.' in value:  # If '.' is in the string, try parsing as float
                    return float(value)
                else:  # Else try parsing as int
                    return int(value)
            except (ValueError, TypeError):  # If both float and int casting fail, keep as string
                return value

        base_params = dbase.get_base_str_params(bot_id=self.id)
        params = dbase.get_str_params(bot_id=self.id)
        ret_params = {}
        if not params:
            logger.warning("Couldn't find params for this bot, are you sure this is ok")            
            ret_params[base_params[0].str_id] = base_params[0].to_dict()
            ret_params[base_params[0].str_id]['uid'] = self.uid
            ret_params[base_params[0].str_id]['bot_id'] = self.id
            self.pre_load_bars = base_params[0].pre_load_bars
            ret_params[base_params[0].str_id].pop('mail')
            ret_params[base_params[0].str_id].pop('name')
            ret_params[base_params[0].str_id]['helper'] = self
        for param in params:
            # Iterate over a copy of the dictionary's items
            for name, value in list(param.items()):
                param[name] = convert_value(value)
            # Assign the helper object
            param['helper'] = self
            # Assign the base parameter object
            for base_param in base_params:
                if base_param.str_id == param['str_id']:
                    param.update(base_param.to_dict())
                    break  # Stop looking through base_params once a match is found
            param.pop('mail')
            param.pop('name')
            param['uid'] = self.uid
            param['bot_id'] = self.id
            if self.pre_load_bars < param['pre_load_bars']:
                self.pre_load_bars = param['pre_load_bars']
            ret_params[param['str_id']] = param
        return ret_params

    def extend_str_params(self, str_id: int, test_params: dict) -> None:
        """
        Extend the strategy parameters with additional test parameters.

        :param test_params: A dictionary containing additional test parameters.
        :param str_id: Strategy_id to modify params
        """
        if test_params:
            for key, value in test_params.items():
                self.str_params[str_id][key] = value

    def _set_timeframe(self, period: str) -> Any:
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

    def backload_from(self, str_id: int, bars: int = 100) -> Tuple[arrow.Arrow, arrow.Arrow]:
        """
        Shift the current time by a certain amount, based on the 'frame' and 'compression' parameters.
        Returns a new Arrow object with the shifted time.

        Returns a second date which the fullonfeed requieres for faster startup
        """
        # define a dictionary that maps each period string to the corresponding time unit for Arrow
        period_map = {
            "ticks": "minutes",
            "minutes": "minutes",
            "days": "days",
            "weeks": "weeks",
            "months": "months"
        }
        # get the feed for the last data and calculate the time shift based on the compression and simul_backtest
        feed = self.str_feeds[str_id][-1]
        timeframe = self._set_timeframe(period=feed.period)
        time_unit = period_map.get(feed.period.lower())
        if time_unit is None:
            raise ValueError("Unrecognized period: {}".format(feed.period))
        shift_args = {time_unit: -feed.compression * bars}
        # shift the current time by the specified amount and set the time to midnight
        match timeframe:
            case 5:
                target1 = arrow.utcnow().shift(**shift_args).floor('day')
                target2 = arrow.utcnow().shift(days=-2).floor('day')
            case 6:
                target1 = arrow.utcnow().shift(**shift_args).floor('day')
                target2 = arrow.utcnow().shift(weeks=-2).floor('day')
            case 7:
                target1 = arrow.utcnow().shift(**shift_args).floor('day')
                target2 = arrow.utcnow().shift(months=-2).floor('day')
            case _:
                target1 = arrow.utcnow().shift(**shift_args).floor('minute')
                target2 = arrow.utcnow().shift(minutes=-1*(bars*2)+1)
        return target1, target2

    def _pair_feeds(self, cerebro: bt.Cerebro) -> bool:
        """
        Pair up the data feeds in the Cerebro object by setting the 'feed2' attribute of each feed to the
        corresponding feed in the pair.
        """
        for str_id, params in self.str_params.items():
            num_feeds = len(self.str_feeds[str_id])
            if params['feeds'] != num_feeds:
                msg = f"Number of feeds ({num_feeds}) do not match "
                msg += f"strategy requirement ({params['feeds']})"
                logger.error(msg)
                return False
            # If there is an odd number of data feeds, raise an error
            if params['pairs'] is True:
                if num_feeds % 2 != 0:
                    msg = f"Number of data feeds must be even, current num feeds {num_feeds}"
                    logger.error(msg)
                    return False
                # Determine the number of pairs of data feeds
                num_pairs = num_feeds // 2
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

    def _feeds_can_start(self, stop_signal, retries=80) -> bool:
        """
        Checks if all feeds can start based on certain conditions.
        It will check for the conditions for a number of times defined by 'retries' before giving up.

        Args:
            retries (int): The number of times to retry if any condition is not met. Default to 20.

        Returns:
            bool: `True` if all feeds can start, `False` otherwise.
        """
        for feeds in self.str_feeds.values():
            for feed in feeds:
                with cache.Cache() as store:
                    # Check if the OHLCV process for the feed is 'Synced' and its timestamp is not older than 120 seconds.
                    if not self.check_ohlcv(feed, store):
                        return self.retry_or_fail(retries, f"OHLCV for {feed.exchange_name}:{feed.symbol} is not synced", stop_signal)

                    # Check if the ticker for the feed is running and its timestamp is not older than 120 seconds.
                    if not self.check_ticker(feed, store):
                        return self.retry_or_fail(retries, f"Ticker for {feed.exchange_name}:{feed.symbol} doesn't seem to be working", stop_signal)

                    # Check if the account associated with `self.uid` is being updated and its timestamp is not older than 120 seconds.
                    if not self.check_account(store=store, feed=feed):
                        return self.retry_or_fail(retries, f"Account {self.uid} is not being updated", stop_signal)

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
        if res:
            return res and 'Synced' in res['message'] and arrow.get(res['timestamp']).shift(seconds=120) > arrow.utcnow()
        return False

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
        if res:
            try:
                return arrow.get(res[1]).shift(seconds=600) > arrow.utcnow()
            except TypeError:
                pass
        return False

    def check_account(self, store, feed) -> bool:
        """
        Checks if the account associated with `self.uid` is being updated and its timestamp is not older than 120 seconds.

        Args:
            store: The cache store.

        Returns:
            bool: `True` if the account associated with `self.uid` is being updated and its timestamp is not older than 120 seconds, `False` otherwise.
        """
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

    def _load_feeds(self,
                    cerebro: bt.Cerebro,
                    warm_up: int,
                    event: bool,
                    ofeeds: dict) -> bool:
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
        loaded = []
        index = 0
        for str_id, feeds in self.str_feeds.items():
            for num, feed in enumerate(feeds):
                key = f"{feed.ex_id}:{feed.symbol}:{feed.period}:{feed.compression}"
                # Clear the simulation results list for this feed
                self.simulresults[str_id][num] = []
                #if key in loaded:
                #    continue
                # Set the timeframe for the feed
                timeframe = self._set_timeframe(period=feed.period)
                not_tick = True
                if feed.period.lower() == "ticks":
                    self.str_feeds[str_id][num].period = "minutes"
                    feed.period = "minutes"
                    feed.trading = True
                    not_tick = False
                compression = feed.compression
                try:
                    compression = ofeeds[num]['compression']
                except KeyError:
                    pass
                if not_tick:
                    fromdate, _ = self.backload_from(str_id=str_id,
                                                     bars=self.bars+warm_up)
                else:
                    # Set the start date for the backtest
                    fromdate, _ = self.backload_from(str_id=str_id,
                                                     bars=self.bars)
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
                loaded.append(key)
                data = FeedClass(feed=feed,
                                 timeframe=timeframe,
                                 compression=int(compression),
                                 helper=self,
                                 fromdate=fromdate,
                                 mainfeed=feed0)
                # Add the data object to the cerebro instance
                cerebro.adddata(data)
                # Store the first feed object for later use
                if index == 0:
                    feed0 = data
                index += 1
        return True

    def _load_strategies(self, cerebro: bt.Cerebro, event: bool = False):
        """
        loads strategies into a cerebro
        """
        if event:
            strategy.STRATEGY_TYPE = "event"
        else:
            strategy.STRATEGY_TYPE = "backtest"

        for params in self.str_params.values():
            module = importlib.import_module(
                'strategies.' + params['cat_name'] + '.strategy',
                package='Strategy')
            cerebro.addstrategy(module.Strategy, **params)

    def run_simul_loop(self,
                       feeds: dict = {},
                       visual: bool = False,
                       leverage: int = 1,
                       test_params: list = [],
                       warm_up: int = 0,
                       event: bool = False,
                       noise: bool = False,
                       fee: float = 0.0015) -> dict:
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
            return {}
        if test_params:
            str_ids = list(self.str_params.keys())
            if len(str_ids) != len(test_params):
                logger.critical("This # of strategies in tests_params do not match bots")
                return {}
            for num, str_id in enumerate(str_ids):
                self.extend_str_params(str_id=str_id, test_params=test_params[num])

        cerebro = bt.Cerebro(tradehistory=True)
        broker = self.get_broker(dry=True, mult=leverage, fee=fee)
        cerebro.setbroker(broker)
        self.noise = noise
        self._load_strategies(cerebro=cerebro, event=event)
        main_str_id = list(self.str_params.keys())[0]
        cerebro.addobserver(CashInterestObserver, interest_rate=0.04, main_str_id=main_str_id)
        if not self._load_feeds(cerebro=cerebro, warm_up=warm_up, event=event, ofeeds=feeds):
            return {}
        if not self._pair_feeds(cerebro=cerebro):
            return {}
        r = []
        try:
            r = cerebro.run(live=True)
        except:
            raise
        if r == []:
            return {"ERROR": "Either nothing happened or could not pass strategy __init__, check log"}
        imgtitle = ""
        if visual:
            now = arrow.utcnow().format('YYYY-MM-DD_HH:mm:ss')
            p = ""
            #for key, value in test_params.items():
            #    p = p + str(key) + "_" + str(value) + "_"
            #imgtitle = "tmp/simul_" + "me" + "_" + p + "_" + now + ".png"
            imgtitle="some_sim"
            cerebro.plot(style='lines', saveimg=imgtitle)
        interests = r[0].observers.cashinterestobserver.totalinterest
        for str_id, params in self.str_params.items():
            params.pop('helper', None)
            params.pop('pre_load_bars', None)
            params.pop('cat_str_id', None)
            strategy_name = params.pop('cat_name')
            for num in range(0, len(self.simulresults[str_id])):
                self.simulresults[str_id][num].append({"strategy": strategy_name,
                                                       "params": params,
                                                       "feed": self.str_feeds[str_id][num],
                                                       "imgtitle": imgtitle,
                                                       "starting_cash": broker.startingcash,
                                                       "ending_assets": cerebro.broker.getvalue(),
                                                       "interest_earned": interests})
        del cerebro
        return self.simulresults

    def _load_live_feeds(self, cerebro: bt.Cerebro):
        """
        Loads the feeds into the cerebro instance for backtesting.

        Parameters:
        - cerebro: A `backtrader.Cerebro` instance.
        Returns:
        - None
        """
        # Initialize the first feed as None
        #fromdate = arrow.get('2023-09-04 00:00:00')
        feed_map = {}
        index = 0
        for str_id, feeds in self.str_feeds.items():
            fromdate, fromdate2 = self.backload_from(
                                    str_id=str_id,
                                    bars=self.pre_load_bars)
            for num, feed in enumerate(feeds):
                compression = int(feed.compression)
                period = feed.period
                timeframe = self._set_timeframe(period=period)
                # Choose the feed class based on the event parameter
                feed_class = FEED_CLASSES['FullonFeed']
                feed_module, feed_class_name = feed_class.rsplit(".", 1)
                FeedClass = getattr(importlib.import_module(feed_module), feed_class_name)
                if timeframe == bt.TimeFrame.Ticks:
                    data = FeedClass(feed=feed,
                                     timeframe=1,
                                     compression=1,
                                     helper=self,
                                     fromdate=fromdate,
                                     fromdate2=fromdate2,
                                     mainfeed=None)
                    cerebro.adddata(data, name=f'{index}')
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
                                                          name=f'{index}')
                    sampler = FullonFeedResampler()
                    sampler.prepare(data=resampled_data,
                                    bars=self.pre_load_bars,
                                    timeframe=timeframe,
                                    compression=compression,
                                    feed=feed,
                                    fromdate=fromdate.format("YYYY-MM-DD HH:mm:ss"))
                    index += 1

    def get_broker(self, dry: bool = False, mult: int = 1, fee: float = 0.0015) -> bt.brokers.BackBroker:
        """
        Initializes and sets the brokers for each data feed.

        Returns:
            None
        """
        if self.dry_run or dry:
            broker = BaseBroker()
            broker.setcash(10000)
            broker.setcommission(
                commission=fee,
                margin=None,
                mult=mult,
                interest=0.000
            )
        else:
            first_feed = list(self.str_feeds.keys())[0]
            broker = FullonBroker(feed=self.str_feeds[first_feed][0])
        return broker

    def _load_live_strategies(self, cerebro: bt.Cerebro, stop_signal):
        """
        loads strategies into a cerebro
        """
        if self.dry_run:
            strategy.STRATEGY_TYPE = "drylive"
        else:
            strategy.STRATEGY_TYPE = "live"
        if self.test:
            strategy.STRATEGY_TYPE = "testlive"
        for params in self.str_params.values():
            params['stop_signal'] = stop_signal
            module = importlib.import_module(
                'strategies.' + params['cat_name'] + '.strategy',
                package='Strategy')
            cerebro.addstrategy(module.Strategy, **params)

    def run_loop(self, stop_signal, no_check: bool = False, test: Optional[bool] = False) -> None:
        """
        Run the bot's main loop until the stop_signal is set.

        Parameters:
            test (Optional[bool]): Whether to run the bot in test mode. Defaults to False.
            stop_signal (Optional[threading.Event]): An event object to signal the loop to stop. Defaults to None.
        """
        if test:
            self.test = True
        setproctitle(f"Fullon Bot {self.id}")
        if no_check is True:
            time.sleep(5)
            return
        if not self._feeds_can_start(stop_signal=stop_signal):
            logger.error("Feeds can't start, exiting bot startup")
            return
        cerebro = bt.Cerebro()
        broker = self.get_broker()
        cerebro.setbroker(broker)
        self._load_live_strategies(cerebro=cerebro, stop_signal=stop_signal)
        self._load_live_feeds(cerebro=cerebro)
        logger.info("Starting Bot...")
        try:
            cerebro.run(live=True)
        except KeyboardInterrupt:
            exit()
