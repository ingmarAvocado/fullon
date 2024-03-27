from multiprocessing import Value
import sys
import ccxt
import time
import json
from libs import settings, log
from libs.secret import SecretManager
from libs.cache import Cache
from libs.database import Database
from libs.structs.trade_struct import TradeStruct
from libs.structs.order_struct import OrderStruct
from libs.structs.exchange_struct import ExchangeStruct
from typing import Dict, Union, List, Any, Optional, Tuple
import arrow

logger = log.fullon_logger(__name__)


class Interface:

    _socket: Optional[Any]
    _sleep: float = 3.0
    websocket_connected = False
    sleep = 0
    ohlcv = False
    has_ticker: bool = True

    def __init__(self,
                 exchange: str,
                 params: Optional[ExchangeStruct] = None,
                 dry_run=False):
        self.exchange = exchange
        self.params = ExchangeStruct()
        if params:
            self.params = params
        if self.params.ex_id != '':
            key, secret = self.get_user_key(
                uid=self.params.uid, exchange=self.params.cat_ex_id)

        self.ws = getattr(ccxt, exchange)({
            'apiKey': key,
            'secret': secret,
            'verbose': False,
            'enableRateLimit': False
        })

        if self.params.test:
            if 'test' in self.ws.urls:
                self.ws.urls['api'] = self.ws.urls['test']
                self.ws.urls['apiKey'] = key
                self.ws.urls['secret'] = secret
                # logger.info("allegedly running test url: %s" %(self.ws.urls['api']))
            elif self.test_url():
                self.ws.urls['apiKey'] = key
                self.ws.urls['secret'] = secret
            else:
                # logger.info("Asked for test/sanddbox but exchange -%s- has none" %(self.ws.name))
                raise ValueError("no test url")

        self.err = ""
        # if  not lowkey:
        # self.execute_ws("load_markets")
        self.precision = None
        self.futures = False
        self.ohlcv_needs_trades = False
        self.no_sleep = ['minimum_order_cost', 'get_quote', 'get_pair_decimals', 'get_cost_decimals', 'get_markets', 'get_market']
        if self.params.cat_ex_id == '':
            with Cache() as store:
                self.params.cat_ex_id = store.get_cat_ex_id(
                    exchange=self.exchange)
        logger.info(f"Loading Exchange {self.exchange} - ({self.params.ex_id})")

        return None

    def __del__(self) -> None:
        self.stop()

    def stop(self):
        pass

    def refresh(self):
        pass

    def test(self, symbol):
        if self.get_market(symbol):
            return True
        else:
            return False

    @staticmethod
    def get_user_key(uid: int, exchange: str) -> tuple[str, str]:
        """
        Retrieve the user's API key for a specific exchange using the secret manager.

        :param uid: The user ID whose API key needs to be fetched.
        :param exchange: The name of the exchange for which the API key is required.
        :return: The API key for the specified user and exchange, or None if not found.
        """
        hush = SecretManager()
        exchange = str(exchange)
        payload = hush.access_secret_version(secret_id=str(uid))
        key = ''
        secret = ''
        if payload:
            try:
                key, secret = json.loads(payload)[exchange].split(":")
            except KeyError:
                pass
        return (key, secret)

    def set_leverage(self, symbol, leverage):
        return 1

    def get_market(self, symbol):
        market = self.execute_ws("market", [symbol])
        if market['info']:
            self.precision = market['precision']['price']
            self.taker_fee = market['taker']
            self.maker_fee = market['maker']
            self.market_info = market['info']
            return True
        else:
            return False

    def get_markets(self) -> Dict[str, Dict[str, str]]:
        """
        This method retrieves market data from the WebSocket instance, processes it,
        and returns a dictionary containing the relevant information for each market.
        """
        # Get the markets dictionary from the WebSocket instance
        markets_dict = self.ws.markets
        # Initialize an empty dictionary to store the processed market data
        result = {}
        # Iterate over the markets in the markets_dict
        for market in markets_dict.values():
            # Add the extracted information to the result dictionary
            result[market['symbol']] = {
                'symbol': market['symbol'],
                'wsname': market['info']['wsname'],
                'base': market['base'],
                'cost_decimals': market['info']['cost_decimals'],
                'pair_decimals': market['info']['pair_decimals']
            }

        # Return the processed result dictionary
        return result

    def execute_ws(self, api_call: str, vals: list = [], retries=0) -> Any:
        """
        Executes a WebSocket API call for the current exchange.

        Args:
        api_call (str): The name of the API call to execute.
        vals (list, optional): The list of arguments to pass to the API call. Defaults to [].

        Returns:
        dict or None: The result of the API call as a dictionary, or None if an error occurred.
        """
        retvalue = None
        try:
            retvalue = getattr(self.ws, api_call)(*vals)
            self.auth = True
        except ccxt.DDoSProtection as e:
            logger.error("Request Timed Out, sleeping")
            if retries < 69:  # one hour trying
                time.sleep(30)
                return self.execute_ws(api_call=api_call, vals=vals, retries=retries+1)
            retvalue = False
        except ccxt.RequestTimeout as e:
            logger.error("Request Timed Out, sleeping")
            if retries < 69:  # one hour trying
                time.sleep(30)
                return self.execute_ws(api_call=api_call, vals=vals, retries=retries+1)
            retvalue = False
        except ccxt.ExchangeNotAvailable as error:
            logger.error("Exchange %s Not Available due to downtime or maintenance (%s)", self.exchange, str(error))
            logger.error(f"Call {api_call}")
            if retries < 140:  # one hour trying
                time.sleep(15)
                return self.execute_ws(api_call=api_call, vals=vals, retries=retries+1)
            retvalue = False
        except ccxt.AuthenticationError as e:
            logger.error("Authentication Error (missing API keys, ignoring)")
            retvalue = False
        except ccxt.InsufficientFunds as e:
            logger.error("Insufficient Funds")
            retvalue = False
        except ccxt.OrderNotFound as e:
            logger.error("Order Not Found")
            retvalue = False
        except ccxt.NetworkError as error:
            logger.error("Network error exchange(%s): %s, retrying in 5 seconds", self.exchange, str(error))
            logger.error(f"Call {api_call}")
            if retries < 140:
                time.sleep(5)
                return self.execute_ws(api_call=api_call, vals=vals, retries=retries+1)
            retvalue = False
        except ccxt.NotSupported:
            logger.error("API call not supported")
            retvalue = False
        except ccxt.ExchangeError as error:
            logger.error("Exchange Error, sleeping: %s", str(error))
            retvalue = False
        except ccxt.base.errors.ExchangeError:
            logger.error("Exchange Error, sleeping: %s", str(error))
            retvalue = False
        return retvalue

    def get_cash(self, symbol):
        with Cache() as store:
            cash = store.get_user_size_by_symbol(
                    uid=self.params.uid,
                    ex_id=self.params.ex_id,
                    symbol=symbol.split('/')[1],
                    free=True)
        return cash

    def get_order(self, oid, symbol):
        return self.execute_ws("fetch_order", [oid, symbol])

    def fetch_orders(self,
                     symbol: str,
                     since: Union[str, None] = None,
                     limit: Union[int, None] = None,
                     params: Dict = {}) -> Dict[str, str]:
        """
        Fetches orders for a given trading symbol.

        Args:
        symbol (str): The trading symbol to fetch orders for.
        since (str, optional): The timestamp to start fetching orders from. Defaults to None.
        limit (int, optional): The maximum number of orders to fetch. Defaults to None.
        params (dict, optional): Additional parameters to pass to the exchange API. Defaults to {}.

        Returns:
        dict: A dictionary of order IDs and their corresponding status.
        """
        ret_orders = {}
        if limit is None:
            limit = 300
        if since:
            since = int(arrow.get(since).shift(days=-3).timestamp())
        orders = self.execute_ws("fetch_orders", [symbol, since, limit, params])
        if orders:
            for order in orders:
                status = order['status']
                if status == 'New':
                    status = 'Open'
                ret_orders[str(order['id'])] = status
        return ret_orders

    def cancel_all_orders(self, symbol):
        orders = self.execute_ws("fetch_open_orders", [symbol,])
        for o in orders:
            self.execute_ws("cancel_order", [o['id'], symbol])
        return None

    def cancel_order(self, oid: str) -> None:
        """
        Cancels an open order by ID.

        Args:
            order_id (str): The ID of the order to cancel.

        Returns:
            None
        """
        pass

    def create_order(self, order: OrderStruct) -> Any:
        # self.ws.verbose = True
        # print(f"order details symbol ({symbol}) amount ({amount}) side ({side}) order_type ({order_type})")
        if amount % 1 == 0:
            amount = int(amount)
        if 'limit' in order_type:
            price = self.decimal_rules(symbol=symbol, price=price)
        if 'market' in order_type:
            o = self.execute_ws(
                "create_order", [
                    symbol, order_type, side, amount, None, params])
        else:
            o = self.execute_ws(
                "create_order", [
                    symbol, order_type, side, amount, price, params])
        # self.ws.verbose = False
        return o

    def get_candles(self, symbol: str, timeframe: str, since: Union[int, float], limit: Union[int, None], params: dict = {}) -> Union[List, None]:
        """
        Fetches candlestick data for a given trading symbol and timeframe.

        Args:
        symbol (str): The trading symbol to fetch candles for.
        timeframe (str): The timeframe to fetch candles for.
        since (int, float): The timestamp to start fetching candles from.
        limit (int, None): The maximum number of candles to fetch. Defaults to None.
        params (dict, optional): Additional parameters to pass to the exchange API. Defaults to {}.

        Returns:
        list or None: A list of candlestick data or None if no data is available.
        """
        if len(str(since)) != 13:  # not in milliseconds
            since = int(since * 1000)
        if since and not limit:
            ohlcv = self.execute_ws("fetch_ohlcv", [symbol, timeframe, since])
        elif since and limit:
            ohlcv = self.execute_ws("fetch_ohlcv", [symbol, timeframe, since, limit, params])
        elif not since and not limit:
            ohlcv = self.execute_ws("fetch_ohlcv", [symbol, timeframe])
        else:
            raise ValueError("Invalid arguments: either since or limit must be specified.")
        if not ohlcv:
            return None
        return ohlcv

    def get_tickers(self, sleep: int = 1) -> Dict[str, Dict[str, Union[str, float]]]:
        """
        Retrieve ticker information for all available markets.

        :param sleep: Sleep interval between ticker updates, default is 1 second.
        :return: A dictionary with ticker symbols as keys and ticker information as values.
        """
        markets = self.execute_ws("fetch_tickers")
        if not markets:
            return {}

        tickers = {}
        for m in markets:
            market = markets[m]
            tickers.update(
                {
                    market['symbol']: {
                        'symbol': market['symbol'],
                        'datetime': arrow.get(
                            float(
                                market['info']['closeTime']) /
                            1000).format(),
                        'openPrice': market['info']['prevClosePrice'],
                        'highPrice': market['info']['highPrice'],
                        'lowPrice': market['info']['lowPrice'],
                        'close': market['info']['lastPrice'],
                        'volume': market['info']['volume']
                    }
                }
            )
        return tickers

    def get_balances(self, count: int = 0) -> Dict:
        """
        Retrieve the user's account information with balances for
        each cryptocurrency and calculate the total balance in terms of BTC.

        :param count: Number of retries for fetching user
                      account information, default is 0.
        :return: A list containing the user's account information or
                 None if balances could not be retrieved.
        """
        pre_balances = self.execute_ws("fetchBalance")
        if not pre_balances:
            return {}
        remove_list = ['info', 'free', 'used', 'total', 'timestamp', 'datetime']
        for key in remove_list:
            pre_balances.pop(key, None)
        positions = []
        balances = {}
        total = 0
        free = 0
        used = 0
        pairs = []
        for asset, values in pre_balances.items():
            vals = values.copy()
            vals['symbol'] = asset
            balances[asset] = vals
            if 'USD' not in asset:
                pairs.append(f"{asset}/USD")
        pairs = self.replace_symbols(symbols=pairs)
        tickers = self.get_tickers(pairs=pairs)
        for symbol, balance in balances.items():
            total += self.get_usd_value(symbol=symbol,
                                        balance=balance['total'],
                                        tickers=tickers)
            positions.append({'symbol': symbol,
                              'free': balance['free'],
                              'used': balance['used'],
                              'total': balance['total']})
        account = {
            'total': total,
            'used': None,
            'free': None,
            'base': 'USD',
            'positions': positions}
        return account

    def get_positions(self) -> Dict:
        """
        Get open positions and consolidate them by pair, calculating the average price.

        :return: A dictionary containing consolidated positions with the average price, total volume, and total fee.
        """
        positions = self.execute_ws("private_post_openpositions")
        cons_positions = defaultdict(lambda: {'total_cost': 0.0,
                                              'total_volume': 0.0,
                                              'total_fee': 0.0,
                                              'count': 0.0})
        if positions['error'] == []:
            for key, value in positions['result'].items():
                pair = value['pair']
                cost = float(value['cost'])
                volume = float(value['vol'])
                fee = float(value['fee'])
                cons_positions[pair]['total_cost'] += cost
                cons_positions[pair]['total_volume'] += volume
                cons_positions[pair]['total_fee'] += fee
                cons_positions[pair]['count'] += 1
                cons_positions[pair]['price'] = \
                    cons_positions[pair]['total_cost'] / cons_positions[pair]['total_volume']
        return cons_positions

    def fetch_trades(self,
                     symbol: Optional[str] = None,
                     since: Optional[int] = None,
                     limit: Optional[int] = None,
                     params: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
        """
        Fetches all trades for a given symbol from the exchange.

        Args:
            symbol (str, optional): The symbol to fetch trades for. Defaults to None.
            since (int, optional): The timestamp to filter trades after. Defaults to None.
            limit (int, optional): The maximum number of trades to fetch. Defaults to None.
            params (Dict[str, Any], optional): Additional parameters to pass to the exchange API. Defaults to {}.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the trades.
        """
        trades = self.execute_ws(
            "fetch_trades", [symbol, since, limit, params])
        correctedtrades = []
        for t in trades:
            if t['info']['isMaker'] == "True":
                t['takerOrMaker'] = "Maker"
                t['type'] = "limit"
            else:
                t['takerOrMaker'] = "Taker"
                t['type'] = "market"
            correctedtrades.append(t)
        return correctedtrades

    def fetch_my_trades(self,
                        symbol: Optional[str] = None,
                        since: Optional[Union[int, float]] = None,
                        limit: Optional[int] = None,
                        params: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
        """
        Fetches the user's trades from the exchange.

        Args:
            symbol (str, optional): The symbol to filter the trades by. Defaults to None.
            since (int, optional): The timestamp to filter trades after. Defaults to None.
            limit (int, optional): The maximum number of trades to fetch. Defaults to None.
            params (Dict[str, Any], optional): Additional parameters to pass to the exchange API. Defaults to {}.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the trades.
        """
        trades = self.execute_ws(
            "fetch_my_trades", [symbol, since, limit])
        return trades

    def rearrange_tickers(self, tickers):
        newtickers = {}
        for tick in tickers:
            symbol = tick[1]
            last = tick[6]
            newtickers.update({symbol: {'last': last}})
        return newtickers

    def decimal_rules(self, price, symbol):
        with Database() as dbase:
            decimals = dbase.get_symbol_decimals(symbol, self.cat_ex_id)
        if decimals == 8:
            return f'{price:.8f}'
        if decimals == 7:
            return f'{price:.7f}'
        if decimals == 6:
            return f'{price:.6f}'
        if decimals == 5:
            return f'{price:.5f}'
        if decimals == 4:
            return f'{price:.4f}'
        if decimals == 3:
            return f'{price:.3f}'
        if decimals == 2:
            return f'{price:.2f}'
        if decimals == 1:
            return f'{price:.1f}'
        if decimals == 0:
            return f'{price:.0f}'
        else:
            return f'{price:.8f}'

    def minimum_order_cost(self, symbol: str) -> float:
        """
        Returns the minimum cost required to place an order for a given symbol.
        :param symbol: The trading symbol (e.g. 'BTC/USD', 'ETH/EUR') to get the minimum order cost for.

        :return: The minimum cost required to place an order for the given symbol.
        """
        try:
            return self.ws.markets[symbol]['limits']['amount']['min']
        except KeyError:
            logger.error("No such symbol (%s)", symbol)
            return 0

    def quote_symbol(self, symbol: str) -> float:
        """
        Returns the quote currency for a given symbol.
        :param symbol: The trading symbol (e.g. 'BTC/USD', 'ETH/EUR')to get the quote currency.

        :return: The minimum cost required to place an order for the given symbol.
        """
        return self.ws.markets[symbol]['quote']

    def get_pair_decimals(self, symbol: str) -> float:
        """
        Returns the decimals for a  currency for a given symbol.
        :param symbol: The trading symbol (e.g. 'BTC/USD', 'ETH/EUR')to get the quote currency.

        :return: The minimum cost required to place an order for the given symbol.
        """
        return int(self.ws.markets[symbol]['info']['pair_decimals'])

    def get_cost_decimals(self, symbol: str) -> float:
        """
        Returns the decimals for a  currency for a given symbol.
        :param symbol: The trading symbol (e.g. 'BTC/USD', 'ETH/EUR')to get the quote currency.

        :return: The minimum cost required to place an order for the given symbol.
        """
        return int(self.ws.markets[symbol]['info']['cost_decimals'])

    def stop_websockets(self) -> None:
        """
        Stops the WebSocket connection and sets the `websocket_connected` attribute to False.
        """
        if self._socket:
            self._socket.stop()
            self.websocket_connected = False
        else:
            logger.warning("WebSocket is not initialized")

    def start_ticker_socket(self, tickers: list) -> bool:
        """
        Subscribes to ticker updates for a list of trading pairs and saves them to Redis.

        Args:
        tickers (list): A list of trading pairs to subscribe to.

        Returns:
        bool: True if the subscription was successfully created, False otherwise.
        """
        return True

    def stop_ticker_socket(self) -> bool:
        """
        UnSubscribes to ticker updates for a list of trading pairs and saves them to Redis.

        Returns:
        bool: True if the subscription was successfully stopped, False otherwise.
        """
        return False

    def socket_connected(self) -> bool:
        """
        Checks if the WebSocket connection is still active.

        Returns:
        bool: True if the WebSocket connection is active, False otherwise.
        """
        return False

    def connect_websocket(self):
        """
        Establishes a connection to the WebSocket and sets the `websocket_connected` attribute to True.
        """
        pass

    def get_sleep(self) -> float:
        """Gets the currency information for a symbol.

        Returns:
            float: Latest sleep time
        """
        sleep = self._sleep if self._sleep > 0 else 0
        return float(sleep)

    def get_asset_pairs(self) -> List[Dict[str, str]]:
        """Retrieves the asset pairs registered on fullon

        Returns:
            List[Tuple[str]]: A list of tuples, each containing an asset pair.
        """
        pairs = {}
        with Cache() as store:
            pairs = store.get_exchange_symbols(exchange=self.params.cat_ex_id)
        return pairs

    def start_my_trades_socket(self) -> bool:
        """
        Subscribes to user trades

        Args:
        tickers (list): A list of trading pairs to subscribe to.

        Returns:
        bool: True if the subscription was successfully created, False otherwise.
        """
        return False

    def start_trade_socket(self, tickers) -> bool:
        """
        Subscribes to user trades

        Args:
        tickers (list): A list of trading pairs to subscribe to.

        Returns:
        bool: True if the subscription was successfully created, False otherwise.
        """
        return False

    def my_open_orders_socket(self) -> bool:
        """
        Subscribes to user's trades.

        Returns:
        None
        """
        return False
