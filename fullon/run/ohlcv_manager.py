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
from libs.database_ohlcv import Database as Database_Ohlcv
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
                    self.stop_signals[thread].set()
                    self.threads[thread].join(timeout=1)  # Wait for the thread to finish with a timeout
                    logger.debug(f'{thread}, "has been closed')
                except KeyError:
                    try:
                        logger.error(f"Seems an ohlcv thread {thread} is not existing and cant be stopped")
                    except ValueError:
                        pass
                except Exception as error:
                    logger.error(f"Error stopping ohlcv {thread}: {error}")
                else:
                    logger.info(f"Stopped ohlcv {thread}")
                try:
                    del self.threads[thread]
                    del self.stop_signals[thread]
                except KeyError:
                    pass
                try:
                    del self.stop_signals[thread]
                except KeyError:
                    pass
            else:
                logger.info(f"No running ticker found for exchange {thread}")

    def stop_all(self, exchange="") -> None:
        """
        Stops tick data collection loops for all exchanges.
        """
        # Create a list of keys to prevent RuntimeError due to dictionary size change during iteration
        threads_to_stop = list(self.stop_signals.keys())
        if exchange == "":
            for thread in threads_to_stop:
                self.stop(thread=thread)
        else:
            for thread in threads_to_stop:
                if exchange in thread:
                    self.stop(thread=thread)
        self.started = False

    def database_handler(self, symbol: SymbolStruct):
        res = Database_Ohlcv(exchange=symbol.exchange_name,
                             symbol=symbol.symbol)
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
            since = arrow.get(last_ts).timestamp()
        else:
            since = arrow.utcnow().shift(days=-symbol.backtest).timestamp()
        trade_manager = TradeManager()
        while not stop_signal.is_set():
            time.sleep(1)
            last = trade_manager.update_trades_since(exchange=symbol.exchange_name,
                                                     symbol=symbol.symbol,
                                                     since=since,
                                                     test=test)

            if since == last:
                return None
            since = last
            now = time.time()
            self._update_process(exchange_name=symbol.exchange_name, symbol=symbol.symbol, message="Syncing")
            if since:
                time_difference = now - since
                if time_difference < 55:
                    return
            else:
                return
        del trade_manager

    def fetch_candles(self,
                      symbol: SymbolStruct,
                      stop_signal: threading.Event,
                      exch: Exchange,
                      test: bool = False) -> None:
        """
        Retrieve trade ohlcv data for the specified symbol and timeframe.
        Returns:
            None
        """
        with self.database_handler(symbol=symbol) as dbase:
            last_ts = dbase.get_latest_timestamp(
                table2=symbol.exchange_name+"_" + symbol.symbol.replace("/", "_") + ".candles1m")
        if last_ts:
            since = arrow.get(last_ts).timestamp()
        else:
            since = arrow.utcnow().shift(days=-symbol.backtest).timestamp()
        while not stop_signal.is_set():
            candles = exch.get_candles(symbol=symbol.symbol, frame='1m', since=since)
            last = arrow.get(candles[-1][0]).timestamp()
            with Database_Ohlcv(exchange=symbol.exchange_name, symbol=symbol.symbol) as dbase:
                dbase.fill_candle_table(table='candles1m', data=candles)
            if since == last:
                return None
            since = last
            now = time.time()
            self._update_process(exchange_name=symbol.exchange_name, symbol=symbol.symbol, message="Syncing")
            if test:
                break
            if since:
                time_difference = now - since
                if time_difference < 55:
                    return
            else:
                return

    def fetch_individual_trades_ws(self, symbol: SymbolStruct, test: bool = False) ->  bool:
        """
        Retrieve trade data for the specified symbol and timeframe.
        Returns:
            None
        """
        trades = None
        with cache.Cache() as store:
            trades = store.get_trades_list(
                symbol=symbol.symbol, exchange=symbol.exchange_name)
        if trades:
            with self.database_handler(symbol=symbol) as dbase:
                dbase.save_symbol_trades(data=trades)
            return True
        return False

    @staticmethod
    def _update_process(exchange_name: str, symbol: str, message="Synced") -> bool:
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
                                    message=message)
        return bool(res)

    def delete_before_midnight(self, symbol_struct: SymbolStruct, exchange_key: str):
        """
        """
        with self.database_handler(symbol=symbol_struct) as dbase:
            dbase.delete_before_midnight()
        try:
            del self.stop_signals[exchange_key]
        except KeyError:
            pass

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
            try:
                self.fetch_candles(symbol=symbol_struct, stop_signal=stop_signal, exch=exch, test=test)
                self.delete_before_midnight(symbol_struct=symbol_struct, exchange_key=exchange_key)
            except KeyboardInterrupt:
                return
            if not stop_signal.is_set():
                exch.start_candle_socket(tickers=[symbol_struct.symbol])
                while not stop_signal.is_set():
                    self._update_process(exchange_name=exchange, symbol=symbol)
                time.sleep(9)
                # maybe i need to check here if database is updating
        else:
            try:
                self.fetch_individual_trades(
                    symbol=symbol_struct, stop_signal=stop_signal)
                self._update_process(exchange_name=exchange, symbol=symbol)
            except KeyboardInterrupt:
                return
            if not stop_signal.is_set():
                exch.start_trade_socket(tickers=[symbol_struct.symbol])
            while not stop_signal.is_set():
                msg = (
                        f"Getting trades from webservice for "
                        f"{exch.exchange}:{symbol_struct.symbol}"
                      )
                logger.debug(msg)
                trades = self.fetch_individual_trades_ws(symbol=symbol_struct)
                if test:
                    logger.debug("setting stop signal")
                    stop_signal.set()
                    break
                now = arrow.now()
                pause_until = now.shift(minutes=1).floor('minute')
                pause_duration = (pause_until - now).total_seconds()
                if trades:
                    log_message = (
                        f"Updating trade database for {exch.exchange}:{symbol_struct.symbol}. "
                        f"Pausing until ({pause_until.format()})"
                    )
                    logger.info(log_message)
                    self._update_process(exchange_name=exchange, symbol=symbol)
                check_interval = 0.3  # How often to check for the stop signal, in seconds
                total_checks = int(pause_duration / check_interval)
                for _ in range(total_checks):
                    if stop_signal.is_set():
                        logger.info("Stop signal received. Exiting pause loop.")
                        break
                    time.sleep(check_interval)
                # some times it escapes the loop a few milis before the minute and it creates havoc. this
                # makes sure it doesnt happen
                pause.until(pause_until.timestamp())
        del exch

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
        self.started = True

    def run_loop_one_exchange(self, exchange, test=False) -> None:
        """
        Runs the OHLCV loop for one exchanges and update frames.
        """
        with Database() as dbase:
            symbols = dbase.get_symbols(all=True, exchange=exchange)
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
        self.started = True
