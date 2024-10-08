import json
from typing import Any, Dict, List, Callable, Optional
from kraken_wsclient_py import kraken_wsclient_py
import arrow
from libs import log
from libs.caches.trades_cache import Cache
from libs.structs.trade_struct import TradeStruct
from libs.structs.exchange_struct import ExchangeStruct
from twisted.internet import reactor
from twisted.internet import error as twisted_error
import threading
import time
from autobahn.exception import Disconnected
from functools import partial


logger = log.fullon_logger(__name__)


class WebSocket:
    """
    KrakenWebSocket class to interact with the Kraken WebSocket API.
    """

    def __init__(self, markets: Dict, ex_id: str) -> None:
        """
        Initialize the KrakenWebSocket class.

        Args:
            markets (Dict): A dictionary of market details.
            ex_id (str): The exchange ID.
        """
        self._markets: Dict = markets
        self.ex_id: str = ex_id
        self.client: Optional[kraken_wsclient_py.WssClient] = None
        self.subscriptions: List = []
        self.started: bool = False
        self.ticker_factory_keys: list = []
        self.trade_factory_keys: list = []
        self.subscribed_tickers: list = []
        self.subscribed_trades: list = []
        self.cache_trade_reply = 0
        self.cache_ticker_reply = 0

    def __del__(self):
        self.clean_up()

    def start(self, retries=5) -> None:
        """
        starts  connections
        """
        if self.started or retries == 0:
            logger.info("Cant start a started socket.")
            return
        self.client = kraken_wsclient_py.WssClient()
        self.client.start()
        count = 0
        while not self.is_connected() and count < 5:
            time.sleep(1)
            count += 1
        if self.is_connected():
            self.started = True
            return
        self.started = False
        return self.start(retries=retries-1)

    def stop(self) -> None:
        """
        Stop the KrakenWebSocket instance.

        Returns:
            None
        """
        if self.client:
            try:
                self.client.close()  # Close the WebSocket connection
            except AttributeError as error:
                pass
            self.started = False
            self.client = None

    def clean_up(self):
        """
        shots down twisted, necessary for proper shutdown.
        """
        try:
            logger.warning("WebSocket for kraken has been closed, you will need to start a new one on different process")
            reactor.stop()
        except twisted_error.ReactorNotRunning:
            pass

    def is_connected(self) -> bool:
        """
        Check if the WebSocket connection is established and receiving messages.

        Returns:
            bool: True if connected and receiving messages, False otherwise.
        """
        if not self.client:
            return False

        connected_event = threading.Event()
        connected = False

        def ping_response(message):
            nonlocal connected
            if 'connectionID' not in message:
                if message['event'] == "pong":
                    connected = True
                else:
                    connected = False
                connected_event.set()

        message = {
            "event": "ping",
        }
        try:
            if self.request(message, callback=ping_response):
                connected_event.wait(timeout=3)  # Wait for the connected_event to be set
                return connected
        except Disconnected:
            logger.error("Attempt to send on a closed protocol")
        except Exception as e:
            logger.error(str(e))
            raise
        return False

    def request(self, request: Dict[str, str], callback: Callable, **kwargs)-> bool:
        """
        Send a request to the Kraken WebSocket API, such as placing an order.

        Args:
            request (Dict[str, str]): The request details, including the API token.
            callback (Callable): The callback function to handle the response.

        Returns:
            None
        """
        if not self.client:
            return False

        id_ = request['event']
        payload = json.dumps(request, ensure_ascii=False).encode('utf8')
        wrapped_callback = partial(callback, **kwargs)
        try:
            if id_ not in self.client._conns:
                # Create a new WebSocket connection for one-time messages if it doesn't exist
                connected_event = threading.Event()

                def ping_reply(message, **kwargs):
                    connected_event.set()
                    pass
                pingload = json.dumps({'event': 'ping'}, ensure_ascii=False).encode('utf8')
                self.client._start_socket(id_, pingload, ping_reply, private=True)
                connected_event.wait(timeout=3)
                return reactor.callLater(0, self.request, request=request, callback=callback, **kwargs)
            else:
                # Update the callback and reuse the existing WebSocket connection for one-time messages
                self.client.factories[id_].callback = wrapped_callback
                self.client.factories[id_].protocol_instance.sendMessage(payload, isBinary=False)
        except twisted_error.ConnectionDone as error:
            logger.error(f"Unexpected twisted error occurred: {error}")
            return False
        except AttributeError as error:
            logger.info(f"websocket client not created yet")
            return False
        return True

    def subscribe_public(self, subscription: Dict[str, str], pair: List[str], callback: Callable) -> bool:
        """
        Subscribe to public data channels.

        Args:
            subscription (Dict[str, str]): Subscription details.
            pair (List[str]): List of currency pairs.
            callback (Callable): The callback function to handle received data.

        Returns:
            bool: True if subscription was successful, False otherwise.
        """
        try:
            self.client.subscribe_public(subscription=subscription, pair=pair, callback=callback)
            if 'ticker' in subscription['name']:
                key, _ = list(self.client.factories.items())[-1]
                self.ticker_factory_keys.append(key)
            elif 'trade' in subscription['name']:
                key,  _ = list(self.client.factories.items())[-1]
                self.trade_factory_keys.append(key)
            logger.info("Subscribing to public channel")
            return True
        except (twisted_error.ConnectionDone, twisted_error.ConnectionLost, Exception) as err:
            logger.error(f"Failed to subscribe to public channel: {err}")
            return False

    def unsubscribe_tickers(self) -> bool:
        """
        unSubscribe to public data channels.

        Args:
            subscription (Dict[str, str]): Subscription details.
            callback (Callable): The callback function to handle received data.

        Returns:
            None
        """
        if not self.ticker_factory_keys:
            logger.warning("Attempting to stop a ticker, but ticker had not been started")
            return False

        message = {
              "event": "unsubscribe",
              "pair": self.subscribed_tickers,
              "subscription": {
                "name": "ticker"
              }
            }
        payload = json.dumps(message, ensure_ascii=False).encode('utf8')
        try:
            for key in self.ticker_factory_keys:
                self.client.factories[key].protocol_instance.sendMessage(payload, isBinary=False)
                self.subscribed_tickers.clear()
                self.client.stop_socket(key)
                logger.info(f"Unsubscribed from ticker socket {key}")
        except Disconnected:
            logger.warning("attempting to stop a ticker socket, when apparently there is none connected")
            self.ticker_factory_keys = []
            return False
        self.ticker_factory_keys = []
        return True

    def unsubscribe_trades(self) -> bool:
        """
        Unsubscribe from public trade data channels.

        Returns:
            bool: True if unsubscription was successful, False otherwise.
        """
        if not self.trade_factory_keys:
            logger.warning("Attempting to stop a trade websocket, but trade had not been started")
            return False

        message = {
              "event": "unsubscribe",
              "pair": [],
              "subscription": {
                "name": "trade"
              }
            }
        payload = json.dumps(message, ensure_ascii=False).encode('utf8')
        try:
            for key in self.trade_factory_keys:
                self.client.factories[key].protocol_instance.sendMessage(payload, isBinary=False)
                self.subscribed_trades.clear()
                self.client.stop_socket(key)
                logger.warning(f"Disconnected from trade socket {key}")
        except Disconnected:
            logger.warning("attempting to stop a trade socket, when apparently there is none connected")
        logger.info("Unsubscribed from trade socket")
        self.trade_factory_keys = []
        return True

    def subscribe_private(self, subscription: Dict[str, str], callback: Callable) -> bool:
        """
        Subscribe to private data channels.

        Args:
            subscription (Dict[str, str]): Subscription details, including the API token.
            callback (Callable): The callback function to handle received data.

        Returns:
            True if request went without problem.
        """
        if not self.client:
            return False
        try:
            self.client.subscribe_private(subscription=subscription, callback=callback)
        except twisted_error as twisted_err:
            logger.error(f"Twisted error occurred while subscribing to private data channel: {twisted_err}")
            return False
        return True

    def on_ticker(self, message: Dict[str, Any]) -> None:
        """
        Handle ticker messages used as callback

        Args:
            message (Dict[str, Any]): A dictionary containing ticker data.
        """
        data: Dict[str, Any] = message
        self.subscribe_message(data=data)

        if isinstance(data, list):
            # Ticker data format: [channelID, {'c': [price, volume]}, "ticker", "symbol"]

            ticker_data = {
                'price': data[1]['c'][0],
                'volume': data[1]['c'][1],
                'time': str(arrow.utcnow().to('utc').format(
                                                'YYYY-MM-DD HH:mm:ss.SSS'))
            }
            symbol = data[3]

            try:
                symbol = self._markets[symbol]
            except KeyError:
                pass

            with Cache() as store:
                _ = store.update_ticker(symbol=symbol,
                                          exchange="kraken",
                                          data=ticker_data)
            self.cache_ticker_reply = 1

    def on_trade(self, message: Dict[str, Any]) -> None:
        """
        Handle trade messages, used as callback

        Args:
            message (Dict[str, Any]): A dictionary containing trade data.

        Returns:
            None
        """
        data: Dict[str, Any] = message
        self.subscribe_message(data=data)

        if isinstance(data, list):
            # Trade data format: [channelID, [[price, volume, time, side, orderType, misc], ...], "trade", "pair"]
            trades = data[1]
            subscription = data[2]
            symbol = data[3]

            for trade in trades:
                trade_data = {
                    'price': trade[0],
                    'volume': trade[1],
                    'time': arrow.get(float(trade[2])).format("YYYY-MM-DD HH:mm:ss.SSS"),
                    'side': trade[3],
                    'order_type': trade[4]
                }
                try:
                    symbol = self._markets[symbol]
                except KeyError:
                    pass
                with Cache() as store:
                    """ i want to save on redis list """
                    _ = store.push_trade_list(
                                        symbol=symbol,
                                        exchange="kraken",
                                        trade=trade_data)
            self.cache_trade_reply = 1

    def on_my_trade(self, message: Dict[str, Any]):
        """
        Handle user trade messages, callback.

        Args:
            message (Dict[str, Any]): A dictionary containing trade data.

        Returns:
            None
        """
        data: Dict[str, Any] = message
        self.subscribe_message(data=data)
        with Cache() as store:
            user_ex: ExchangeStruct = store.get_exchange(ex_id=self.ex_id)
        if isinstance(data, list):
            trades = data[0]
            for trade_dict in trades:
                trade_key = next(iter(trade_dict))
                trade = trade_dict[trade_key]
                if 'posstatus' in trade:
                    trade_data = {
                        'leverage': round(float(trade['margin'])),
                        'cost': float(trade['cost']),
                        'fee': float(trade['fee']),
                        'ex_order_id': trade['ordertxid'],
                        'order_type': trade['ordertype'],
                        'symbol': self._markets[trade['pair']],
                        'price': float(trade['price']),
                        'timestamp': trade['time'],
                        'time': arrow.get(float(trade['time'])).format("YYYY-MM-DD HH:mm:ss.SSS"),
                        'side': trade['type'],
                        'volume': float(trade['vol']),
                        'ex_trade_id': trade_key,
                        'uid': user_ex.uid,
                        'ex_id': self.ex_id,
                    }
                    trade_struct = TradeStruct.from_dict(trade_data)
                    with Cache() as store:
                        """ i want to save on redis list """
                        res = store.push_my_trades_list(
                                        uid=user_ex.uid,
                                        exchange=user_ex.ex_id,
                                        trade=trade_struct.to_dict())

    def on_my_order(self, message: Dict[str, Any], local_oid: str):
        """
        Handle open order messages, callback

        Args:
            message (Dict[str, Any]): A dictionary containing open order data.
        """
        data: Dict[str, Any] = message
        if 'txid' in data:
            with Cache() as store:
                store.push_open_order(oid=data['txid'], local_oid=local_oid)
        if 'errorMessage' in data:
            with Cache() as store:
                logger.info(f"Error processing order: {data['errorMessage']} {message}")
                store.push_open_order(oid='error', local_oid=local_oid)

    def cancel_order(self, message: Dict[str, Any], local_oid: str):
        """
        Handle open order messages, callback

        Args:
            message (Dict[str, Any]): A dictionary containing open order data.
        """
        data: Dict[str, Any] = message
        if data['event'] == 'cancelOrderStatus':
            with Cache() as store:
                store.push_open_order(oid=data['status'], local_oid=local_oid)

    def on_my_open_orders(self, message: Any):
        """
        Handle my open order messages.

        Args:
            message (Any): A dictionary containing open order message.
        """
        self.subscribe_message(data=message)
        if isinstance(message, List):
            if message[0]:
                order = message[0][0]
                order_id, order_dict = order.popitem()
                timestamp = None
                odetail = {}
                if 'descr' in order_dict:
                    odetail = {
                               "timestamp": order_dict['opentm'],
                               "ex_id": self.ex_id,
                               "ex_order_id": order_id,
                               "exchange": "kraken",
                               "symbol": 'BTC/USD',
                               "volume": order_dict['vol'],
                               "price": order_dict['avg_price'],
                               'cost': order_dict['cost'],
                               'fee': order_dict['fee'],
                               'status': order_dict['status'],
                               'order_type': order_dict['descr']['ordertype'],
                               'side': order_dict['descr']['type'],
                               'leverage': order_dict['descr']['leverage'].split(":")[0]
                               }
                if 'lastupdated' in order_dict and 'vol_exec' in order_dict and not timestamp:
                    odetail = {
                           "timestamp": order_dict['lastupdated'],
                           "volume": order_dict['vol_exec'],
                           "status": order_dict['status'],
                           "cost": order_dict['cost'],
                           "fee": order_dict['fee'],
                           "price": order_dict['avg_price'],
                           }
                if odetail:
                    self.cache_order_reply = 1
                    with Cache() as store:
                        store.save_order_data(ex_id=self.ex_id,
                                              oid=order_id,
                                              data=odetail)

    def subscribe_message(self, data: Dict) -> None:
        """
        Handles a subscription message from the Kraken WebSocket API.
        Args:
            data (dict): The message data received from the WebSocket.
        Returns:
            None
        """
        if 'event' in data and data['event'] == 'subscriptionStatus':
            if data['status'] == 'subscribed':
                try:
                    pair = data['pair']
                except KeyError:
                    pair = ''
                logger.info(f"Kraken subscribed to {data['subscription']['name']} {pair}")
                self.subscriptions.append(data['subscription']['name'])
                if data['subscription']['name'] == 'ticker':
                    if pair not in self.subscribed_tickers:
                        self.subscribed_tickers.append(pair)
                if data['subscription']['name'] == 'trade':
                    if pair not in self.subscribed_trades:
                        self.subscribed_trades.append(pair)
            else:
                error_message = data.get('errorMessage', 'Unknown error')
                if 'Invalid session' in error_message:
                    with Cache() as store:
                        store.push_ws_error(
                            error=error_message,
                            ex_id=self.ex_id)
                else:
                    logger.warning(f"Failed to subscribe: {data}")
