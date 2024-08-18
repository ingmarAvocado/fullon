"""
Trade Manager

This script contains the TradeManager class that manages the updating of trade data
from various exchanges. It includes methods to fetch all exchanges, update trades,
and run loops to periodically update trade data.
"""

import time
import threading
import arrow
from libs import exchange, log
from libs.caches.trades_cache import Cache
from libs.database import Database
from libs.exchange import Exchange
from libs.structs.exchange_struct import ExchangeStruct
from libs.database_ohlcv import Database as Database_ohlcv
from typing import Union, Optional

logger = log.fullon_logger(__name__)


class TradeManager:

    started: bool = False

    def __init__(self):
        """Initialize the TradeManager and log the start."""
        self.started = True
        logger.info("Initializing Trade Manager...")
        self.lastrecord = ""
        self.stop_signals = {}
        self.thread_lock = threading.Lock()
        self.threads = {}

    def __del__(self):
        self.started = False
        self.stop_all()

    def stop(self, thread):
        """
        Stops the trade data collection loop for the specified exchange.
        """
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

    def stop_all(self) -> None:
        """
        Stops trade data collection loops for all exchanges.
        """
        threads_to_stop = list(self.stop_signals.keys())
        for thread in threads_to_stop:
            self.stop(thread=thread)
        self.started = False

    @staticmethod
    def _update_process(exch: exchange.Exchange) -> bool:
        """
        Update the usertrade status in cache.

        Args:
            exchange_id (int): The name of the exchange.
        Returns:
            bool: Returns True if the process is successfully updated in the cache, else False.
        """
        key = f"{exch.ex_id}-{exch.exchange}"
        with Cache() as store:
            res = store.update_user_trade_status(key=key)
        return bool(res)

    def update_trades(self, ex, symbol, test=False):
        """
        Update trades for a specific exchange and symbol.

        Args:
            ex (exchange.Exchange): An instance of the Exchange class.
            symbol (str): The trading symbol.
            test (bool, optional): Whether to run in test mode or not. Defaults to False.
        """
        with Database_ohlcv(exchange=ex.exchange,
                            symbol=symbol.symbol) as dbase:
            now = arrow.utcnow().int_timestamp
            then = dbase.get_latest_timestamp(table="trades")
            # If the latest timestamp doesn't exist, define it.
            if not then:
                then = now - (int(symbol.backtest) * 24 * 60 * 60)
                then = arrow.get(then).replace(
                    minute=0, second=0, hour=0).int_timestamp
            else:
                then = arrow.get(then).int_timestamp
            # Refresh if more than one minute has passed.
            while now - then >= 59:
                table = dbase.get_schema() + ".trades"
                seconds = now - then
                days = round(seconds/60/60/24, 2)
                mesg = f"Installing/Updating trade database of {symbol.symbol}.\
                Behind for seconds({seconds})  days ({days})  on table {table}"
                logger.info(mesg)
                data = ex.fetch_trades(
                    symbol=symbol.symbol, since=then, limit=500)
                if data and not test:
                    dbase.save_symbol_trades(data=data)
                    then = int(data[-1:][0].timestamp)
                if test:
                    break

    def update_trades_since(self,
                            exchange: str,
                            symbol: str,
                            since: Union[int, float],
                            test: bool = False) -> Optional[float]:
        """
        Update trades for a specific exchange and symbol since a given timestamp.

        Args:
            exchange (str): The exchange name.
            symbol (str): The trading symbol.
            since (int): The timestamp to start updating trades from.
            test (bool, optional): Whether to run in test mode or not. Defaults to False.

        Returns:
            None
        """
        exchange_conn = Exchange(exchange=exchange)
        with Database_ohlcv(exchange=exchange, symbol=symbol) as dbase:
            table = f"{dbase.get_schema()}.trades"
            then = dbase.get_latest_timestamp(table2=table)
        if not then:
            then = since
        else:
            then = arrow.get(then).float_timestamp
        now = arrow.utcnow().float_timestamp
        time_difference = now - then

        log_message = (f"Installing/Updating trade database for {symbol}. Behind "
                       f"({round(time_difference, 2)}) seconds "
                       f"({round(time_difference/60/60/24, 2)}) "
                       f"days table {table}")
        try:
            logger.info(log_message)
        except ValueError:
            pass
        try:
            data = exchange_conn.fetch_trades(symbol=symbol,
                                              since=then,
                                              limit=1000)
        except (EOFError, RuntimeError):
            return
        if not data or test:
            return
        with Database_ohlcv(exchange=exchange, symbol=symbol) as dbase:
            dbase.save_symbol_trades(data=data)
        latest_timestamp = float(data[-1].timestamp)+0.000001
        return latest_timestamp

    def _update_user_trades(self, exch: exchange.Exchange) -> arrow.Arrow:
        """
        Updates user trades.

        Args:
            exch (Exchange): An Exchange object for the user's selected exchange.
            test (bool): A flag indicating whether this is a test run.
        """
        with Database() as dbase:
            last_trade = dbase.get_trades(ex_id=exch.params.ex_id, last=True)

        last_id = ''
        if last_trade:
            trade = last_trade[0]
            timestamp = arrow.get(trade.time)
            last_id = trade.ex_trade_id
        else:
            timestamp = arrow.get('2023-01-01')
        while True:
            tradestamp = timestamp.timestamp() + timestamp.microsecond / 1000000.0
            trades = exch.fetch_my_trades(since=tradestamp, last_id=last_id)
            if trades:
                logger.debug("Saving user trades")
                with Database() as dbase:
                    dbase.save_trades(trades=trades)
                # Update timestamp with the time of the last fetched trade
                try:
                    timestamp = arrow.get(trades[-1].time)
                    last_id = trades[-1].ex_trade_id
                except KeyError:
                    last_trade = dbase.get_trades(ex_id=exch.params.ex_id, last=True)
                    timestamp = arrow.get(last_trade[0].time)
                    break
            else:
                break
            import ipdb
            ipdb.set_trace()
            self._update_process(exch=exch)
            time.sleep(1)
        return timestamp

    def _update_user_trades_ws(self,
                               exch: exchange.Exchange,
                               date: arrow.Arrow,
                               test: bool = False) -> None:
        """
        Continuously updates user trades at regular intervals using a WebSocket connection.

        Args:
            exch (Exchange): An Exchange object for the user's selected exchange.
            date (arrow.Arrow): The date of the last trade.
            test (bool): A flag indicating whether this is a test run.
        """
        if not exch.ex_id:
            logger.error("exch doesn't have ex_id set")
        exch.start_my_trades_socket()
        timestamp = date.timestamp() + date.microsecond / 1000000.0
        try:
            while not self.stop_signals[exch.ex_id].is_set():
                trade = None
                try:
                    with Cache() as store:
                        trade = store.pop_my_trade(uid=exch.uid, exchange=exch.ex_id)
                except TimeoutError:
                    try:
                        logger.info("no trade so far")
                    except ValueError:
                        pass
                    pass
                if trade:
                    if float(trade.timestamp) > timestamp:
                        with Database() as dbase:
                            dbase.save_trades(trades=[trade])
                self._update_process(exch=exch)
                if test:
                    break
                time.sleep(1)
        except KeyError:
            logger.debug(f"Seems key {exch.ex_id} is not in stopped signals anymore")
        return

    def update_user_trades(self, ex_id: int):
        """
        Update a user's trades.

        This method retrieves the user's exchange information and creates an Exchange instance. Then it
        calls the '_update_user_trades' method to update the account. If the user's exchange is not found,
        the method returns False.

        Args:
            ex_id (int): The exchange ID of the user's account.
            test (bool, optional): A flag to enable test mode. Defaults to False.

        """
        stop_signal = threading.Event()
        self.stop_signals[ex_id] = stop_signal
        with Cache() as store:
            user_ex: ExchangeStruct = store.get_exchange(ex_id=ex_id)
        if user_ex.name == '':
            return False
        exch = exchange.Exchange(exchange=user_ex.cat_name, params=user_ex)
        # Call the '_user_account_flow' method to update the account
        last_date = self._update_user_trades(exch=exch)
        self._update_user_trades_ws(exch=exch, date=last_date)

    def run_user_exchange_trades(self, user_ex: ExchangeStruct) -> None:
        """
        Run account loop to start threads for a user's exchange.
        """
        # Start a new thread
        thread = threading.Thread(target=self.update_user_trades,
                                  args=(user_ex.ex_id,))
        thread.daemon = True
        thread.start()
        logger.info(f"started to listen to trades for ex_id {user_ex.ex_id}")
        # Store the thread in the threads dictionary
        self.threads[user_ex.ex_id] = thread

    def run_users_trades(self) -> None:
        """
        Run account loop to start threads for each user's active exchanges.

        The method retrieves the list of users and their active exchanges, then starts a thread for each
        exchange, storing the thread in the 'threads' dictionary. Sets the 'started' attribute to True
        when completed.
        """
        with Cache() as store:
            exchanges = store.get_exchanges()
        for exch in exchanges:
            # Start a new thread for each exchange
            thread = threading.Thread(target=self.update_user_trades,
                                      args=(exch.ex_id,))
            thread.daemon = True
            thread.start()
            # Store the thread in the threads dictionary
            self.threads[exch.ex_id] = thread
