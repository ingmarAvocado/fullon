"""
Order Managing System
"""
import threading
import time
import arrow
from typing import List, Dict, Optional
from libs.database_ohlcv import Database as DatabaseOhlcv
from libs import log
from libs.caches.orders_cache import Cache
from libs.exchange import Exchange
from libs.structs.order_struct import OrderStruct
from libs.structs.exchange_struct import ExchangeStruct


logger = log.fullon_logger(__name__)


class OrderMethods:
    """ class """

    started: bool = False

    def __init__(self) -> None:
        """
        Initialize OrderManager and set up required variables.
        """
        self.threads: List[threading.Thread] = []
        self.order_managers: Dict[str, threading.Thread] = {}
        self.manager_types = ['New', 'Open', 'Cancel']
        self.monitor_interval = 10  # Adjust this value as needed

    def __del__(self):
        #do we want to cancel all orders?
        pass

    @staticmethod
    def _get_exchange_cur(ex_id: str) -> Exchange:
        """
        Retrieves the exchange object based on the exchange ID.

        This method retrieves the ExchangeStruct object from the cache, using the provided
        exchange ID. It then uses this ExchangeStruct to initialize a new Exchange object
        which is returned.

        Args:
            ex_id (str): The ID of the exchange to retrieve.

        Returns:
            Exchange: An Exchange object corresponding to the given exchange ID.
        """
        with Cache() as store:
            exch: ExchangeStruct = store.get_exchange(ex_id=ex_id)
        exchange = Exchange(exchange=exch.cat_name, params=exch)
        return exchange

    def _update_user_account(self, ex_id: str) -> None:
        """
        updates user account details, position and available balances

        Args:
            ex_id (str): The ID of the exchange to retrieve.

        Returns:
            None
        """
        exch = self._get_exchange_cur(ex_id=ex_id)
        account = exch.get_balances()
        # If there are any account balances, update user account and positions
        if account:
            # Get the user's last positions for the current exchange
            with Cache() as store:
                store.upsert_user_account(ex_id=exch.ex_id, account=account)
                pos = exch.get_positions()
                store.upsert_positions(ex_id=exch.ex_id, positions=pos)

    def _can_place_order(self, order: OrderStruct) -> bool:
        """
        Process the incoming order.

        Args:
            order (OrderStruct): The order to process.

        Returns:
            bool: True if order can proceed, False otherwise.
        """
        exchange = self._get_exchange_cur(ex_id=order.ex_id)
        exchange.my_open_orders_socket()

        with Cache() as store:
            account = store.get_full_accounts(ex_id=order.ex_id)
            ticker = store.get_ticker(exchange=order.exchange, symbol=order.symbol)

        currency = exchange.quote_symbol(symbol=order.symbol)
        if not currency or not ticker:
            logger.info(f"no currency or ticker available {currency} {ticker}")
            return False

        return (self._has_user_account(account) and
                self._has_sufficient_funds(ticker, account, currency, order) and
                self._is_recent_ticker(ticker) and
                self._order_type_can_proceed(order, ticker[0]) and
                self._is_minimum_order(exchange, order))

    def _order_type_can_proceed(self, order: OrderStruct, ticker: float) -> bool:
        """
        Checks if the order type can proceed
        Args:
            order (OrderStruct): The order details
            ticker (float): The current price
        Returns:
            bool: If the order can proceed
        """
        with Cache() as store:
            position = store.get_position(symbol=order.symbol, ex_id=order.ex_id)

        is_stop_loss = order.order_type == 'stop-loss'
        is_take_profit = order.order_type == 'take-profit'

        if (is_stop_loss or is_take_profit) and position.volume == 0:
            logger.error("No position volume for stop-loss or take-profit order")
            return False
        elif is_stop_loss and ((order.side == "Sell" and order.price >= ticker) or (order.side == "Buy" and order.price <= ticker)):
            logger.error("Stop-loss order price not valid compared to ticker price")
            return False
        elif is_take_profit and ((order.side == "Sell" and order.price <= ticker) or (order.side == "Buy" and order.price >= ticker)):
            logger.error("Take-profit order price not valid compared to ticker price")
            return False

        return True

    def _has_user_account(self, account: dict) -> bool:
        """
        Check if a user account exists.

        Args:
            account (dict): A user account.

        Returns:
            bool: True if the account exists, False otherwise.
        """
        if not account:
            logger.info("Can't process order: No user account")
            return False
        return True

    def _has_sufficient_funds(self, ticker, account, currency, order: OrderStruct) -> bool:
        """
        Check if there are sufficient funds for the order.

        Args:
            ticker: The ticker for the order.
            account (dict): The user account.
            order (OrderStruct): The order to process.

        Returns:
            bool: True if there are sufficient funds, False otherwise.
        """
        if ticker[0] > 0:
            if (ticker[0]*order.volume) > float(account[currency]['free']):
                logger.info("Can't process order: Not enough funds")
                return False
        return True

    def _is_recent_ticker(self, ticker) -> bool:
        """
        Check if the ticker is recent.

        Args:
            ticker: The ticker to check.

        Returns:
            bool: True if the ticker is recent, False otherwise.
        """
        if arrow.utcnow().shift(seconds=-3600) > arrow.get(ticker[1]):
            logger.info("Can't trade with such old ticker")
            return False
        return True

    def _is_minimum_order(self, exchange, order) -> bool:
        """
        Check if the order volume is larger than the exchange minimum.

        Args:
            exchange: The exchange to check in.
            order (OrderStruct): The order to process.

        Returns:
            bool: True if the order is larger than the minimum, False otherwise.
        """
        if order.volume < exchange.minimum_order_cost(symbol=order.symbol):
            logger.info("Order bellow minimum levels")
            return False
        exchange.my_open_orders_socket()
        return True

    def _process_now_market(self, order: OrderStruct) -> OrderStruct:
        """
        Process the incoming order.

        Args:
            order (OrderStruct): The order to process.

        Returns:
            str: oid if it worked, empty string if it didn't
        """
        # Check if the order volume is larger than the exchange minimum.
        order = self._place_order(order=order)
        if 'error' not in order.status:
            count = 0
            while count < 20:
                with Cache() as store:
                    _order = store.get_order_status(
                        ex_id=order.ex_id, oid=order.order_id)
                try:
                    if _order.status == 'closed':
                        self._update_user_account(ex_id=order.ex_id)
                        return _order
                except AttributeError:
                    pass
                time.sleep(0.5)
                count += 1
        return order

    @staticmethod
    def _get_ticker_price(order) -> Optional[float]:
        """
        Get ticker price based on order command.

        Args:
            order: OrderStruct object

        Returns:
            float: Calculated price if ticker found, otherwise None.
        """
        with Cache() as store:
            ticker = store.get_ticker(exchange=order.exchange, symbol=order.symbol)
            if ticker:
                adjustment = ticker[0] * 0.00005
                price = ticker[0] - adjustment if order.side == "Buy" else ticker[0] + adjustment
                return price
        return None

    def _get_price(self, order: OrderStruct) -> Optional[float]:
        """
        Set order price based on order command.

        Args:
            order: OrderStruct object

        Returns:
            float: Calculated price based on order type, otherwise None.
        """
        price: Optional[float] = None
        match order.command:
            case "spread":
                price = self._get_ticker_price(order)
            case "twap":
                price = self._get_twap(order=order)
            case "vwap":
                price = self._get_vwap(order=order)
        return price

    def _process_now_limit(self, order: OrderStruct) -> OrderStruct:
        """
        Process the incoming order.

        Args:
            order: The order to process.

        Returns:
            str: oid if it worked, empty string if it didn't.
        """
        order.price = self._get_price(order)
        if not order.price:
            logger.error("Error can't place order: can't get price")
            order.status = "error"
            return order
        _order = self._place_order(order=order)
        if 'error' in order.status.lower():
            logger.error(f'Error: could not place order {order.order_id}')
            return _order
        # Wait until order is closed, update every minute
        return self._await_order_closure(_order)

    def _await_order_closure(self, order: OrderStruct) -> OrderStruct:
        """
        Wait until order is closed, check status every minute.

        Args:
            order: The order to process.
            oid: Order id.

        Returns:
            str: oid if it worked, error message if it didn't.
        """
        retry_count: int = 0
        wait_seconds: int = 60
        if order.command == "twap" or order.command == "vwap":
            compression, period = order.subcommand.split(":")
            match period:
                case "minutes":
                    wait_seconds = int(compression) * 60
                case "days":
                    wait_seconds = int(compression) * 60 * 60 * 24
        while True:
            try:
                with Cache() as store:
                    _order = store.get_order_status(ex_id=order.ex_id,
                                                    oid=order.order_id)
                if _order:
                    if _order.status == 'closed':
                        self._update_user_account(ex_id=order.ex_id)
                        return _order

                    if _order.status == 'canceled':
                        return self._process_now_limit(order=order)

                if retry_count > wait_seconds:  # Update every minute
                    order = self._cancel_and_replace_order(order)
                    if order.status == 'error':
                        logger.error("Error: Can't process _cancel_and_replace_order")
                        return order
                    retry_count = 0
                retry_count += 1
                time.sleep(1)
            except KeyboardInterrupt:
                self.cancel_order(order=order)

    def _cancel_and_replace_order(self, order: OrderStruct) -> OrderStruct:
        """
        Cancel the current order and replace it with a new one.

        Args:
            order: The order to process.
            oid: Order id.
        """
        logger.info(f"Canceling {order.order_id}")
        if self.cancel_order(order=order):
            logger.info(f"Order {order.order_id} canceled")
            order.price = self._get_price(order)
            if order.price is None:
                logger.info("Error: can't get price")
                order.status = 'error'
                return order
            order = self._place_order(order=order)
            if 'error' in order.status:
                logger.info('Error: could not place new order')
                return order
            logger.info(f"New order placed, new oid {order.order_id}")
            return order
        else:
            logger.info(f"Order {order.order_id} could not be canceled")
        order.status = 'error'
        return order

    def _place_order(self, order: OrderStruct) -> OrderStruct:
        """
        Creates an order on the specified exchange using the given order details.
        Args:
            exchange (Exchange): The exchange object to create the order on.
            order (OrderStruct): The order details, including the symbol, side, volume, and leverage.

        Returns:
            str: The order ID if the order was created successfully.

        Notes:
            This method fetches the ticker data from the cache to determine the order price.
            The order price is set to the ticker's first value minus 5.
        """
        if self._can_place_order(order=order):
            if order.order_type == 'stop-loss' or order.order_type == 'take-profit':
                order.reduce_only = True
            exchange = self._get_exchange_cur(ex_id=order.ex_id)
            try:
                decimals = exchange.get_pair_decimals(symbol=order.symbol)
                order.price = round(order.price, decimals)
            except (AttributeError, TypeError) as error:
                pass
            decimals = exchange.get_cost_decimals(symbol=order.symbol)
            order.volume = round(order.volume, decimals)
            _order = exchange.create_order(order=order)
            if 'error' in _order.status.lower():
                logger.info("Error, couldn't place order")
            return _order
        order.status = "error"
        return order

    def _get_twap(self, order: OrderStruct) -> Optional[float]:
        """
        Fetches the Time Weighted Average Price (TWAP) for a given order.

        Args:
            order (Any): An object representing the order. It should have `exchange` and `symbol` attributes.

        Returns:
            float: The TWAP for the given order.
        """
        compression, period = order.subcommand.split(":")
        with DatabaseOhlcv(exchange=order.exchange, symbol=order.symbol) as dbase:
            twap_data = dbase.twap(compression=int(compression), period=period)
        return twap_data[-1][1] if twap_data else None

    def _get_vwap(self, order: OrderStruct) -> Optional[float]:
        """
        Fetches the Volume Weighted Average Price (VWAP) for a given order.

        Args:
            order (Any): An object representing the order. It should have `exchange` and `symbol` attributes.

        Returns:
            float: The VWAP for the given order.
        """
        compression, period = order.subcommand.split(":")
        with DatabaseOhlcv(exchange=order.exchange, symbol=order.symbol) as dbase:
            vwap_data = dbase.vwap(compression=int(compression), period=period)
        return vwap_data[-1][1] if vwap_data else None

    def cancel_order(self, oid: str, ex_id: str) -> bool:
        """
        Cancel an order and verify its cancellation.
        The order status is checked repeatedly until the order is confirmed as 'canceled' or 'closed'.
        The method will attempt cancellation up to MAX_ATTEMPTS times before returning False.      
        Args:
            ex_id: The exchange ID.
            oid: The order ID.
        Returns:
            bool: True if the order was successfully canceled, False otherwise.
        """
        exchange = self._get_exchange_cur(ex_id=ex_id)
        exchange.my_open_orders_socket()
        exchange.cancel_order(oid=oid)
        time.sleep(1)
        attempts = 0
        while attempts < 50:  # 10 seconds but check 50 times
            with Cache() as store:
                _order = store.get_order_status(
                    ex_id=ex_id, oid=oid)
            if _order:
                if _order.status == 'canceled':
                    logger.info(f"Order {oid} was successfully canceled.")
                    return True
                if _order.status == 'closed':
                    logger.info(f"Order {oid} is closed and cannot be canceled.")
                    break
            else:
                logger.warning(f"Order {oid} not found.")
                return False
            time.sleep(0.2)
            attempts += 1
            if attempts == 25:
                exchange.cancel_order(oid=oid)
        logger.error(f"Failed to confirm the cancellation of order {oid}")
        return False

    def new_order(self, order: OrderStruct) -> Optional[OrderStruct]:
        """
        Processes new orders based on the type and command of the order.

        The function processes the order differently depending on the order command and type. 
        For 'spread' commands, the function processes market and limit orders differently. 
        For 'twap' and 'vwap' commands, the function processes limit orders.
        If the command doesn't match any of these cases, the function places the order as it is.

        Args:
            order (OrderStruct): The order to be processed.

        Returns:
            str: The Order ID (oid) of the processed order.
        """
        _order: Optional[OrderStruct] = None
        match order.command:
            case "spread":
                match order.order_type:
                    case 'market':
                        _order = self._process_now_market(order=order)
                    case 'limit':
                        _order = self._process_now_limit(order=order)
            case "twap":
                _order = self._process_now_limit(order=order)
            case "vwap":
                _order = self._process_now_limit(order=order)
            case _:
                _order = self._place_order(order=order)
        return _order

    def get_minimum_order(self, ex_id, symbol) -> float:
        """
        Check the minimum order size for a given symbol.

        Args:
            exchange: The exchange to check in.
            order (OrderStruct): The order to process.

        Returns:
            bool: True if the order is larger than the minimum, False otherwise.
        """
        res = 0
        exchange = self._get_exchange_cur(ex_id=ex_id)
        res = exchange.minimum_order_cost(symbol=symbol)
        del exchange
        return res
