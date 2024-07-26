import json
import time
import hmac
import hashlib
import threading
import websocket
from typing import Dict, Any, Optional, List, Callable
from libs import log
from libs.caches.trades_cache import Cache
from libs.structs.trade_struct import TradeStruct
from libs.structs.exchange_struct import ExchangeStruct
from libs.database_ohlcv import Database, DatabaseOHLCV

logger = log.fullon_logger(__name__)


class WebSocket:
    """A WebSocket client for interacting with the BitMEX API."""

    def __init__(self, markets: Dict, ex_id: str, api_key: str, api_secret: str) -> None:
        """
        Initialize the WebSocket client.

        Args:
            markets (Dict): A dictionary of market details.
            ex_id (str): The exchange ID.
            api_key (str): The API key for authentication.
            api_secret (str): The API secret for authentication.
        """
        self._markets: Dict = markets
        self.ex_id: str = ex_id
        self.api_key: str = api_key
        self.api_secret: str = api_secret
        self.client: Optional[websocket.WebSocketApp] = None
        self.subscriptions: List[str] = []
        self.subscribed_tickers: List[str] = []
        self.subscribed_trades: List[str] = []
        self.started: bool = False
        self.cache_trade_reply: int = 0
        self.cache_ticker_reply: int = 0
        self.cache_my_trade_reply: int = 0
        self.cache_order_reply: int = 0

    def __del__(self):
        self.stop()

    def _wait_for_connection(self, timeout: int = 5) -> None:
        """Wait for the WebSocket connection to be established."""
        count = 0
        while not self.is_connected() and not self.started and count < timeout:
            time.sleep(1)
            count += 1
        if not self.started:
            logger.error("Failed to establish WebSocket connection")
        else:
            logger.info("Bitmex WebSocket Connected!")

    def connect(self) -> None:
        """Establish a WebSocket connection to BitMEX."""
        websocket.enableTrace(False)
        self.client = websocket.WebSocketApp(
            "wss://www.bitmex.com/realtime",
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        wst = threading.Thread(target=self.client.run_forever)
        wst.daemon = True
        wst.start()
        self._wait_for_connection()
        self.start_ping()

    def stop(self) -> None:
        """Close the WebSocket connection."""
        if self.client:
            self.client.close()
        self.client = None
        self.started = False

    def is_connected(self) -> bool:
        """Check if the WebSocket is connected."""
        return self.client is not None and self.client.sock and self.client.sock.connected

    def subscribe_public(self, subscription: Dict[str, str], pairs: List[str], callback: Callable) -> bool:
        """
        Subscribe to public channels for multiple pairs.

        Args:
            subscription (Dict[str, str]): Subscription details.
            pairs (List[str]): List of trading pairs.
            callback (Callable): The callback function to handle received data.

        Returns:
            bool: True if subscription request was sent successfully, False otherwise.
        """
        if not self.is_connected():
            logger.error("WebSocket is not connected")
            return False

        sub_data = {
            "op": "subscribe",
            "args": [f"{subscription['name']}:{pair}" for pair in pairs]
        }
        self.client.send(json.dumps(sub_data))
        return True

    def subscribe_private(self, subscription: Dict[str, str], callback: Callable) -> bool:
        """
        Subscribe to a private channel.

        Args:
            subscription (Dict[str, str]): Subscription details.
            callback (Callable): The callback function to handle received data.

        Returns:
            bool: True if subscription request was sent successfully, False otherwise.
        """
        if not self.is_connected():
            logger.error("WebSocket is not connected")
            return False

        expires = int(time.time()) + 5
        signature = self.generate_signature(f'GET/realtime{expires}')
        auth_data = {
            "op": "authKeyExpires",
            "args": [self.api_key, expires, signature]
        }
        self.client.send(json.dumps(auth_data))
        sub_data = {
            "op": "subscribe",
            "args": [subscription['name']]
        }
        self.client.send(json.dumps(sub_data))
        return True

    def subscribe_tickers(self, tickers: List[str]) -> bool:
        """
        Subscribe to ticker channels for multiple symbols.

        Args:
            tickers (List[str]): List of ticker symbols.
        """
        subscription = {'name': 'instrument'}
        self.subscribe_public(subscription, tickers, self.on_ticker)
        # Wait for a short period to receive subscription responses
        time.sleep(2)
        # Log the results
        for ticker in tickers:
            if not f"instrument:{ticker}" in self.subscriptions:
                logger.warning(f"Failed to subscribe to {ticker}. It may not exist on BitMEX.")
                return False
        return True

    def unsubscribe_tickers(self) -> bool:
        """Unsubscribe from all ticker channels."""
        if not self.is_connected():
            logger.error("WebSocket is not connected")
            return False

        for ticker in self.subscribed_tickers:
            unsub_data = {
                "op": "unsubscribe",
                "args": [f"instrument:{ticker}"]
            }
            self.client.send(json.dumps(unsub_data))
        self.subscribed_tickers.clear()
        logger.info("Unsubscribed from all ticker channels")
        return True

    def subscribe_trades(self, tickers: List[str]) -> bool:
        """
        Connect to public trade feeds for specified tickers.

        Args:
            tickers (List[str]): List of trading tickers to subscribe to.

        Returns:
            bool: True if successfully connected, False otherwise.
        """
        if not self.is_connected():
            logger.error("WebSocket is not connected")
            return False

        subscription = {'name': 'trade'}
        success = self.subscribe_public(subscription, tickers, self.on_trade)

        if success:
            logger.info(f"Successfully connected to trade feeds for symbols: {', '.join(tickers)}")
            # Wait for a short period to receive subscription responses
            time.sleep(2)
            # Verify subscriptions
            for ticker in tickers:
                if f"trade:{ticker}" not in self.subscriptions:
                    logger.warning(f"Failed to subscribe to trade feed for {ticker}")
                    return False
            return True
        else:
            logger.error("Failed to connect to trade feeds")
            return False

    def unsubscribe_trades(self) -> bool:
        """
        Disconnect from public trade feeds for specified symbols.

        Returns:
            bool: True if successfully disconnected, False otherwise.
        """

        if not self.is_connected():
            logger.error("WebSocket is not connected")
            return False

        for ticker in self.subscribed_trades:
            unsub_data = {
                "op": "unsubscribe",
                "args": [f"instrument:{ticker}"]
            }
            self.client.send(json.dumps(unsub_data))
        self.subscribed_tickers.clear()
        logger.info("Unsubscribed from all trade channels")
        return True

    def subscribe_my_trades(self) -> bool:
        """
        Subscribes to user's own trades.

        Returns:
        bool: True if the subscription was successfully created, False otherwise.
        """
        if not self.is_connected():
            logger.error("WebSocket is not connected")
            return False

        if 'execution' in self.subscriptions:
            logger.info("Already subscribed to own trades")
            return True

        subscription = {'name': 'execution'}
        if self.subscribe_private(subscription, self.on_my_trade):
            # Wait for the subscription to be confirmed
            timeout = 10  # 10 seconds timeout
            start_time = time.time()
            while 'execution' not in self.subscriptions:
                if time.time() - start_time > timeout:
                    logger.error("Timed out waiting for own trades subscription confirmation")
                    return False
                time.sleep(0.5)
            logger.info("Successfully subscribed to own trades")
            return True
        else:
            logger.error("Failed to subscribe to own trades")
            return False

    def subscribe_candles(self, tickers: List[str]) -> bool:
        """
        Subscribe to 1-minute candle (OHLCV) channels for multiple symbols.

        Args:
            tickers (List[str]): List of ticker symbols.

        Returns:
            bool: True if subscription request was sent successfully, False otherwise.
        """
        if not self.is_connected():
            logger.error("WebSocket is not connected")
            return False

        subscription = {'name': 'tradeBin1m'}
        success = self.subscribe_public(subscription, tickers, self.on_candle)

        if success:
            logger.info(f"Successfully connected to 1-minute candle feeds for symbols: {', '.join(tickers)}")
            # Wait for a short period to receive subscription responses
            time.sleep(2)
            # Verify subscriptions
            for ticker in tickers:
                if f"tradeBin1m:{ticker}" not in self.subscriptions:
                    logger.warning(f"Failed to subscribe to 1-minute candle feed for {ticker}")
                    return False
            return True
        else:
            logger.error("Failed to connect to 1-minute candle feeds")
            return False

    def unsubscribe_candles(self) -> bool:
        """
        Unsubscribe from all 1-minute candle channels.

        Returns:
            bool: True if unsubscribe request was sent successfully, False otherwise.
        """
        if not self.is_connected():
            logger.error("WebSocket is not connected")
            return False

        unsub_data = {
            "op": "unsubscribe",
            "args": [sub for sub in self.subscriptions if sub.startswith("tradeBin1m:")]
        }
        self.client.send(json.dumps(unsub_data))

        # Remove unsubscribed channels from the subscriptions list
        self.subscriptions = [sub for sub in self.subscriptions if not sub.startswith("tradeBin1m:")]

        logger.info("Unsubscribed from all 1-minute candle channels")
        return True

    def on_candle(self, message: Dict[str, Any]) -> None:
        """
        Handle 1-minute candle (OHLCV) messages.

        Args:
            message (Dict[str, Any]): The received candle data.
        """
        data = message.get('data', [])
        for candle in data:
            symbol = self.replace_symbol(symbol=candle.get('symbol'))
            candle_data = [[candle.get('timestamp'),
                            float(candle.get('open', 0)),
                            float(candle.get('high', 0)),
                            float(candle.get('low', 0)),
                            float(candle.get('close', 0)),
                            float(candle.get('volume', 0))]]
            with DatabaseOHLCV(exchange='bitmex', symbol=symbol) as dbase:
                dbase.fill_candle_table(table='candles1m', data=candle_data)
            logger.info(f"Received 1-minute candle for {symbol}: {candle_data}")
            key = f"bitmex:{symbol}"

    def start_ping(self):
        """Start sending ping messages to keep the connection alive."""
        def ping():
            while self.is_connected():
                try:
                    self.client.send('ping')
                    time.sleep(30)  # Send a ping every 30 seconds
                except Exception as e:
                    logger.error(f"Error sending ping: {e}")
                    break

        ping_thread = threading.Thread(target=ping)
        ping_thread.daemon = True
        ping_thread.start()
        logger.info("Starting Bitmex websocket keepalive ping")

    def generate_signature(self, message: str) -> str:
        """Generate a signature for authentication."""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def on_open(self, ws):
        """Callback for when the WebSocket connection is opened."""
        logger.info("BitMEX WebSocket connection opened")
        self.started = True

    def on_message(self, ws, message):
        """Callback for when a message is received."""
        if 'pong' in message:
            logger.debug("Received pong from server")
            return
        try:
            data: Dict[str, Any] = json.loads(message)
            if 'table' in data:
                match data['table']:
                    case 'trade':
                        self.on_trade(data)
                    case 'order':
                        self.on_order(data)
                    case 'instrument':
                        self.on_ticker(data)
                    case  'execution':
                        self.on_my_trade(data)
                    case 'tradeBin1m':
                        self.on_candle(data)
            elif 'success' in data and 'subscribe' in data:
                self.on_subscription_success(data)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode message: {message}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def on_error(self, ws, error):
        """Callback for when an error occurs."""
        logger.warning(f"BitMEX WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        """Callback for when the WebSocket connection is closed."""
        logger.info(f"BitMEX WebSocket connection closed: {close_status_code} - {close_msg}")
        self.started = False

    def on_subscription_success(self, message: Dict[str, Any]) -> None:
        """Handle subscription success messages."""
        if message.get('success'):
            channel = message.get('subscribe')
            if channel not in self.subscriptions:
                self.subscriptions.append(channel)
            logger.info(f"Successfully subscribed to channel: {channel}")
        else:
            logger.warning(f"Subscription failed: {message.get('error')}")

    @staticmethod
    def replace_symbol(symbol, separate=True):
        """
        """
        match symbol:
            case 'XBTUSD':
                return 'BTCUSD'
        return symbol

    def on_trade(self, message: Dict[str, Any]) -> None:
        """Handle trade messages."""
        data = message.get('data', [])
        for trade in data:
            symbol = self.replace_symbol(symbol=trade.get('symbol'))
            trade_data = {
                'price': float(trade.get('price', 0)),
                'volume': float(trade.get('size', 0)),
                'time': trade.get('timestamp'),
                'side': 'buy' if trade.get('side') == 'Buy' else 'sell',
                'symbol': symbol,
                'order': trade.get('trdMatchID')
            }
            with Cache() as store:
                res = store.push_trade_list(
                    symbol=trade_data['symbol'],
                    exchange="bitmex",
                    trade=trade_data
                )
            self.cache_trade_reply = res

    def on_order(self, message: Dict[str, Any]) -> None:
        """Handle order messages."""
        data = message.get('data', [])
        for order in data:
            order_data = {
                'ex_order_id': order.get('orderID'),
                'symbol': order.get('symbol'),
                'price': float(order.get('price', 0)),
                'volume': float(order.get('orderQty', 0)),
                'side': order.get('side', '').lower(),
                'order_type': order.get('ordType'),
                'status': order.get('ordStatus'),
                'timestamp': order.get('timestamp'),
            }
            with Cache() as store:
                store.save_order_data(
                    ex_id=self.ex_id,
                    oid=order_data['ex_order_id'],
                    data=order_data
                )
            self.cache_order_reply += 1

    def on_ticker(self, message: Dict[str, Any]) -> None:
        """Handle ticker messages."""
        data = message.get('data', [])
        for instrument in data:
            ticker_data = {
                'price': instrument.get('lastPrice'),
                'volume': instrument.get('volume'),
                'time': instrument.get('timestamp')
            }
            if ticker_data['price']:
                symbol = instrument.get('symbol')
                try:
                    symbol = self._markets[symbol]
                except KeyError:
                    pass
                with Cache() as store:
                    res = store.update_ticker(
                        symbol=symbol,
                        exchange="bitmex",
                        data=ticker_data
                    )
                self.cache_ticker_reply = res

    def get_subscribed_tickers(self) -> List[str]:
        """
        Get the list of successfully subscribed tickers.

        Returns:
            List[str]: List of subscribed ticker symbols.
        """
        return self.subscribed_tickers

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
                    self.cache_my_trade_reply = 1

    def subscribe_message(self, data: Dict) -> None:
        """
        Handles a subscription message from the BitMEX WebSocket API.

        Args:
            data (dict): The message data received from the WebSocket.

        Returns:
            None
        """
        if 'success' in data and data.get('request', {}).get('op') == 'subscribe':
            subscription = data.get('request', {}).get('args', [])
            if subscription:
                logger.info(f"Subscribed to BitMEX {subscription[0]}")
                if subscription[0] not in self.subscriptions:
                    self.subscriptions.append(subscription[0])
            else:
                logger.warning(f"Subscription confirmation received but no channel specified: {data}")
        elif 'error' in data:
            logger.warning(f"Subscription failed: {data.get('error')}")