"""
Crawler Manager

This script contains the Crawleranager class that manages the fetching of information from
the Web and saves it on the database, will be used later by sentiment manager.
"""
import threading

from pandas_ta import thermo
from libs import log
from libs.caches.crawler_cache import Cache
from libs.structs.crawler_struct import CrawlerStruct
from libs.structs.crawler_analyzer_struct import CrawlerAnalyzerStruct
from libs.models.crawler_model import Database
from typing import List, Optional
import sys
import importlib
from time import sleep
import arrow
from itertools import groupby
from operator import attrgetter

logger = log.fullon_logger(__name__)


class CrawlerManager:

    started: bool = False

    def __init__(self):
        """Initialize the TradeManager and log the start."""
        self.started = True
        self.stop_signals = {}
        self.thread_lock = threading.Lock()
        self.threads = {}
        self.monitor_thread: threading.Thread
        self.monitor_thread_signal: threading.Event

    def __del__(self):
        self.started = False
        self.stop()

    def stop(self):
        """
        Stops the trade data collection loop for the specified exchange.
        """
        return
        '''
        with self.thread_lock:  # Acquire the lock before accessing shared resources
            if thread in self.stop_signals:
                self.stop_signals[thread].set()
                try:
                    self.threads[thread].join(timeout=1)  # Wait for the thread to finish with a timeout
                except Exception as error:
                    logger.error(f"Error stopping user_trades {thread}: {error}")
                logger.info(f"Stopped  user_trades {thread}")
                del self.stop_signals[thread]
                del self.threads[thread]
            else:
                logger.info(f"No running thread: {thread}")
        '''

    def add_site(self, site: str) -> bool:
        """
        blah
        """
        res = False
        with Database() as dbase:
            res = dbase.add_crawler_site(site=site)
        return res

    def get_sites(self) -> list:
        """
        blah
        """
        res = []
        with Database() as dbase:
            res = dbase.get_crawler_sites()
        return res

    def del_site(self, site: str) -> bool:
        """
        blah
        """
        res = False
        with Database() as dbase:
            res = dbase.del_crawler_site(site=site)
        return res

    def add_llm_engine(self, engine: str) -> bool:
        """
        blah
        """
        res = False
        with Database() as dbase:
            res = dbase.add_llm_engine(engine=engine)
        return res

    def get_llm_engines(self) -> list:
        """
        blah
        """
        res = []
        with Database() as dbase:
            res = dbase.get_llm_engines()
        return res

    def del_llm_engine(self, engine: str) -> bool:
        """
        blah
        """
        res = False
        with Database() as dbase:
            res = dbase.del_llm_engine(engine=engine)
        return res

    def get_profiles(self,
                     page: int = 1,
                     page_size: int = 20,
                     site: str = '',
                     all: bool = False) -> List:
        """
        Blah
        """
        profiles = []
        with Database() as dbase:
            profiles = dbase.get_profiles(site=site,
                                          page=page,
                                          page_size=page_size,
                                          all=all)
        return profiles

    def upsert_profile(self, profile: dict) -> Optional[int]:
        """
        Blah
        """
        res: Optional[int] = None
        _profile = CrawlerStruct.from_dict(profile)
        with Database() as dbase:
            res = dbase.upsert_profile(profile=_profile)
        return res

    def del_profile(self, fid: int) -> bool:
        """
        Blah
        """
        res = False
        with Database() as dbase:
            res = dbase.del_profile(fid=fid)
        return res

    def add_analyzer(self, analyzer: CrawlerAnalyzerStruct) -> Optional[int]:
        """
        Adds a new analyzer to the database.

        Args:
            analyzer_data (dict): The analyzer data to add.

        Returns:
            Optional[int]: The ID of the added analyzer, or None if the operation fails.
        """
        with Database() as dbase:
            aid = dbase.add_analyzer(analyzer)
            if aid:
                msg = f"Analyzer {aid} has been created"
                logger.info(msg)
        return aid

    def edit_analyzer(self, analyzer_data: dict) -> bool:
        """
        Edits an existing analyzer in the database.

        Args:
            analyzer_data (dict): The updated analyzer data.

        Returns:
            bool: True if the operation succeeds, False otherwise.
        """
        analyzer = CrawlerAnalyzerStruct.from_dict(analyzer_data)
        if analyzer.aid is None:
            logger.error("Analyzer ID is required for editing.")
            return False

        with Database() as dbase:
            success = dbase.edit_analyzer(analyzer)
        return success

    def del_analyzer(self, aid: int) -> bool:
        """
        Deletes an analyzer from the database.

        Args:
            aid (int): The ID of the analyzer to delete.

        Returns:
            bool: True if the operation succeeds, False otherwise.
        """
        with Database() as dbase:
            success = dbase.del_analyzer(aid)
        return success

    def add_follows_analyzer(self,
                             uid: int,
                             aid: int,
                             fid: int,
                             account: str) -> bool:
        """
        Adds a new analyzer/follows to the database.

        Args:
            uid
            aid
            fid
            account

        Returns:
            Bool if it works
        """
        with Database() as dbase:
            return dbase.add_follows_analyzer(uid=uid, aid=aid, fid=fid, account=account)

    def delete_follows_analyzer(self,
                                uid: int,
                                aid: int,
                                fid: int,
                                ) -> bool:
        """
        Adds a new analyzer/follows to the database.

        Args:
            uid
            aid
            fid

        Returns:
            Bool if it works
        """
        with Database() as dbase:
            return dbase.delete_follows_analyzer(uid=uid, aid=aid, fid=fid)


    def _load_module_for_site(self, site: str):
        """
        Dynamically loads a module named after the site. Attempts to load from 'libs.crawler'
        and falls back to 'fullon.libs.crawler' if the initial attempt fails.

        Args:
            site (str): The site name to construct the module path.

        Returns:
            An instance of the Crawler class from the loaded module if successful, None otherwise.
        """
        primary_module_name = f'libs.crawler.{site}.crawler'
        fallback_module_name = f'fullon.libs.crawler.{site}.crawler'
        try:
            module = self._import_module(primary_module_name)
        except ImportError as primary_error:
            try:
                module = self._import_module(fallback_module_name)
            except ImportError as fallback_error:
                # Log the error. Replace 'print' with your logging approach.
                print(f"Error importing module '{primary_module_name}': {primary_error}")
                print(f"Attempted fallback to '{fallback_module_name}', but also failed: {fallback_error}")
                return None
        if module:
            try:
                crawler_instance = module.Crawler(site=site)  # Instantiate the Crawler class
                return crawler_instance
            except AttributeError:
                print(f"The module '{module.__name__}' does not contain a 'Crawler' class.")
                return None

    def _import_module(self, module_name: str):
        """
        Helper method to import a module given its name.

        Args:
            module_name (str): Fully qualified module name.

        Returns:
            The imported module.
        """
        if module_name in sys.modules:
            return importlib.reload(sys.modules[module_name])
        else:
            return importlib.import_module(module_name)

    def _llm_scores(self) -> None:
        """
        blah blah
        """
        # First i need to get all analyzer
        with Database() as dbase:
            analyzers = dbase.get_account_analyzers()
            engines = dbase.get_llm_engines()
            for analyzer in analyzers:
                for engine in engines:
                    posts = dbase.get_unscored_posts(aid=analyzer.aid,
                                                     engine=engine)
                    print(">>>",posts)
                    if posts:
                        post_groups = {}
                        for post in posts:
                            post_groups[post.remote_id] = {'content': post.content, 'post_id': post.post_id}
                        for post in posts:
                            if post.self_reply:
                                parent_content = post_groups[post.reply_to]['content']
                                new_content = parent_content + post.content
                                post_groups[post.reply_to]['content'] = new_content
                        for post in post_groups.values():
                            print(post)
                            #here we can call scoring API with the content to score

    def _fetch_posts(self, site: str) -> None:
        """
        Continuously checks for new posts from authors for a specific site, updates scores, and sends to LLMS for sentiment analysis.
        Utilizes dynamic module loading based on the site to fetch posts. Stops when stop signal is set for the site.

        Args:
            site (str): The name of the site to filter profiles by.

        Returns:
            None
        """
        stop_signal = threading.Event()
        self.stop_signals[site] = stop_signal
        module = self._load_module_for_site(site)
        if not module and not hasattr(module, 'get_posts'):
            msg = f"Couldnt not load module {module}"
            logger.error(msg)
            return None
        while not stop_signal.is_set():
            with Database() as dbase:
                accounts = dbase.get_crawling_list(site=site)
                last = dbase.get_last_post_dates(site=site)
                posts = module.get_posts(accounts=accounts, last=last)
                if posts:
                    posts = module.download_medias(posts=posts)
                    dbase.add_posts(posts=posts)
                self._llm_scores()
            return
            current_time = arrow.now()
            next_hour = current_time.shift(hours=1).replace(minute=0, second=0, microsecond=0)
            sleep_time = (next_hour - current_time).total_seconds()
            sleep(sleep_time)  # Sleep until the start of the next hour
        del module

        #por cada sitio (twitter, etc necesito lanzar un thread)
        # ese tread va a leer los posteadores de twitter
        # armara un super request a apify para obtener los twitts
        # luego por cada twiit insertamos su registro en la base de datos
        # actualizamos scores y corremos vs openai u otros llms

    def run_loop(self) -> None:
        """
        Run account loop to start threads for each user's active exchanges.

        The method retrieves the list of users and their active exchanges, then starts a thread for each
        exchange, storing the thread in the 'threads' dictionary. Sets the 'started' attribute to True
        when completed.
        """
        with Database() as dbase:
            sites = dbase.get_crawler_sites()
            for site in sites:
                thread = threading.Thread(target=self._fetch_posts,
                                          args=(site,))
                thread.daemon = True
                thread.start()
                # Store the thread in the threads dictionary
                self.threads[site] = thread
        # Set the started attribute to True after starting all threads
        self.started = True
        monitor_thread = threading.Thread(target=self.relaunch_dead_threads)
        monitor_thread.daemon = True
        monitor_thread.start()
        self.monitor_thread = monitor_thread

    def relaunch_dead_threads(self):
        """
        relaunches dead threads
        """
        pass
        '''
        self.monitor_thread_signal = threading.Event()
        while not self.monitor_thread_signal.is_set():
            for ex_id, thread in list(self.threads.items()):
                if not thread.is_alive():
                    logger.info(f"Thread for trades {ex_id} has died, relaunching...")
                    new_thread = threading.Thread(target=self.update_user_trades, args=(ex_id,))
                    new_thread.daemon = True
                    new_thread.start()
                    self.threads[ex_id] = new_thread
                    time.sleep(0.1)
            for _ in range(50):  # 50 * 0.2 seconds = 10 seconds
                if self.monitor_thread_signal.is_set():
                    break
                time.sleep(0.2)
        '''
