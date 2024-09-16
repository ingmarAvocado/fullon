"""
Crawler Manager

This script contains the Crawleranager class that manages the fetching of information from
the Web and saves it on the database, will be used later by sentiment manager.
"""
import threading
from libs import log
from libs.structs.crawler_struct import CrawlerStruct
from libs.structs.crawler_post_struct import CrawlerPostStruct
from libs.structs.crawler_analyzer_struct import CrawlerAnalyzerStruct
from libs.database import Database
#from libs.models.crawler_model import Database
from libs.cache import Cache
from typing import List, Optional
import sys
import importlib
from time import sleep
import arrow
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
from os import getpid
import pause
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


logger = log.fullon_logger(__name__)


class CrawlerManager:

    started: bool = False

    def __init__(self):
        """Initialize the TradeManager and log the start."""
        self.started = False
        self.stop_signals = {}
        self.thread_lock = threading.Lock()
        self.threads = {}

    def __del__(self):
        self.started = False
        self.stop_all()

    def stop_all(self):
        """
        stops all threads
        """
        threads_to_stop = list(self.stop_signals.keys())
        for thread in threads_to_stop:
            self.stop(thread=thread)
        self.started = False

    def stop(self, thread):
        """
        Stops the trade data collection loop for the specified exchange.

        Args:
            thread
        """
        with self.thread_lock:  # Acquire the lock before accessing shared resources
            if thread in self.stop_signals:
                try:
                    self.stop_signals[thread].set()
                    self.threads[thread].join(timeout=1)  # Wait for the thread to finish with a timeout
                    del self.stop_signals[thread]
                    del self.threads[thread]
                except KeyError:
                    logger.debug("Can't stop thread %s", (thread))
                    pass
                logger.info(f"Stopped  user_trades {thread}")
            else:
                logger.info(f"No running thread: {thread}")

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
            aid = dbase.add_analyzer(analyzer=analyzer)
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
            success = dbase.edit_analyzer(analyzer=analyzer)
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
            success = dbase.del_analyzer(aid=aid)
        return success

    def add_follows_analyzer(self, uid: int, aid: int, fid: int, account: str) -> bool:
        """
        Adds a new analyzer/follows to the database.

        Args:
            uid (int): user id
            aid (int): analyzer id
            fid (int): follow id
            account (str): account string

        Returns:
            Bool if it works
        """
        with Database() as dbase:
            return dbase.add_follows_analyzer(uid=uid, aid=aid, fid=fid, account=account)

    def delete_follows_analyzer(self, uid: int, aid: int, fid: int) -> bool:
        """
        Adds a new analyzer/follows to the database.

        Args:
            uid (int): user id
            aid (int): analyzer id
            fid (int): follow id

        Returns:
            Bool if it works
        """
        with Database() as dbase:
            return dbase.delete_follows_analyzer(uid=uid, aid=aid, fid=fid)

    @staticmethod
    def _update_process(key: str, message="Synced") -> bool:
        """
        Update the process status in cache. This function generates a new process ID 
        and updates the cache with a new message status.

        Args:
            exchange_name (str): The name of the exchange.
            symbol (str): The trading pair symbol.

        Returns:
            bool: Returns True if the process is successfully updated in the cache, else False.
        """
        with Cache() as store:
            res = store.update_process(tipe="crawler",
                                       key=key,
                                       message=message)
        return bool(res)

    def _load_module(self, site: str = '', engine: str = '') -> Optional[object]:
        """
        Dynamically loads a module named after the site. Attempts to load from 'libs.crawler'
        and falls back to 'fullon.libs.crawler' if the initial attempt fails.

        Args:
            site (str): The site name to construct the module path.

        Returns:
            An instance of the Crawler class from the loaded module if successful, None otherwise.
        """
        if site:
            primary_module_name = f'libs.crawler.{site}.crawler'
            fallback_module_name = f'fullon.libs.crawler.{site}.crawler'
        elif engine:
            primary_module_name = f'libs.crawler.llm_engines.{engine}.engine'
            fallback_module_name = f'fullon.libs.crawler.llm_engines.{engine}.engine'
        else:
            logger.error("Need parameter site or engine")
            return
        try:
            module = self._import_module(primary_module_name)
        except ImportError as primary_error:
            if 'apify' in str(primary_error):
                logger.error('No apify library installed, install it with pip3 install apify_client')
            try:
                module = self._import_module(fallback_module_name)
            except ImportError as fallback_error:
                # Log the error. Replace 'print' with your logging approach.
                msg = f"Error importing module '{primary_module_name}': {primary_error}"
                msg = f"Attempted fallback to '{fallback_module_name}', but also failed: {fallback_error}"
                logger.error(msg+msg)
                return
        if module:
            try:
                if site:
                    return module.Crawler()  # Instantiate the Crawler class
                if engine:
                    return module.Engine()  # instantiate an Engine
            except AttributeError as error:
                msg = ''
                if site:
                    msg = f"The module '{module.__name__}' does not contain a 'Crawler' class."
                if engine:
                    msg = f"The module '{module.__name__}' does not contain a 'Engine' class."
                logger.error(msg)
        return

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

    def normalize_and_scale_scores(self, posts: List[CrawlerPostStruct]) -> List[CrawlerPostStruct]:
        """
        Combine historical scores with current pre_scores, converting all to float,
        and normalize scores using min-max scaling based on historical data.

        The scores are log-transformed to normalize large variances and then scaled
        to a range of 1 to 10.

        Args:
            posts (List[CrawlerPostStruct]): List of post structures with pre_score attribute.

        Returns:
            List[CrawlerPostStruct]: The input list with adjusted pre_scores.
        """
        with Database() as dbase:
            # Fetch historical scores, assuming this includes current posts
            historical_scores = [float(score) for score in dbase.get_pre_scores(num=15000)]

        # Apply log transformation to normalize variances, np.log1p avoids log(0) issues
        log_scores = np.log1p(historical_scores)

        # Calculate scaling parameters from historical context
        min_log_score = np.min(log_scores)
        max_log_score = np.max(log_scores)
        range_log_scores = max_log_score - min_log_score

        # If there's no range (all scores identical), avoid division by zero
        if range_log_scores == 0:
            adjusted_scores = [Decimal(5.5)] * len(posts)  # Midpoint if no variance
        else:
            # Directly use historical scores for adjusting current posts
            # This requires matching posts to their historical scores, which might need adjustment
            # in how you track or fetch historical scores.
            # Assuming we adjust based on the fetched historical scores directly
            adjusted_scores = 1 + (np.log1p([float(post.pre_score) if post.pre_score is not None else 0.0 for post in posts]) - min_log_score) * (9 / range_log_scores)
            adjusted_scores = [Decimal(score).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) for score in adjusted_scores]

        # Assign adjusted scores back to posts
        for post, adjusted_score in zip(posts, adjusted_scores):
            post.score = adjusted_score
        return posts

    def _llm_score(self, engine: str, post: CrawlerPostStruct) -> Optional[Decimal]:
        """
        Scores a single post
        """
        llm_engine = self._load_module(engine=engine)
        score: float = llm_engine.score_post(post=post)
        if score is not None:
            return round(Decimal(score), 2)

    def _llm_scores(self, engine: str = '') -> None:
        """
        blah blah
        """
        # First, get all analyzers
        with Database() as dbase:
            analyzers = dbase.get_account_analyzers()
        if engine:
            engines = [engine]
        else:
            with Database() as dbase:
                engines = dbase.get_llm_engines()

        def process_posts(analyzer, engine):
            with Database() as dbase:
                posts = dbase.get_unscored_posts(aid=analyzer.aid, engine=engine, no_is_reply=True)
            if posts:
                for post in posts:
                    try:
                        score = self._llm_score(engine=engine, post=post)
                        if score is not None:
                            with Database() as dbase:
                                dbase.add_engine_score(post_id=post.post_id,
                                                       score=score,
                                                       aid=analyzer.aid,
                                                       engine=engine)
                    except Exception as error:
                        logger.error(f"Can't set score for engine {engine} post id {post.post_id} with {str(error)}")

        '''
        for analyzer in analyzers:
            for engine in engines:
                process_posts(analyzer=analyzer, engine=engine)
        '''

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(process_posts, analyzer, engine) for analyzer in analyzers for engine in engines]
            for future in as_completed(futures):
                try:
                    future.result()  # To raise exceptions if any occurred in the threads
                except Exception as e:
                    print(f"An error occurred: {e}")

    def _process_posts(self, site: str, account: str) -> None:
        """
        process the posts
        """
        module = self._load_module(site)
        if not module and not hasattr(module, 'get_posts'):
            msg = f"Couldn't load module {module}"
            logger.error(msg)
            return None
        while True:
            with Database() as dbase:
                last = dbase.get_last_post_date(site=site, account=account)
            posts = module.get_posts(account=account, last=last)
            if len(posts) == 0:
                break
            posts = module.download_medias(posts=posts)
            with Database() as dbase:
                dbase.add_posts(posts=posts)
                posts = self.normalize_and_scale_scores(posts=posts)
                dbase.add_posts(posts=posts)

    def wait_until_next_period(self, stop_signal: threading.Event, site: str) -> bool:
        """
        Waits until a minute passed or stop_signal is true

        Args:
            stop_signal: a threading even to stop before minute passed by
            site: site that is being updated

        Returns:
            Bool True if it waited


        """
        target_time = arrow.utcnow().shift(days=1).floor('day').shift(minutes=-20)
        counter = 0
        while arrow.utcnow() < target_time:
            if stop_signal.is_set():
                return True  # Stop signal received
            remaining = (target_time - arrow.now()).total_seconds()
            sleep_time = min(remaining, 0.1)  # Check every 100ms, or less if less time remains
            if sleep_time > 0:
                time.sleep(sleep_time)
            counter += 1
            if counter > 200:
                counter = 0
                logger.info("Let the process manger know i am alive")
                self._update_process(key=site)
        return False

    def _fetch_posts(self, site: str, llm_scores: bool = True) -> None:
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

        msg = f"Crawling service for site {site} has started"
        logger.info(msg)
        while not stop_signal.is_set():
            with Database() as dbase:
                accounts = dbase.get_crawling_list(site=site)
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(self._process_posts, site, account) for account in accounts]
                for future in as_completed(futures):
                    try:
                        future.result()  # This will raise an exception if the thread raised one
                    except Exception as e:
                        print(f"Exception occurred: {e}")
                        raise

            if llm_scores:
                self._llm_scores()
            now = arrow.now()
            next_time = now.shift(days=1).floor('day').shift(minutes=-20)
            log_message = (
                f"Updating crawler  for site {site}. "
                f"Pausing until ({next_time.format()})"
            )
            if not llm_scores:
                log_message = (
                    f"No scores detected for {site}. "
                    f"Pausing until ({next_time.format()})"
                )
            else:
                log_message = (
                    f"Registering scores for site {site} "
                    f"Pausing until ({next_time.format()})"
                )
            logger.info(log_message)
            self._update_process(key=site)
            if self.wait_until_next_period(stop_signal=stop_signal, site=site):
                logger.info("Stop signal received. Exiting loop.")
                break

    def run_loop(self) -> None:
        """
        Run account loop to start threads for each user's active exchanges.

        The method retrieves the list of users and their active exchanges, then starts a thread for each
        exchange, storing the thread in the 'threads' dictionary. Sets the 'started' attribute to True
        when completed.
        """
        with Database() as dbase:
            sites = dbase.get_crawler_sites(active=True)
            for site in sites:
                thread = threading.Thread(target=self._fetch_posts,
                                          args=(site,))
                thread.daemon = True
                thread.start()
                # Store the thread in the threads dictionary
                self.threads[site] = thread
                with Cache() as store:
                    store.new_process(tipe="crawler",
                                      key=site,
                                      pid=f"thread:{getpid()}",
                                      params={},
                                      message="Started")
        # Set the started attribute to True after starting all threads
        self.started = True
