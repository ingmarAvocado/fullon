"""
Manages the tick data for multiple exchanges.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import threading
import time
import arrow
from prompt_toolkit.styles.base import Attrs
from libs import exchange, log
from libs.cache import Cache
from libs.structs.tick_struct import TickStruct
from os import getpid


logger = log.fullon_logger(__name__)


class TickManager:
    """
    Manages the tick data for multiple exchanges.
    """
    started: bool = False

    def __init__(self) -> None:
        """Initializes the Tick Manager."""
        self.stop_signals = {}
        self.thread_lock = threading.Lock()
        self.threads = {}
        self.monitor_thread: threading.Thread
        self.monitor_thread_signal: threading.Event

    def __del__(self) -> None:
        self.stop_all()
        self.started = False

    def stop(self, thread):
        """
        Stops the tick data collection loop for the specified exchange.
        """
        with self.thread_lock:  # Acquire the lock before accessing shared resources
            if thread in self.stop_signals:
                try:
                    _thread = self.threads[thread]
                    del self.threads[thread]
                    _thread.join(timeout=2)  # Wait for the thread to finish with a timeout
                    logger.info(f"Stopped tick {thread}")
                except KeyError:
                    pass
                except Exception as error:
                    logger.warning(f"Error stopping tick {thread}: {error}")
            else:
                logger.info(f"No running ticker found for exchange {thread}")

    def stop_all(self) -> None:
        """
        Stops tick data collection loops for all exchanges.
        """
        # Create a list of keys to prevent RuntimeError due to dictionary size change during iteration
        try:
            self.monitor_thread_signal.set()
            self.monitor_thread.join(timeout=1)
        except AttributeError:
            pass
        threads_to_stop = list(self.threads.keys())
        for thread in threads_to_stop:
            self.stop(thread=thread)
        self.started = False
        self.clean_cache()

    def clean_cache(self) -> None:
        """
        Cleans the table of process from tick processes
        """
        store = Cache()
        store.delete_from_top(component='tick')
        for key in store.get_keys(key='tickers:*'):
            store.delete_from_top(component=key)
        del store

    def get_cat_exchanges(self) -> List[Dict[str, Any]]:
        """
        Retrieves and returns a list of supported exchanges with their names and IDs.
        The function accesses the cache to retrieve a list of supported exchanges. It then
        formats this list to only include the name and ID of each exchange.

        Returns:
        - List[Dict[str, Any]]: A list of dictionaries where each dictionary represents 
          an exchange with its 'name' and 'id'.

        Examples:
        >>> get_cat_exchanges()
        [{'name': 'Binance', 'id': 'binance'}, {'name': 'Kraken', 'id': 'kraken'}, ...]
        """
        with Cache() as store:
            exchanges = store.get_cat_exchanges()
        ret_list = [{'name': exch['name'], 'id': exch['id']} for exch in exchanges]
        return ret_list

    def btc_ticker(self) -> float:
        """
        Fetches the current BTC price in USD from either Deribit or FTX.

        The function first tries to get the price using the symbol "XBT/USD". If unsuccessful,
        it attempts to retrieve the price using the symbol "BTC/USD". If both attempts fail, it logs an
        informational message and returns 0.

        Returns:
        - float: The current BTC price in USD. If the price cannot be fetched, returns 0.

        Examples:
        >>> btc_ticker()
        55678.24
        """
        cache_cur = Cache()
        price = cache_cur.get_price(symbol="XBT/USD")
        if price:
            del cache_cur
            return price
        price = cache_cur.get_price(symbol="BTC/USD")
        del cache_cur
        if price:
            return price
        logger.info("Could not get btc_ticker")
        return 0

    def get_tickers(self) -> list[TickStruct]:
        """
        Retrieves and returns the current ticker list.

        The function accesses the cache to get the list of tickers and then returns it.

        Returns:
        - list: The current list of tickers.

        """
        tickers = []
        with Cache() as store:
            tickers = store.get_tickers()
        return tickers

    def get_exchange_pairs(self, exchange_name: str) -> List:
        """
        Retrieves and returns a list of supported pairs for a specific exchange.

        The function accesses the cache to get a list of supported pairs for the provided
        exchange name. It then formats this list to only include the symbol of each pair.

        Parameters:
        - exchange_name (str): The name of the exchange for which pairs are to be retrieved.

        Returns:
        - List: A list of supported pairs' symbols for the given exchange.

        Examples:
        >>> get_exchange_pairs('Binance')
        ['BTC/USD', 'ETH/USD', ...]
        """
        with Cache() as store:
            pairs = store.get_symbols(exchange=exchange_name)
        result = []
        for pair in pairs:
            result.append(pair.symbol)
        return result

    def check_most_recent_tick(self, exchange_name: str):
        """
        Checks if the most recent tick from a specified exchange is within the last 5 minutes.

        This function retrieves all ticker data for a specified exchange and determines the timestamp
        of the most recent tick. If the most recent tick is older than 5 minutes from the current time,
        the function returns False. Otherwise, it returns True.

        Parameters:
        - exchange_name (str): The name of the exchange for which to check the most recent tick.

        Returns:
        - bool: True if the most recent tick is within the last 5 minutes, otherwise False.

        Raises:
        None. If no tick data is found for the exchange, the function considers the most recent tick to be 1 day old.

        Notes:
        - The function uses the `Cache` context manager to access stored tick data.
        - Ticker timestamps are compared using the 'arrow' library.

        Examples:
        >>> check_most_recent_tick('Binance')
        True
        >>> check_most_recent_tick('UnknownExchange')
        False
        """
        with Cache() as store:
            tickers = store.get_tickers(exchange=exchange_name)
            most_recent: arrow.Arrow = arrow.utcnow().shift(days=-1)
            for tick in tickers:
                tick_time = arrow.get(tick.time)
                if tick_time > most_recent:
                    most_recent = tick_time
            cur_time = arrow.utcnow()
            time_difference = cur_time.timestamp() - most_recent.timestamp()
            if time_difference > 5 * 60:  # 5 minutes
                return False
            else:
                return True

    def start(self, exchange_name: str) -> None:
        """
        Starts the tick data collection loop for the specified exchange.
        """
        # Create a new stop signal Event for the current thread and store it in the stop_signals dictionary
        #print(exchange_name)
        stop_signal = threading.Event()
        self.stop_signals[exchange_name] = stop_signal
        tick_exchange = exchange.Exchange(exchange_name)
        with Cache() as store:
            store.del_exchange_ticker(exchange=exchange_name)
        if tick_exchange.has_ticker():
            pairs = self.get_exchange_pairs(exchange_name=exchange_name)
            if not pairs:
                return self.stop(exchange_name)
            tick_exchange.start_ticker_socket(tickers=pairs)

        while not stop_signal.is_set():
            check = self.check_most_recent_tick(exchange_name=exchange_name)
            if check:
                with Cache() as store:
                    store.update_process(tipe="tick",
                                         key=exchange_name,
                                         message="Updated")
                for _ in range(10):  # 5 * 0.2 seconds = 1 seconds
                    if stop_signal.is_set():
                        break
                    time.sleep(0.2)
            else:
                tick_exchange.stop_ticker_socket()
                time.sleep(1)
                if tick_exchange.has_ticker():
                    tick_exchange.start_ticker_socket(tickers=pairs)

    def run_loop(self) -> None:
        """
        Starts tick data collection loops for all supported exchanges.
        """
        exchanges = self.get_cat_exchanges()
        for exch in exchanges:
            thread = threading.Thread(target=self.start,
                                      args=(exch['name'],))
            thread.daemon = True
            thread.start()
            logger.info(f"Websocket loop for exchange {exch['name']} is up and running")
            self.threads[exch['name']] = thread  # Store the thread in the threads dictionary
            self.register_process(exch=exch)
        # Start a new thread to monitor and relaunch dead threads
        self.launch_socket_monitor()
        statuses_updated: int = 0
        while statuses_updated < len(exchanges):
            for exch in exchanges:
                with Cache() as store:
                    proc = store.get_process(tipe="tick", key=exch['name'])
                if proc:
                    if proc['message'] == 'Updated':
                        statuses_updated += 1
                time.sleep(1)
        self.started = True

    def run_loop_one_exchange(self, exchange_name: str, monitor: bool = False) -> None:
        """
        Starts tick data collection loops for a particular exchange.
        """
        exchanges = self.get_cat_exchanges()
        for exch in exchanges:
            if exch['name'] == exchange_name:
                thread = threading.Thread(target=self.start,
                                          args=(exchange_name,))
                thread.daemon = True
                thread.start()
                self.threads[exch['name']] = thread  # Store the thread in the threads dictionary
                time.sleep(0.5)
                self.register_process(exch=exch)

        # Start a new thread to monitor and relaunch dead threads
        if monitor:
            self.launch_socket_monitor()

    def launch_socket_monitor(self) -> None:
        """
        Launches a new thread to monitor and relaunch dead threads.
        """
        monitor_thread = threading.Thread(target=self.relaunch_dead_threads)
        monitor_thread.daemon = True
        monitor_thread.start()
        self.monitor_thread = monitor_thread

    def register_process(self, exch: Dict[str, Any]) -> None:
        """
        Registers a new process in the cache.
        """
        with Cache() as store:
            params = [exch['name'], exch['id']]
            store.new_process(tipe="tick",
                              key=exch['name'],
                              pid=f"thread:{getpid()}",
                              params=params,
                              message="Started")

    def thread_is_working(self, key: str, retries: int = 12) -> bool:
        """
        Determines if a thread, identified by its `ex_id`, is actively updating based on a cached timestamp.

        The function checks a stored timestamp in a cache to determine if the thread
        associated with the given `ex_id` has been updating recently (within the last 4 minutes).
        If the timestamp is not recent, or if there's no timestamp available,
        the function will sleep for a short duration and re-attempt up to the specified number of retries.

        Parameters:
        - ex_id (str): The identifier for the thread whose status needs to be checked.
        - retries (int): The number of times the function should retry checking if the thread is working.
                         Defaults to 12.

        Returns:
        - bool: True if the thread is working (i.e., if it has updated within the last 4 minutes),
                otherwise False.

        """
        while retries > 0:
            with Cache() as store:
                status = store.get_process(tipe='tick', key=key)
            if not status:
                time.sleep(5)
                retries -= 1
                continue

            last = arrow.get(status['timestamp'])
            now = arrow.utcnow().shift(minutes=-4)
            if last > now:
                return True  # thread is working if it has updated in the last 4 minutes
            time.sleep(5)
            retries -= 1
        return False

    def relaunch_dead_threads(self) -> None:
        """
        Monitors and relaunches dead threads for tick data collection.
        """
        logger.info("Launching ticker thread monitor")
        self.monitor_thread_signal = threading.Event()
        while not self.monitor_thread_signal.is_set():
            for exchange_name, thread in list(self.threads.items()):
                if not thread.is_alive() or not self.thread_is_working(key=exchange_name):
                    logger.error(f"Thread for tick exchange {exchange_name} has died, relaunching...")
                    self.run_loop_one_exchange(exchange_name=exchange_name)
                time.sleep(0.1)  # Add a small sleep to prevent high CPU usage
            for _ in range(50):  # 50 * 0.2 seconds = 10 seconds
                if self.monitor_thread_signal.is_set():
                    break
                time.sleep(0.2)
