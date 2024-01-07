"""
Manages OHLCV functions to get and to save to db
"""
import time
import threading
import arrow
import pause
from libs import cache, log
from libs.database import Database
from libs.exchange import Exchange
from libs.structs.symbol_struct import SymbolStruct
from libs.models.ohlcv_model import Database as Database_Ohlcv
from run.trade_manager import TradeManager
from os import getpid
from signal import SIGTERM

logger = log.fullon_logger(__name__)


class OhlcvManager:
    """
    A class for managing Open-High-Low-Close-Volume (OHLCV) data for financial symbols.

    Attributes:
    - started (bool): Whether the OHLCV Manager has been started or not.
    """
    started: bool = False

    def __init__(self) -> None:
        """
        Initializes the OHLCV Manager.
        """
        # logger.info("Initializing OHLCV Manager...")
        self.stop_signals = {}
        self.threads = {}
        self.thread_lock = threading.Lock()
        self.clean_cache()
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
                self.stop_signals[thread].set()
                try:
                    self.threads[thread].join(timeout=1)  # Wait for the thread to finish with a timeout
                except Exception as error:
                    logger.error(f"Error stopping ohlcv {thread}: {error}")
                else:
                    logger.info(f"Stopped ohlcv {thread}")
                try:
                    del self.threads[thread]
                except KeyError:
                    pass
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
        threads_to_stop = list(self.stop_signals.keys())
        for thread in threads_to_stop:
            self.stop(thread=thread)
        self.started = False

    def database_handler(self, symbol: SymbolStruct, simul=False):
        res = Database_Ohlcv(exchange=symbol.exchange_name,
                             symbol=symbol.symbol,
                             simul=simul)
        return res

    def clean_cache(self) -> None:
        """
        Cleans the table of process from tick processes
        """
        store = cache.Cache()
        store.delete_from_top(component='ohlcv')
        del store

    def start(self, symbol: str, exchange: str) -> None:
        """
        Sets the process title and starts the OHLCV loop for a specific exchange and update frame.

        Args:
        - exchange (str): The name of the exchange category to retrieve symbols for.
        - symbols (str): A symbol to update.

        Returns:
        - None:
        """
        return self.run_ohlcv_loop(symbol=symbol, exchange=exchange)

    def delete_schema(self, symbol) -> bool:
        """
        Deletes the schema in the database.
        Returns:
            bool: True if successful.
        """
        with self.database_handler(symbol=symbol) as dbase:
            dbase.delete_schema()
        return True

    def _get_since(self, symbol: SymbolStruct) -> float:
        """
        Comments
        """
        table = "candles1m"
        now = arrow.utcnow().timestamp()
        with self.database_handler(symbol=symbol) as dbase:
            then = dbase.get_latest_timestamp(table=table)
        if not then:
            then = now - (int(self.symbol.backtest) * 24 * 60 * 60)
            then = arrow.get(then).replace(minute=0, second=0, hour=0).timestamp()
        else:
            then = arrow.get(then).timestamp()
        return then

    def fetch_individual_trades(self, symbol: SymbolStruct, stop_signal, test: bool = False) -> None:
        """
        Retrieve trade data for the specified symbol and timeframe.
        Returns:
            None
        """
        with self.database_handler(symbol=symbol) as dbase:
            last_ts = dbase.get_latest_timestamp(
                table2=symbol.exchange_name+"_" + symbol.symbol.replace("/", "_") + ".trades")
        if last_ts:
            since = arrow.get(last_ts).float_timestamp
        else:
            since = time.time() - (symbol.backtest * 24 * 60 * 60) # timestamp 'symbol.backtest' days ago
        trade_manager = TradeManager()
        #while not stop_signal.is_set():
        while True:
            last = trade_manager.update_trades_since(exchange=symbol.exchange_name,
                                                     symbol=symbol.symbol,
                                                     since=since,
                                                     test=test)
            if since == last:
                return None
            since = last
            now = time.time()
            if since:
                time_difference = now - since
                if time_difference < 55:
                    return
            else:
                return

    def fetch_individual_trades_ws(self, symbol: SymbolStruct, test: bool = False) -> None:
        """
        Retrieve trade data for the specified symbol and timeframe.
        Returns:
            None
        """
        trade = None
        with cache.Cache() as store:
            trades = store.get_trades_list(
                symbol=symbol.symbol, exchange=symbol.exchange_name)
        if trades:
            with self.database_handler(symbol=symbol) as dbase:
                dbase.save_symbol_trades(trades)

    @staticmethod
    def _update_process(exchange_name: str, symbol: str) -> bool:
        """
        Update the process status in cache. This function generates a new process ID 
        and updates the cache with a new message status.

        Args:
            exchange_name (str): The name of the exchange.
            symbol (str): The trading pair symbol.

        Returns:
            bool: Returns True if the process is successfully updated in the cache, else False.
        """

        key = f"{exchange_name}:{symbol}"
        with cache.Cache() as store:
            res = store.new_process(tipe="ohlcv",
                                    key=key,
                                    pid=f"thread:{getpid()}",
                                    params=[key],
                                    message="Synced")
        return bool(res)

    def run_ohlcv_loop(self, symbol: str, exchange: str, test: bool = False) -> None:
        """
        Runs the main OHLCV loop for a specific exchange and update frame, using the list of symbols
        retrieved from the database.

        Args:
        - exchange (str): The Name of the exchange category to retrieve symbols for.
        - symbol (str): A symbol to update.
        - test (bool, optional): Whether to run the loop in test mode.

        Returns:
        - None
        """
        exchange_key = f"{exchange}:{symbol}"
        logger.info(f"OHLCV for exchange {exchange_key} is up and running")

        # Create a new stop signal Event for the current thread and store it in the stop_signals dictionary
        stop_signal = threading.Event()
        self.stop_signals[exchange_key] = stop_signal
        with cache.Cache() as store:
            symbol_struct: SymbolStruct = store.get_symbol(
                symbol=symbol, exchange_name=exchange)
        if not symbol_struct:
            return

        exch = Exchange(exchange=symbol_struct.exchange_name)

        with self.database_handler(symbol=symbol_struct) as dbase:
            dbase.install_schema(ohlcv=symbol_struct.ohlcv_view)

        if exch.has_ohlcv():
            while not stop_signal.is_set():
                self.fetch_individual_trades(
                    symbol=symbol_struct, stop_signal=stop_signal)
                pause_time = arrow.now().shift(minutes=1).floor('minute')
                self._update_process(exchange_name=exchange, symbol=symbol)
                if test:
                    break
                while arrow.now() < pause_time:
                    if stop_signal.is_set():
                        break
                    time.sleep(0.2)
        else:
            try:
                self.fetch_individual_trades(
                    symbol=symbol_struct, stop_signal=stop_signal)
                self._update_process(exchange_name=exchange, symbol=symbol)
            except KeyboardInterrupt:
                pass
            if not stop_signal.is_set():
                exch.start_trade_socket(tickers=[symbol_struct.symbol])
            while not stop_signal.is_set():
                msg = (
                        f"Getting trades from webservice for "
                        f"{exch.exchange}:{symbol_struct.symbol}"
                      )
                logger.debug(msg)
                self.fetch_individual_trades_ws(symbol=symbol_struct)
                if test:
                    break
                pause_time = arrow.now().shift(minutes=1).floor('minute')
                log_message = (
                    f"Updating trade database for {exch.exchange}:{symbol_struct.symbol}. "
                    f"Pausing until ({pause_time.naive})"
                )
                logger.info(log_message)
                self._update_process(exchange_name=exchange, symbol=symbol)
                pause.until(pause_time.naive)
        del exch
        # Remove the stop signal from the dictionary when the loop is stopped
        with self.database_handler(symbol=symbol_struct) as dbase:
            dbase.delete_before_midnight()
        try:
            del self.stop_signals[exchange_key]
        except KeyError:
            pass

    def run_loop(self, test=False) -> None:
        """
        Runs the OHLCV loop for all exchanges and update frames.
        """
        with Database() as dbase:
            symbols = dbase.get_symbols(all=True)
        for symbol in symbols:
            if not symbol.only_ticker:
                thread = threading.Thread(target=self.start,
                                          args=(symbol.symbol,
                                                symbol.exchange_name))
                thread.daemon = True
                thread.start()
                key = f"{symbol.exchange_name}:{symbol.symbol}"
                self.threads[key] = thread  # Store the thread in the threads dictionary
                with cache.Cache() as store:
                    store.new_process(tipe="ohlcv",
                                      key=key,
                                      pid=f"thread:{getpid()}",
                                      params=[key],
                                      message="Started")
        self.monitor_thread = threading.Thread(target=self.relaunch_dead_threads)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        self.started = True

    def thread_is_working(self, exchange: str, symbol: str, retries: int = 12) -> bool:
        """
        Determines if a thread, identified by its `ex_id`, is actively updating based on a cached timestamp.

        The function checks a stored timestamp in a cache to determine if the thread
        associated with the given `ex_id` has been updating recently (within the last 4 minutes).
        If the timestamp is not recent, or if there's no timestamp available,
        the function will sleep for a short duration and re-attempt up to the specified number of retries.

        Parameters:
        - exchange (str): The first part of identifier for the thread whose status needs to be checked.
        - symbol (str) The second part of identifier for the thread whose status needs to be checked.
        - retries (int): The number of times the function should retry checking if the thread is working.
                         Defaults to 12.

        Returns:
        - bool: True if the thread is working (i.e., if it has updated within the last 4 minutes),
                otherwise False.

        """
        while retries > 0:
            with cache.Cache() as store:
                status: dict = store.get_process(tipe='ohlcv', key=f"{exchange}:{symbol}")
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

    def relaunch_dead_threads(self, test=False):
        """ comment """
        self.monitor_thread_signal = threading.Event()
        logger.info("Thread monitor for ohlcv started")
        while not self.monitor_thread_signal.is_set():
            for exchange_key, thread in list(self.threads.items()):
                exchange, symbol = exchange_key.split(':')
                if not thread.is_alive() or not self.thread_is_working(exchange=exchange, symbol=symbol):
                    logger.info(f"Thread for {exchange_key} has died, relaunching...")
                    new_thread = threading.Thread(
                        target=self.run_ohlcv_loop, args=(symbol, exchange,))
                    new_thread.daemon = True
                    new_thread.start()
                    self.threads[exchange_key] = new_thread
                    if test:
                        return
                    time.sleep(0.1)
                break
            for _ in range(50):  # 50 * 0.2 seconds = 10 seconds
                if self.monitor_thread_signal.is_set():
                    break
                time.sleep(0.2)
