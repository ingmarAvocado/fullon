"""
Manages launch of Bots
"""
from threading import Thread, Event
from libs import log
from libs.bot import Bot
from libs.database import Database
from libs.cache import Cache
from libs.bot_launcher import Launcher
from libs.simul_launcher import simulator
from run.user_manager import UserManager
import time
from typing import Any, Dict, Optional

logger = log.fullon_logger(__name__)


class BotManager:
    """
    Manages the launch of Bots
    """

    def __init__(self):
        self.started = None
        self.launcher: Launcher = Launcher()
        self.relauncher: Optional[Thread]
        self.relauncher_event: Optional[Event]

    def __del__(self):
        self.stop_all()

    def stop_bot(self, bot_id: int) -> bool:
        """
        """
        res = self.launcher.stop(bot_id=bot_id)
        if res:
            with Cache() as store:
                store.del_bot(bot_id=str(bot_id))
        return res

    def stop_all(self) -> None:
        """
        Stops all the bots.
        """
        if self.started:
            self.started = False
            self.relauncher_event.set()
            self.relauncher.join(timeout=1)
            self.launcher.stop_all()

    def start_bot(self, bot_id: int) -> bool:
        """
        Start the specified bot

        Args:
            bot_id (int): The id of the bot to start
        """
        if not self.started:
            self.started = True
            with Cache() as store:
                store.del_status()
            self.relauncher_event = Event()
            self.relauncher = Thread(target=self.relaunch_dead_bots)
            self.relauncher.daemon = True
            self.relauncher.start()
        return self.launcher.start(bot_id=bot_id)

    def is_running(self, bot_id: int) -> bool:
        """ checks with the launcher queue if proces is alive"""
        res = self.launcher.ping(bot_id=bot_id)
        return res

    def relaunch_dead_bots(self) -> None:
        """
        Continually checks the state of the bot processes and relaunches any that have died.
        """
        while not self.relauncher_event.is_set():  # Changed from `self.started.is_set()` to `self.monitor_signal.is_set()`
            bots = self.launcher.get_bots()
            for bot_id in bots:
                if not self.is_running(bot_id=bot_id):
                    logger.warning(f"Detected dead bot {bot_id}. Relaunching...")
                    self.start_bot(bot_id)
            for _ in range(0, 10):
                if self.relauncher_event.is_set():
                    return
                time.sleep(1)

    def run_bot_loop(self) -> None:
        """
        Description:
            This method starts a new process for each bot in the bot list that is set to active.

        Returns:
            None
        """
        bots = []
        with Database() as dbase:
            bots = dbase.get_bot_list(active=True)
        if bots:
            for bot in bots:
                self.start_bot(bot_id=bot.bot_id)
        logger.info("Bots started")

    def delete(self, bot_id: str) -> bool:
        """
        Deletes the specified bot.

        Args:
            bot_id (int): The id of the bot to stop
        """
        res = False
        with Database() as dbase:
            res = dbase.delete_bot(bot_id=bot_id)
        return res

    def bots_list(self, page_size=20, page=1) -> Optional[list]:
        """
        Get a list of all bots

        Returns:
            str: A string representation of all bots in the format of
                '{bot_id: <id>, dry_run: <dry_run>}\n'
        """
        bots = []
        with Database() as dbase:
            _bots = dbase.get_bot_full_list(page_size=page_size, page=page)
        with Cache() as store:
            _bots2 = store.get_bots()
        live_bots = self.launcher.get_bots()
        for bot in _bots:
            bot_id = str(bot['bot_id'])
            bot['live'] = False
            bot['position'] = False
            if bot_id in _bots2:
                for feed, _bot in _bots2[bot_id].items():
                    if float(_bot['position']) != 0:
                        bot['position'] = True
                if int(bot_id) in live_bots:
                    bot['live'] = True
            bots.append(bot)
        return bots

    def bot_details(self, bot_id: int) -> Dict[str, Any]:
        """
        Fetches bot parameters, feeds, and strategy details for a bot from the database, given its unique bot ID. 

        The function queries the database to get the bot parameters, bot feeds, and strategy parameters. These
        details are combined into a dictionary and returned.

        Args:
            bot_id (int): The unique ID of the bot for which details are to be fetched.

        Returns:
            Dict[str, Any]: A dictionary with bot parameters, feeds, and strategy details. Returns an empty
                            dictionary if the bot ID does not exist.
        """
        details = {}

        with Database() as dbase:
            details = dbase.get_bot_params(bot_id=bot_id)
            if details:
                _feeds = dbase.get_bot_feeds(bot_id=bot_id)
                feeds = {}
                for num, feed in enumerate(_feeds):
                    feeds[f"{num}"] = {
                                  'symbol': feed.symbol,
                                  'exchange': feed.exchange_name,
                                  'compression': feed.compression,
                                  'period': feed.period,
                                  'feed_id': feed.feed_id
                                  }
                details['feeds'] = feeds
                extended = dbase.get_str_params(bot_id=bot_id)
                details['extended'] = dict(extended)
        return details

    def get_bot_feeds(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetches all bot feeds from the database and returns them as a dictionary.

        This function queries the database to fetch all bot feeds. Each feed's details
        such as symbol, exchange name, compression, and period are stored in a dictionary 
        under the key of the feed's ID.

        Returns:
            Dict[str, Dict[str, Any]]: A dictionary where each key is a feed's ID and its value 
            is another dictionary containing the feed's details (symbol, exchange name, compression, 
            and period). Returns an empty dictionary if there are no feeds.
        """
        feeds = {}

        with Database() as dbase:
            _feeds = dbase.get_bot_feeds()
            if _feeds:
                for feed in _feeds:
                    feeds[feed.feed_id] = {
                                      'symbol': feed.symbol,
                                      'exchange': feed.exchange_name,
                                      'compression': feed.compression,
                                      'period': feed.period,
                                      }
        return feeds

    def bots_live_list(self) -> Dict:
        """
        Get a list of all bots running

        Returns:
            str: A string representation of all bots in the format of
                '{bot_id: <id>, dry_run: <dry_run>}\n'
        """
        with Cache() as store:
            bots = store.get_bots()

        # Only keep bots whose keys (converted to integers) are in self.threads
        bots = {key: value for key, value in bots.items() if int(key) in self.launcher.get_bots()}
        return bots

    def add(self, bot: dict) -> Optional[int]:
        """
        Adds a bot
        """
        user = UserManager()
        bot_id = user.add_bot(bot=bot)
        if bot_id:
            return bot_id

    def add_exchange(self, bot_id: int, exchange: dict) -> bool:
        """
        Adds an exchange to a bot
        """
        user = UserManager()
        return user.add_bot_exchange(bot_id=bot_id, exchange=exchange)

    def add_feeds(self, bot_id: int, feeds: dict) -> bool:
        """
        Adds an exchange to a bot
        """
        user = UserManager()
        for feed in feeds.values():
            feed['bot_id'] = bot_id
            if not user.add_feed_to_bot(feed=feed):
                return False
        return True

    def edit(self, bot: dict) -> bool:
        """
        Edit the specified bot.

        Args:
            bot (dict): The bot to edit.

        Returns:
            bool: True if the bot was successfully edited, False otherwise.
        """
        # Interact with the database

        if 'bot_id' not in bot:
            logger.error("No bot id in bot dict")
            return False
        with Database() as dbase:

            # Extract and remove optional elements from bot
            feeds = bot.pop('feeds', None)
            extended = bot.pop('extended', None)

            # Copy bot to a new dictionary and remove certain elements
            base = bot.copy()
            for key in ['bot_id', 'dry_run', 'active', 'uid']:
                base.pop(key, None)

            _bot = {}
            # Create _bot dictionary
            if 'dry_run' in bot:
                _bot['dry_run'] = bot['dry_run']
            if 'active' in bot:
                _bot['active'] = bot['active']
            if _bot:
                _bot['bot_id'] = bot['bot_id']
                # Perform a sequence of database operations, stopping if any operation fails
                if not (res := dbase.edit_bot(bot=_bot)):
                    return False

            if not (res := dbase.edit_base_strat_params(bot_id=bot['bot_id'], params=base)):
                return False

            if extended:
                forbidden = ['leverage', 'dry_run', 'active', 'take_profit',
                             'stop_loss', 'trailing_stop', 'period',
                             'compression', 'order', 'bot_id', 'symbol_id',
                             'size', 'size_pct', 'size_currency', 'timeout']
                extended = {k: v for k, v in extended.items() if k not in forbidden}
                if not (res := dbase.edit_strat_params(bot_id=bot['bot_id'], params=extended)):
                    return False

            if feeds:
                if not (res := dbase.edit_feeds(bot_id=bot['bot_id'], feeds=feeds)):
                    return False

        # All operations were successful
        return res

    def dry_delete(self, bot_id: int) -> None:
        """
        Delete all dry trades for the specified bot

        Args:
            bot_id (int): The id of the bot to delete dry trades for
        """
        with Database() as dbase:
            dbase.delete_dry_trades(bot_id=bot_id)

    @staticmethod
    def launch_simul(   # pylint: disable=too-many-arguments
            bot_id: int,
            periods: int = 500,
            visual: int = 0,
            event: bool = False,
            feeds: list = [],
            warm_up: Optional[Any] = None,
            test_params: Optional[Any] = None) -> Dict[str, Any]:
        """
        Launches simulation of bot with the specified parameters.
        :param bot_id: ID of the bot to simulate
        :param days: Number of days to simulate
        :param compression: Compression level for the simulation
        :param visual: Indicator for whether to show visual output during simulation
        :param warm_up: Additional parameters for warm-up phase of simulation
        :param test_params: Additional parameters for testing during simulation
        :return: Dictionary of results from the simulation
        """
        try:
            response_queue = simulator.new_queue()
            request = (bot_id, periods, visual, event, feeds, warm_up, test_params, response_queue)
            simulator.request_queue.put(request)
            results = response_queue.get()
            del response_queue
            return results
        except Exception as e:
            logger.error(f"Failed to start bot {bot_id}: {e}")
            raise
