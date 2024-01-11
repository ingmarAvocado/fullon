from inspect import Attribute
import sys
import time
from libs import log, settings
from libs.caches import orders_cache as cache
from libs.structs.trade_struct import TradeStruct
from libs.structs.order_struct import OrderStruct
from exchanges.ccxt.interface import Interface as Ccxt_Interface
import arrow
from typing import Dict, Any, Union, List, Optional
from exchanges.kraken import websockets
from collections import defaultdict
import uuid
from collections import Counter
import threading

logger = log.fullon_logger(__name__)


# This the interface for  kraken

class Interface(Ccxt_Interface):

    _socket: Optional[websockets.WebSocket]
    _ws_token = None
    _ws_subscriptions: Dict = {}
    _markets: Dict = {}
    _token_refresh_thread: Optional[threading.Thread] = None
    currencies: dict = {}
    pairs: dict = {}

    def __init__(self, exchange, params, dry_run=False):
        super().__init__(exchange, params)
        self.ws.verbose = False
        self.short = True
        self.ohlcv_needs_trades = True
        self.delete_trades = False
        self._sleep = float(settings.KRAKEN_TIMEOUT)
        if not self.ws.markets:
            self.ws.load_markets()
        if not self.currencies:
            self.set_currencies()
        if not self.pairs:
            self.set_pairs()
        self._markets = self._markets_dict()
        self._ws_pre_check()
        self.start_token_refresh_thread()
        self.no_sleep.extend(['start_ticker_socket',
                              'start_trade_socket',
                              'start_my_trades_socket',
                              'my_open_orders_socket',
                              'create_order',
                              'cancel_order'])

    def __del__(self) -> None:
        self.stop()

    def stop(self):
        """
        """
        try:
            if self._socket:
                logger.info(f"Closing Kraken Websocket: {self.params.ex_id}")
                self._socket.stop()
                self._socket = None
        except AttributeError:
            pass
        if self._token_refresh_thread is not None:
            try:
                self._token_refresh_thread.join(timeout=1)
            except AttributeError:
                pass
        super().stop()

    def _ws_pre_check(self):
        """
        Checks if the WebSocket connection to the account service
        is established and if an authentication token has been generated.
        If the WebSocket connection is not established, it will be initiated.
        If an authentication token is not available, it will be generated.
        Returns:
        None.
        """
        try:
            if not self._socket.client:
                logger.warning(f"Kraken WebSocket is not connected {self.params.ex_id}")
                # first make sure we turn off the old one
                self._socket.stop()
                del self._socket
                self._socket: Optional[websockets.WebSocket] = None
                # now connect again
                self.connect_websocket()
                self._reconnect_ws_subscriptions()
                return self._ws_pre_check()
        except (TypeError, AttributeError) as error:
            self._socket = None
            time.sleep(1)
            logger.info("No previous Kraken websocket found")
            self.connect_websocket()
            return self._ws_pre_check()
        if not self._ws_token:
            self._generate_auth_token()

    def connect_websocket(self) -> None:
        """
        Establishes a connection to the WebSocket and sets the `websocket_connected` attribute to True.

        Returns:
        bool: True if the WebSocket connection was successfully established, False otherwise.
        """
        if not self._socket:
            self._socket = websockets.WebSocket(
                markets=self._markets, ex_id=self.params.ex_id)
            if self._socket.started is False:
                self._socket = None
                return self.connect_websocket()
            logger.info(f"Kraken WebSocket initiated ex_id {self.params.ex_id}")
            self._ws_subscriptions['ticker'] = []
            self._ws_subscriptions['trades'] = []
            self._ws_subscriptions['ownTrades'] = False
            self._ws_subscriptions['openOrders'] = False

    def refresh_token(self):
        """
        Refreshes the WebSocket token by re-authenticating with the Kraken API.
        """
        try:
            with cache.Cache() as store:
                error = store.pop_ws_error(ex_id=self.params.ex_id)
            if error:
                logger.warning(f"Kraken WebSocket is not connected {self.params.ex_id}")
                self._ws_token = False
                self._generate_auth_token()
                self._socket.stop()
                del self._socket
                self._socket: Optional[websockets.WebSocket] = None
                # now connect again
                self.connect_websocket()
                self._reconnect_ws_subscriptions()
                return self._ws_pre_check()
        except (TypeError, AttributeError) as error:
            self._socket = None
            time.sleep(1)
            logger.info("No previous Kraken websocket found")
            self.connect_websocket()
            return self._ws_pre_check()

    def start_token_refresh_thread(self, interval=60):
        """
        Starts a background thread that periodically refreshes the WebSocket token.

        Args:
            interval: Time in seconds between each token refresh (default: 3600 seconds).
        """

        def run():
            while True:
                try:
                    self.refresh_token()
                except:
                    pass
                time.sleep(interval)

        self._token_refresh_thread = threading.Thread(target=run)
        self._token_refresh_thread.daemon = True  # Daemonize thread
        self._token_refresh_thread.start()
        logger.info("Token refresh thread started.")

    def start_ticker_socket(self, tickers: list) -> bool:
        """
        Subscribes to ticker updates

        Args:
        tickers (list): A list of trading pairs to subscribe to.

        Returns:
        bool: True if the subscription was successfully created, False otherwise.
        """
        self._ws_pre_check()
        subs = Counter(self._socket.subscriptions)['ticker']
        new_total = subs + len(tickers)
        if self._socket.subscribe_public(subscription={'name': 'ticker'},
                                         pair=tickers,
                                         callback=self._socket.on_ticker):
            count = 0
            while Counter(self._socket.subscriptions)['ticker'] < new_total and count <= 20:
                time.sleep(0.5)
                count += 1
            if count > 20:
                return False
            self._ws_subscriptions['ticker'].extend(tickers)
            return True
        return False

    def stop_ticker_socket(self) -> None:
        """
        Subscribes to ticker updates

        Args:
        tickers (list): A list of trading pairs to subscribe to.

        Returns:
        bool: True if the subscription was successfully closed, False otherwise.
        """
        self._ws_pre_check()
        self._socket.unsubscribe_tickers()

    def start_trade_socket(self, tickers: list) -> bool:
        """
        Subscribes to ticker updates

        Args:
        tickers (list): A list of trading pairs to subscribe to.

        Returns:
        bool: True if the subscription was successfully created, False otherwise.
        """
        self._ws_pre_check()
        if self._socket.subscribe_public(
                subscription={'name': 'trade'},
                pair=tickers,
                callback=self._socket.on_trade):
            count = 0
            while 'trade' not in self._socket.subscriptions or count > 20:
                time.sleep(0.5)
                count += 1
            if count > 20:
                return False
            self._ws_subscriptions['trades'].extend(tickers)
            return True
        return True

    def start_my_trades_socket(self) -> bool:
        """
        Subscribes to user's trades.

        Returns:
        bool: True if the subscription was successfully created, False otherwise.
        """
        try:
            if 'ownTrades' in self._socket.subscriptions:
                return True
        except AttributeError:
            pass
        self._ws_pre_check()
        if self._socket.subscribe_private(
                subscription={'name': 'ownTrades', 'token': self._ws_token},
                callback=self._socket.on_my_trade):
            count = 0
            while 'ownTrades' not in self._socket.subscriptions or count > 20:
                time.sleep(0.5)
                count += 1
            if count > 20:
                return False
            self._ws_subscriptions['ownTrades'] = True
            return True
        return False

    def my_open_orders_socket(self) -> bool:
        """
        Subscribes to user's trades.

        Returns:
        None
        """
        try:
            if 'openOrders' in self._socket.subscriptions:
                return True
        except AttributeError:
            pass
        self._ws_pre_check()
        if self._socket.subscribe_private(
                subscription={'name': 'openOrders', 'token': self._ws_token},
                callback=self._socket.on_my_open_orders):
            count = 0
            while 'openOrders' not in self._socket.subscriptions or count > 20:
                time.sleep(0.5)
                count += 1
            if count > 20:
                self._ws_subscriptions['openOrders'] = True
                return False
            return True
        return False

    def create_order(self, order: OrderStruct) -> OrderStruct:
        """
        creates a user trade.

        Returns:
        Str:  oid if order was created successfully
        """
        self._ws_pre_check()
        # Construct the message to add an order
        local_oid = str(uuid.uuid4())
        # Construct the message to add an order
        if float(order.leverage) < 2:
            order.leverage = 2
        order_message = {
            "event": "addOrder",
            "ordertype": order.order_type,
            "pair": order.symbol,
            "token": self._ws_token,
            "type": order.side.lower(),
            "volume": str(order.volume),
            "leverage": str(int(float(order.leverage))),
            "reduce_only": order.reduce_only
        }

        #if order is not market, we have tu put price. now for the leverage
        if order.price:
            order_message['price'] = order.price

        count = 0
        oid = ''
        if self._socket.request(
                order_message, callback=self._socket.on_my_order, local_oid=local_oid):
            while count <= 10:
                try:
                    with cache.Cache() as store:
                        oid = store.pop_open_order(local_oid=local_oid)
                    if oid == 'error':
                        order.status = "error"
                        logger.error(f"got an error processing {order_message}")
                        return order
                    logger.info("Kraken Order placed: %s", oid)
                    order.order_id = oid
                    order.ex_order_id = oid
                    return order
                except TimeoutError:
                    pass
                time.sleep(1)
                count = count+1
                if count > 10:
                    logger.error("Kraken: Waiting too long to receive order response")
        order.order_id = oid
        return order

    def cancel_order(self, oid: str) -> bool:
        """
        Cancels an open order by ID.

        Args:
            order_id (str): The ID of the order to cancel.

        Returns:
            None
        """
        self._ws_pre_check()
        local_oid = str(uuid.uuid4())
        # Construct the message to cancel an order
        cancel_message = {
              "event": "cancelOrder",
              "token": self._ws_token,
              "txid": [oid],
        }
        if self._socket.request(
                cancel_message, callback=self._socket.cancel_order, local_oid=local_oid):
            status = False
            while True:
                try:
                    with cache.Cache() as store:
                        status = store.pop_open_order(local_oid=local_oid)
                except TimeoutError:
                    pass
                if status == 'ok':
                    return True
                else:
                    return False
        return False

    def socket_connected(self) -> bool:
        """
        Checks if the WebSocket connection is still active.

        Returns:
        bool: True if the WebSocket connection is active, False otherwise.
        """
        return self._socket.is_connected()

    def _generate_auth_token(self) -> None:
        """
        Generates an authentication token for Kraken WebSocket API private channels.
        assigns to self._ws_token

        Returns:
            None
        """
        try:
            token: Dict[str, Any] = self.execute_ws("private_post_getwebsocketstoken")
            self._ws_token = token['result']['token']
        except TypeError:
            logger.error("Kraken: Exchange rejected keys")

    def _reconnect_ws_subscriptions(self):
        """
        Reconnects all WebSocket subscriptions by iterating through the
        _ws_subscriptions list and calling the appropriate methods for each
        subscription type. This function is useful when subscriptions are
        unexpectedly disconnected or need to be restarted due to an error.

        This method will:
        - Reconnect to ticker updates if there are tickers in the subscription.
        - Reconnect to trade updates if there are trades in the subscription.
        - Reconnect to user's trades if the ownTrades flag is True.
        - Reconnect to user's open orders if the openOrders flag is True.
        """
        subs = self._ws_subscriptions.copy()
        self._ws_subscriptions['ticker'] = []
        self._ws_subscriptions['trades'] = []
        self._ws_subscriptions['ownTrades'] = False
        self._ws_subscriptions['openOrders'] = False
        for sub in subs:
            if sub['tickers']:
                self.start_ticker_socket(tickers=sub['tickers'])
            if sub['trades']:
                self.start_trade_socket(tickers=sub['trades'])
            if sub['ownTrades']:
                self.start_my_trades_socket()
            if sub['openOrders']:
                self.my_open_orders_socket()

    def fetch_trades(self,
                     symbol: str,
                     since: Union[int, float, str],
                     limit: Union[int, None] = None,
                     params: Dict = {}) -> List[TradeStruct]:
        """
        Fetches all trades for a given trading symbol.

        Args:
        symbol (str): The trading symbol to fetch trades for.
        since (int, float, str): The timestamp to start fetching trades from.
        limit (int, optional): The maximum number of trades to fetch. Defaults to None.
        params (dict, optional): Additional parameters to pass to the exchange API. Defaults to {}.

        Returns:
        list: A list of trade dictionaries, each containing trade information such as price, volume, timestamp, and more.
        """
        if isinstance(since, str):
            since = arrow.get(since).timestamp()
        since = since+1
        symbol = self.replace_symbol(symbol=symbol)
        if len(str(since)) == 10:
            since = int(str(since) + "000000000")
        elif len(str(since)) == 15:
            since = int(str(since).replace('.', '') + "00000")
        elif len(str(since)) == 17:
            since = int(str(since).replace('.', '') + "000")
        kraken_params = {'pair': symbol, 'since': since}
        trades = self.execute_ws("public_get_trades", [kraken_params])
        if not trades:
            return []
        else:
            trades = trades['result'][symbol]
        trade_structs = []
        for t in trades:
            trade = {
                'price': t[0],
                'volume': t[1],
                'timestamp': t[2],
                'time': arrow.get(float(t[2])).naive,
                'side': t[3],
                'order_type': t[4],
                'ex_trade_id': t[5]}
            trade_structs.append(TradeStruct.from_dict(trade))
        return trade_structs

    def replace_symbol(self, symbol: str) -> Optional[str]:
        try:
            return self.ws.markets[symbol]['id']
        except KeyError as error:
            logger.warning(str(error))

    def replace_symbols(self, symbols: list) -> list:
        ret_list = []
        for symbol in symbols:
            ret_list.append(self.ws.markets[symbol]['id'])
        return ret_list

    def get_asset_pairs(self):
        pairs = super().get_asset_pairs()
        pairs = self.replace_symbols(symbols=pairs)
        return pairs

    def get_tickers(self, sleep: int = 1, pairs: List = []) -> Dict[str, Dict[str, Union[str, float]]]:
        """Get all tickers information.

        Args:
            sleep (int, optional): Time to wait before making the request. Defaults to 1.

        Returns:
            Dict[str, Dict[str, Union[str, float]]]: A dictionary of tickers information.
        """
        if not pairs:
            pairs = self.get_asset_pairs()
        params = {
            'pair': ','.join(pairs),
        }
        markets = self.execute_ws("public_get_ticker", [params, ])
        if not markets:
            return {}
        tickers = markets['result']
        markets_dict = {
            self.ws.markets_by_id[id][0]['symbol']:
            self.ws.parse_ticker(tickers[id], self.ws.markets_by_id[id][0])
            for id in tickers.keys()
        }
        return {
            market['symbol']: {
                'symbol': market['symbol'],
                'datetime': arrow.get(market['timestamp']).format(),
                'openPrice': market['open'],
                'highPrice': market['high'],
                'lowPrice': market['low'],
                'close': market['close'],
                'volume': market['baseVolume']
            }
            for market in markets_dict.values()
        }

    def _my_trades_list(self, trades) -> List[TradeStruct]:
        margin_trades = []
        for key, trade in trades.items():
            if float(trade['leverage']) > 1:
                trade_data = {
                    'ex_trade_id': key,
                    'ex_order_id': trade['ordertxid'],
                    'uid': self.params.uid,
                    'ex_id': self.params.ex_id,  # Use the exchange id
                    'symbol': self._markets[trade['pair']],
                    'order_type': trade['ordertype'],
                    'side': trade['type'],
                    'volume': float(trade['vol']),
                    'price': float(trade['price']),
                    'cost': float(trade['cost']),
                    'fee': float(trade['fee']),
                    'leverage': float(trade['leverage']),
                    'time': arrow.get(float(trade['time'])).format("YYYY-MM-DD HH:mm:ss.SSS"),
                    'timestamp': trade['time']
                }
                margin_trades.append(TradeStruct.from_dict(trade_data))
        margin_trades = margin_trades[::-1]
        return margin_trades

    def fetch_my_trades(self,
                        symbol: Optional[str] = None,
                        since: Optional[Union[int, float]] = None,
                        last_id: Optional[Union[int, float]] = None,
                        limit: Optional[int] = None,
                        params: Optional[Dict[str, Any]] = None) -> List[TradeStruct]:
        """Fetches the user's trades.

        Args:
            symbol (Optional[str], optional): The trading symbol. Defaults to None.
            since (Optional[int], optional): The start timestamp for the trades. Defaults to None.
            limit (Optional[int], optional): The maximum number of trades to retrieve. Defaults to None.
            params (Optional[Dict[str, Any]], optional): Additional parameters. Defaults to None.

        Returns:
            Any: The user's trades.
        """
        # i need to get a trade history and get how many trades
        kraken_params = {}
        if not last_id:
            if since:
                start = since
                kraken_params = {'start': start}
        else:
            start = last_id
            kraken_params = {'start': start}
        trades = self.execute_ws("private_post_tradeshistory", [kraken_params])
        ret_trades = []
        if not trades:
            return ret_trades
        count = int(trades['result']['count'])
        if count > 50:
            count = count - 50
        else:
            ret_trades.extend(self._my_trades_list(trades['result']['trades']))
            return ret_trades
        kraken_params['ofs'] = count
        time.sleep(self._sleep)
        trades = self.execute_ws("private_post_tradeshistory", [kraken_params])
        if not trades:
            return ret_trades
        ret_trades.extend(self._my_trades_list(trades['result']['trades']))
        return ret_trades

    def get_balances(self, count: int = 0) -> Dict:
        """
        Retrieve the user's account information with balances for
        each cryptocurrency and calculate the total balance in terms of BTC.

        :param count: Number of retries for fetching user
                      account information, default is 0.
        :return: A list containing the user's account information or
                 None if balances could not be retrieved.
        """
        tbalance = self.execute_ws("private_post_tradebalance")['result']
        balances = {}
        for balance in settings.COMMON_TICKERS.split(','):
            balances[balance] = {'free': float(tbalance['mf']),
                                 'used': round(float(tbalance['m'])-float(tbalance['n']),2),
                                 'total': float(tbalance['eb'])}
        return balances

    def get_positions(self) -> Dict:
        """
        Get open positions and consolidate them by pair, calculating the average price.

        :return: A dictionary containing consolidated positions with the average price, total volume, and total fee.
        """
        # Initialize a dictionary to store consolidated positions.
        cons_positions = defaultdict(lambda: {'cost': 0.0, 'volume': 0.0, 'fee': 0.0})

        # Execute the command to get the open positions.
        positions = self.execute_ws("private_post_openpositions")

        # Check if there are no errors in retrieving positions.
        if positions['error'] == []:
            # Iterate over each position.
            for key, value in positions['result'].items():
                # Get the pair for this position.
                pair = self.pairs[value['pair']]

                # Update the consolidated position dictionary with the cost, volume, and fee of the current position.
                cons_positions[pair]['cost'] += float(value['cost'])
                cons_positions[pair]['volume'] = abs(cons_positions[pair]['volume']) + float(value['vol'])
                cons_positions[pair]['fee'] += float(value['fee'])

                # Calculate the average price for the current pair.
                cons_positions[pair]['price'] = cons_positions[pair]['cost'] / cons_positions[pair]['volume']

                # If the position is a sell, then we negate the volume.
                if "sell" in value['type'].lower():
                    cons_positions[pair]['volume'] *= -1

        # Return the consolidated positions dictionary.
        return dict(cons_positions)

    def get_usd_value(self, symbol: str, balance: float, tickers: Dict[str, Dict[str, float]]) -> float:
        """
        Calculates the USD value of a balance in a given currency.

        :param symbol: The currency symbol.
        :param balance: The balance in the specified currency.
        :param tickers: A dictionary of ticker information for currency pairs.
        :return: The USD value of the balance.
        """
        if 'USD' in symbol:
            return balance

        pair = f'{symbol}/USD'
        if pair in tickers:
            return balance * tickers[pair]['close']
        return 0

    def set_pairs(self) -> None:
        """
        Retrieves pairs information and populates self.pairs with
        a mapping between standard currency symbols and Kraken-specific symbols.
        """
        for key, value in self.ws.markets.items():
            self.pairs[value['id']] = key

    def set_currencies(self) -> None:
        """
        Retrieves currency information and populates self.currencies with
        a mapping between standard currency symbols and Kraken-specific symbols.
        """
        currencies = self.execute_ws("fetch_currencies")
        self.currencies['a'] = {}
        self.currencies['b'] = {}
        for key, values in currencies.items():
            self.currencies['a'][key] = values['id']
            self.currencies['b'][values['id']] = key

    def match_currencies(self, balances: Dict[str, Dict]) -> Dict[str, str]:
        """
        Replaces Kraken-specific currency symbols with standard ones in the balance dictionary.

        :param balances: The balance dictionary with Kraken-specific currency symbols.
        :return: A balance dictionary with standard currency symbols.
        """
        matched_balances = {}
        for key, value in balances['result'].items():
            # Check if the key is present in self.currencies['b'], and use the standard symbol if it exists.
            # Otherwise, use the original key.
            standard_key = self.currencies['b'].get(key, key)
            matched_balances[standard_key] = value
        return matched_balances

    def _markets_dict(self) -> Dict:
        """
        Receives data markets from ws and creates a dictionary to match the
        ws_symbol name for symbol with rest_symbol for Kraken.

        Returns:
            Markets Dict
        """
        markets = {}
        for key, value in self.ws.markets.items():
            markets[value['info']['altname']] = key
            markets[value['info']['wsname']] = key
            markets[value['id']] = key
        return markets
