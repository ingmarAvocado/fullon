"""
This class manages user accounts from exchanges.
Gets the trades, account totals, etc.
"""
import time
import threading
from typing import Optional
import arrow
from libs import settings
from libs import exchange, log
from libs.caches.account_cache import Cache
from libs.structs.exchange_struct import ExchangeStruct
from libs.calculations import TradeCalculator
from run.trade_manager import TradeManager

logger = log.fullon_logger(__name__)


class Reg:
    """ helper class"""
    def __init__(self):
        """ description """

    def __del__(self):
        """ description """

    def value(self):
        """ description """


class AccountManager:
    """ main account class"""

    started: bool = False
    trade: Optional[TradeManager] = None

    def __init__(self):
        """ description """
        # logger.info("Initializing Account Update Manager")
        self.lastrecord = ""
        self.stop_signals = {}
        self.thread_lock = threading.Lock()
        self.threads = {}
        self.stop_signals_calc: threading.Event
        self.calculator_thread: Optional[threading.Thread] = None
        self.clean_cache()

    def clean_cache(self) -> None:
        """
        Cleans the table of process from tick processes
        """
        with Cache() as store:
            store.delete_from_top(component='account')
            store.clean_positions()

    def __del__(self):
        self.stop_all()
        self.started = False

    def stop(self, exchange):
        """
        Stops the tick data collection loop for the specified exchange.
        """
        with self.thread_lock:  # Acquire the lock before accessing shared resources
            if exchange in self.stop_signals:
                try:
                    self.stop_signals[exchange].set()
                    _thread = self.threads[exchange]
                except KeyError:
                    pass
                try:
                    del self.threads[exchange]
                except KeyError:
                    pass
                try:
                    _thread.join(timeout=1)  # Wait for the thread to finish with a timeout
                except Exception as error:
                    logger.error(f"Error stopping account {exchange}: {error}")
                else:
                    logger.info(f"Stopped account {exchange}")
            else:
                logger.info(f"Thread not running {exchange}")

    def stop_all(self) -> None:
        """
        Stops tick data collection loops for all exchanges.
        """
        # Create a list of keys to prevent RuntimeError due to dictionary size change during iteration
        try:
            self.stop_signals_calc.set()
            self.calculator_thread.join(timeout=1)
        except AttributeError:
            pass
        if self.trade:
            self.trade.stop_all()
        threads_to_stop = list(self.stop_signals.keys())
        for thread in threads_to_stop:
            self.stop(exchange=thread)
        self.started = False

    def _user_account_flow(self,  user_ex: ExchangeStruct) -> None:
        """
        Continuously updates user account balances and positions at regular intervals.
        Args:
            user_ex (UserExchange): A UserExchange object containing user
                                    and exchange information.
            exch (ExchangeStruct): An Exchange object for the user's selected exchange.
        """
        stop_signal = threading.Event()
        self.stop_signals[user_ex.ex_id] = stop_signal
        exch = exchange.Exchange(user_ex.cat_name, user_ex)
        intervals = int(settings.UPDATE_ACCOUNT_INTERVAL / 0.2)
        trade = TradeManager()
        trade.run_user_exchange_trades(user_ex=user_ex)
        while not self.stop_signals[user_ex.ex_id].is_set():
            try:
                account = exch.get_balances()
                # If there are any account balances, update user account and positions
                if account:
                    # Get the user's last positions for the current exchange
                    with Cache() as store:
                        store.upsert_user_account(
                            ex_id=user_ex.ex_id, account=account)
                        pos = exch.get_positions()
                        store.upsert_positions(ex_id=user_ex.ex_id, positions=pos)
                        store.update_process(tipe="account",
                                             key=user_ex.name,
                                             message="Updated")
                else:
                    break
                for _ in range(intervals):  # intervals * 0.2 seconds = settings.UPDATE_ACCOUNT_INTERVAL
                    if self.stop_signals[user_ex.ex_id].is_set():
                        break
                    time.sleep(0.2)
            except (EOFError, KeyError):
                return
        self.stop_signals.pop(user_ex.ex_id)

    def update_user_account(self, ex_id: int) -> None:
        """
        Update a user's account information.

        This method retrieves the user's exchange information and creates an Exchange instance. Then it
        calls the '_user_account_flow' method to update the account. If the user's exchange is not found,
        the method returns False.

        Args:
            ex_id (int): The exchange ID of the user's account.

        Returns:
            bool: True if the account update was successful, False otherwise.
        """
        with Cache() as store:
            user_ex: ExchangeStruct = store.get_exchange(ex_id=ex_id)
        if user_ex.name == '':
            return
        thread = threading.Thread(target=self._user_account_flow,
                                  args=(user_ex,))
        thread.daemon = True
        thread.start()
        # Store the thread in the threads dictionary
        self.threads[user_ex.ex_id] = thread
        self.register_process(tipe='account', exch=user_ex, mesg="Started")
        logger.info("Account manager for user exchange %s started", user_ex.name)

    def calculator_loop(self) -> None:
        """
        Roi calculator for trades
        """
        logger.info("Started trade ROI calculator")
        stop_signal = threading.Event()
        self.stop_signals_calc = stop_signal
        while not stop_signal.is_set():
            trade = TradeCalculator()
            trade.calculate_user_trades()
            for _ in range(140):
                if stop_signal.is_set():
                    break
                time.sleep(0.2)
        del self.stop_signals_calc

    def run_account_loop(self) -> None:
        """
        Run account loop to start threads for each user's active exchanges.

        The method retrieves the list of users and their active exchanges, then starts a thread for each
        exchange, storing the thread in the 'threads' dictionary. Sets the 'started' attribute to True
        when completed.
        """
        with Cache() as store:
            store.delete_process(tipe="account")
            exchanges = store.get_exchanges()
        for exch in exchanges:
            self.update_user_account(ex_id=exch.ex_id)
        # Set the started attribute to True after starting all threads
        self.started = True
        if not self.calculator_thread:
            self.calculator_thread = threading.Thread(target=self.calculator_loop)
            self.calculator_thread.daemon = True
            self.calculator_thread.start()
        self.accounts_updates(exchanges=exchanges)
        logger.info("Account loop started and in background")

    def run_loop_one_exchange(self, exchange) -> None:
        """
        Run account loop to start threads for each user's active exchanges.

        The method retrieves the list of users and their active exchanges, then starts a thread for each
        exchange, storing the thread in the 'threads' dictionary. Sets the 'started' attribute to True
        when completed.
        """
        with Cache() as store:
            exchanges = store.get_exchanges()
        for exch in exchanges:
            if exch.cat_name == exchange:
                self.update_user_account(ex_id=exch.ex_id)
        # Set the started attribute to True after starting all threads
        self.started = True
        if not self.calculator_thread:
            self.calculator_thread = threading.Thread(target=self.calculator_loop)
            self.calculator_thread.daemon = True
            self.calculator_thread.start()
        self.accounts_updates(exchanges=exchanges)
        logger.info("Account loop started and in background")

    @staticmethod
    def accounts_updates(exchanges: list) -> None:
        """
        validates that all accounts have started
        """
        statuses_updated: int = 0
        while statuses_updated < len(exchanges):
            for exch in exchanges:
                with Cache() as store:
                    proc = store.get_process(tipe="account", key=exch.name)
                if proc:
                    if proc['message'] == 'Updated':
                        statuses_updated += 1
                time.sleep(0.5)

    @staticmethod
    def register_process(tipe, exch: ExchangeStruct, mesg: str) -> None:
        """
        Registers a new process in the cache.
        """
        with Cache() as store:
            store.new_process(tipe=tipe,
                              key=exch.name,
                              params={'ex_id': exch.ex_id},
                              message=mesg)
