"""
Class to make all exchange methods be called the same way within fullon
"""

from typing import Any, Dict, List, Optional, Union
import importlib.util
from libs import log
from libs.structs.order_struct import OrderStruct
from libs.structs.exchange_struct import ExchangeStruct
import json

logger = log.fullon_logger(__name__)


class ExchangeMethods():

    def __init__(self,
                 exchange: str,
                 params: Optional[ExchangeStruct] = None,
                 dry_run: bool = False):
        """Initializes an Exchange object.

        Args:
            exchange (str): The name of the exchange.
            params (Optional[Dict[str, Any]], optional): A dictionary of parameters for the exchange. Defaults to None.
            dry_run (bool, optional): Whether to run the exchange in dry-run mode. Defaults to False.
        """
        global exchange_ws_pool
        self.wbsrv = ""
        self.dry_run = dry_run
        self.exchange = exchange
        self.params = ExchangeStruct()
        if params:
            try:
                self.params = params
                self.uid = params.uid
                self.ex_id = params.ex_id
            except AttributeError:
                pass
        self.load_exchange_interface(exchange=exchange, params=params)

    def __del__(self):
        try:
            self.wbsrv.stop()
        except AttributeError:
            logger.error(f"Error closing exchange for uid {self.uid}")

    def load_exchange_interface(self,
                                exchange: str,
                                params: Optional[ExchangeStruct] = None,
                                prefix: str = "") -> None:
        """Loads the exchange interface.

        Args:
            exchange (str): The name of the exchange.
            params (Dict[str, Any]): A dictionary of parameters for the exchange.
            prefix (str, optional): The prefix for the exchange's interface path. Defaults to "".
        """
        file_path = prefix + "exchanges/" + exchange + "/interface.py"
        module_name = "interface"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            self.wbsrv = module.Interface(exchange, params, self.dry_run)
        except FileNotFoundError:
            if prefix == "":
                return self.load_exchange_interface(exchange=exchange,
                                                    params=params,
                                                    prefix="fullon/")
            logger.error(f"can't load exchange @{file_path}")
            raise ValueError("Cant find ways to load exchange")

    def get_markets(self) -> Any:
        """Retrieves the markets information.

        Returns:
            Any: The markets information.
        """
        return self.wbsrv.get_markets()

    def no_sleep(self) -> Any:
        """Retrieves the markets information.

        Returns:
            Any: The markets information.
        """
        return self.wbsrv.no_sleep

    def has_ticker(self) -> bool:
        """
        gets wether the exchange has a ticker service

        return
            Bool: True if it does, false if not
        """
        return self.wbsrv.has_ticker

    def get_full_account(self) -> Any:
        """Retrieves the full account information.

        Returns:
            Any: The full account information.
        """
        return self.wbsrv.get_full_account()

    def connect_websocket(self) -> Any:
        """Connects the websocket.

        Returns:
            Any: The result of connecting the websocket.
        """
        return self.wbsrv.connect_websocket()

    def stop_websockets(self) -> Any:
        """Stops the websocket connections.

        Returns:
            Any: The result of stopping the websocket connections.
        """
        try:
            return self.wbsrv.stop_websockets()
        except AttributeError as error:
            if "_socket" in str(error):
                logger.info(f"No websocket _socket for {self.exchange}")

    def socket_connected(self) -> bool:
        """Checks if the websocket is connected.

        Returns:
            bool: True if the websocket is connected, False otherwise.
        """
        return self.wbsrv.socket_connected()

    def start_ticker_socket(self, tickers: List[str]) -> Any:
        """Starts the ticker socket for the given tickers.

        Args:
            tickers (List[str]): A list of ticker symbols.

        Returns:
            Any: The result of starting the ticker socket.
        """
        return self.wbsrv.start_ticker_socket(tickers=tickers)

    def stop_ticker_socket(self) -> bool:
        """Stops the ticker socket.
        Returns:
            Any: The result of starting the ticker socket.
        """
        return self.wbsrv.stop_ticker_socket()

    def start_trade_socket(self, tickers: List[str]) -> bool:
        """
        Subscribes to user trades

        Args:
        tickers (list): A list of trading pairs to subscribe to.

        Returns:
        bool: True if the subscription was successfully created, False otherwise.
        """
        return self.wbsrv.start_trade_socket(tickers=tickers)

    def start_my_trades_socket(self) -> bool:
        """
        Subscribes to user trades

        Args:
        tickers (list): A list of trading pairs to subscribe to.

        Returns:
        bool: True if the subscription was successfully created, False otherwise.
        """
        return self.wbsrv.start_my_trades_socket()

    def fetch_trades(self, symbol: Optional[str], since: Optional[int], limit: Optional[int] = None,
                         params: Optional[Dict[str, Any]] = None) -> Any:
        """Fetches all trades.

        Args:
            symbol (Optional[str], optional): The trading symbol. Defaults to None.
            since (Optional[int], optional): The start timestamp for the trades. Defaults to None.
            limit (Optional[int], optional): The maximum number of trades to retrieve. Defaults to None.
            params (Optional[Dict[str, Any]], optional): Additional parameters. Defaults to None.

        Returns:
            Any: All trades.
        """
        return self.wbsrv.fetch_trades(symbol=symbol, since=since, limit=limit, params=params)

    def get_candles(self,
                    symbol: int,
                    frame: str,
                    since: str,
                    limit: str = "",
                    params: Optional[Dict[str, Any]] = None) -> Any:
        """Gets the candle data for a symbol.

        Args:
            symbol (str): The trading symbol.
            frame (str, optional): The time frame for the candle data. Defaults to "1m".
            since (str, optional): The start timestamp for the candle data. Defaults to "".
            limit (str, optional): The maximum number of candles to retrieve. Defaults to "".
            params (Optional[Dict[str, Any]], optional): Additional parameters. Defaults to None.

        Returns:
            Any: The candle data.
        """
        return self.wbsrv.get_candles(symbol, frame, since, limit, params=params)

    def fetch_orders(self, symbol: str) -> Any:
        """Gets the open orders.

        Args:
            symbol (Optional[str], optional): The trading symbol. Defaults to None.
            since (Optional[int], optional): The start timestamp for the orders. Defaults to None.

        Returns:
            Any: The open orders.
        """
        return self.wbsrv.fetch_orders(symbol=symbol)

    def get_tickers(self) -> Any:
        """Gets all ticker symbols.

        Returns:
            Any: All ticker symbols.
        """
        return self.wbsrv.get_tickers()

    def has_ohlcv(self) -> Any:
        """Gets all ticker symbols.

        Returns:
            Any: All ticker symbols.
        """
        return self.wbsrv.ohlcv

    def fetch_my_trades(self, **kwargs) -> Any:
        """Fetches the user's trades.

        Args:
            symbol (Optional[str], optional): The trading symbol. Defaults to None.
            since (Optional[int], optional): The start timestamp for the trades. Defaults to None.
            limit (Optional[int], optional): The maximum number of trades to retrieve. Defaults to None.
            params (Optional[Dict[str, Any]], optional): Additional parameters. Defaults to None.

        Returns:
            Any: The user's trades.
        """
        return self.wbsrv.fetch_my_trades(**kwargs)

    def get_order(self, oid: str, symbol: str) -> Any:
        """Gets an order by ID.

        Args:
            oid (str): The order ID.
            symbol (str): The trading symbol.

        Returns:
            Any: The order information.
        """
        return self.wbsrv.get_order(oid=oid, symbol=symbol)

    def cancel_all_orders(self, symbol: str) -> Any:
        """Cancels all orders for a symbol.

        Args:
            symbol (str): The trading symbol.

        Returns:
            Any: The result of canceling all orders.
        """
        return self.wbsrv.cancel_all_orders(symbol)

    def cancel_order(self, oid: str) -> Any:
        """Cancels an order by ID.

        Args:
            oid (str): The order ID.
            symbol (str): The trading symbol.

        Returns:
            Any: The result of canceling the order.
        """
        return self.wbsrv.cancel_order(str(oid))

    def create_stop_limit_order(self, symbol: str, side: str, amount: float, price: float, plimit: float,
                                params: Optional[Dict[str, Any]] = None) -> Any:
        """Creates a stop limit order.

        Args:
            symbol (str): The trading symbol.
            side (str): The order side (buy or sell).
            amount (float): The order amount.
            price (float): The order price.
            plimit (float): The price limit.
            params (Optional[Dict[str, Any]], optional): Additional parameters. Defaults to None.

        Returns:
            Any: The result of creating the stop limit order.
        """
        return self.wbsrv.create_stop_limit_order(symbol=symbol, side=side, volume=amount, price=price, plimit=plimit, params=params)

    def create_stop_order(self, symbol: str, side: str, amount: float, price: float,
                          params: Optional[Dict[str, Any]] = None) -> Any:
        """Creates a stop order.

        Args:
            symbol (str): The trading symbol.
            side (str): The order side (buy or sell).
            amount (float): The order amount.
            price (float): The order price.
            params (Optional[Dict[str, Any]], optional): Additional parameters. Defaults to None.

        Returns:
            Any: The result of creating the stop order.
        """
        return self.wbsrv.create_stop_order(symbol=symbol, side=side, volume=amount, price=price, params=params)

    def create_order(self, order: OrderStruct) -> Any:
        """Creates an order.

        Args:
            order: OrderStruct with the contents of the order.

        Returns:
            Any: The result of creating the order.
        """
        return self.wbsrv.create_order(order=order)

    def my_open_orders_socket(self) -> None:
        """
        Subscribes to user's trades.

        Returns:
        None
        """
        return self.wbsrv.my_open_orders_socket()

    def minimum_order_cost(self, symbol: str) -> float:
        """Gets the minimum order cost for a symbol.

        Args:
            symbol (str): The trading symbol.

        Returns:
            Any: The minimum order cost.
        """
        return self.wbsrv.minimum_order_cost(symbol=symbol)

    def get_balances(self) -> Dict[str, Any]:
        """Gets the total user account information.

        Returns:
            Dict[str, Any]: The total user account information.
        """
        if self.exchange != "simulator":
            return self.wbsrv.get_balances()
        return {"total": self.wbsrv.funds}

    def get_positions(self) -> Dict[str, Any]:
        """Gets the total user account .

        Returns:
            Dict[str, Any]: The total user account information.
        """
        if self.exchange != "simulator":
            return self.wbsrv.get_positions()
        return {"positions": self.wbsrv.funds}

    def set_leverage(self, symbol: str, leverage: int) -> None:
        """Sets the leverage for a symbol.

        Args:
            symbol (str): The trading symbol.
            leverage (int): The leverage value.
        """
        self.wbsrv.set_leverage(symbol=symbol, leverage=leverage)

    def get_sleep(self) -> float:
        """Gets the currency information for a symbol.

        Returns:
            Any: Latest sleep time
        """
        return self.wbsrv.get_sleep()

    def quote_symbol(self, symbol: str) -> float:
        """
        Returns the quote currency for a given symbol.
        :param symbol: The trading symbol (e.g. 'BTC/USD', 'ETH/EUR')to get the quote currency.

        :return: The minimum cost required to place an order for the given symbol.
        """
        return self.wbsrv.quote_symbol(symbol=symbol)

    def get_cost_decimals(self, symbol: str) -> float:
        """
        Returns the decimals for a  currency for a given symbol.
        :param symbol: The trading symbol (e.g. 'BTC/USD', 'ETH/EUR')to get the quote currency.

        :return: The minimum cost required to place an order for the given symbol.
        """
        return self.wbsrv.get_cost_decimals(symbol=symbol)

    def get_pair_decimals(self, symbol: str) -> float:
        """
        Returns the decimals for a  currency for a given symbol.
        :param symbol: The trading symbol (e.g. 'BTC/USD', 'ETH/EUR')to get the quote currency.

        :return: The minimum cost required to place an order for the given symbol.
        """
        return self.wbsrv.get_pair_decimals(symbol=symbol)