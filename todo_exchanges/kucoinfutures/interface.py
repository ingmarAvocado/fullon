import sys
import time
from typing import Dict, List, Optional, Union
from libs import settings, log
from exchanges.ccxt.interface import Interface
import arrow

logger = log.fullon_logger(__name__)


class Interface(Interface):
    """This class represents the Kucoin-specific implementation of the ccxt interface."""

    def __init__(self, exchange, db, db_ohlcv, params, dry_run=False):
        logger.info("Loading Kucoin Exchange")
        super().__init__(exchange, db, db_ohlcv, params)
        self.ws.verbose = False
        self.short = True

    def fetch_all_trades(self, symbol: Optional[str] = None, since: Optional[int] = None,
                         limit: Optional[int] = None, params: Optional[Dict] = {}) -> List[Dict]:
        """
        Fetch all trades from Kucoin API and add takerOrMaker field.

        :param symbol: The trading pair symbol, e.g., 'BTC/USD'.
        :param since: Timestamp in milliseconds for filtering trades.
        :param limit: Maximum number of trades to fetch.
        :param params: Additional parameters for the request.
        :return: A list of trade dictionaries with the takerOrMaker field added.
        """
        trades = self.execute_ws("fetch_trades", [symbol, since, limit, params])
        corrected_trades = []
        for trade in trades:
            if trade['takerOrMaker'] is None:
                if trade['fee'] == 0:
                    trade['takerOrMaker'] = 'maker'
                else:
                    trade['takerOrMaker'] = 'taker'
            else:
                trade['takerOrMaker'] = trade['takerOrMaker']
            corrected_trades.append(trade)

        return corrected_trades

    def get_all_tickers(self, sleep: float = 1) -> Dict[str, Dict[str, Union[str, float]]]:
        """
        Fetches all tickers from the exchange.

        :param sleep: The sleep interval between retries if the market is empty.
        :return: A dictionary containing the ticker information for each symbol.
        """
        time.sleep(settings.INTERVAL)
        markets = self.execute_ws("load_markets")
        if not markets:
            return {}
        tickers = {}
        for market in markets.values():
            symbol = market['info']['symbol']
            datetime = arrow.utcnow().format()
            open_price = float(market['info']['lastTradePrice'])
            high_price = float(market['info']['highPrice'])
            low_price = float(market['info']['lowPrice'])
            close_price = float(market['info']['lastTradePrice'])
            volume = 0.01  # float(market['info']['vol'])
            tickers[symbol] = {
                'symbol': symbol,
                'datetime': datetime,
                'openPrice': open_price,
                'highPrice': high_price,
                'lowPrice': low_price,
                'closePrice': close_price,
                'volume': volume
            }
        return tickers


    def create_order(self, symbol: str, order_type: str, side: str, amount: float, price: str = '',
                     params: Optional[List] = []) -> Dict:
        """
        Create an order with the specified parameters.

        :param symbol: The trading pair symbol, e.g., 'BTC/USD'.
        :param order_type: The order type, e.g., 'limit' or 'market'.
        :param side: The side of the trade, 'buy' or 'sell'.
        :param amount: The order amount.
        :param price: The order price.
        :param params: Additional parameters for the order.
        :return: A dictionary containing the created order information.
        """
        amount = self.find_minimum_order_cost(amount=amount, price=price, symbol=symbol)

        return self.execute_ws("create_order", [symbol, order_type, side, float(amount) - 0.00001, price, params])

    def get_my_trades_from(self, symbol: str, from_id: Optional[str] = None,
                           from_date: Optional[str] = None) -> List[Dict]:
        """
        Fetch trades for a specific symbol starting from a given date.

        :param symbol: The trading pair symbol, e.g., 'BTC/USD'.
        :param from_id: Not used in this implementation.
        :param from_date: The starting date for fetching trades.
        :return: A list of trade dictionaries.
        """
        import arrow
        ts = arrow.get(from_date).timestamp * 1000
        params = {'startTime': ts}

        return self.fetch_my_trades(symbol=symbol, params=params)

    def find_minimum_order_cost(self, amount: float, price: str, symbol: str) -> float:
        """
        Calculate the minimum order cost based on the given amount, price, and symbol.

        :param amount: The order amount.
        :param price: The order price.
        :param symbol: The trading pair symbol, e.g., 'BTC/USD'.
        :return: The minimum order cost.
        """
        if not price:
            price = float(self.cache.get_price(symbol=symbol, cat_ex_id=self.cat_ex_id))
        min_cost = self.minimum_order_cost(symbol=symbol)
        cost = amount * float(price)
        if cost < min_cost:
            return min_cost / float(price)  # return new amount
        return amount

    def minimum_order_cost(self, symbol: str) -> float:
        """
        Get the minimum order cost for a specific symbol.

        :param symbol: The trading pair symbol, e.g., 'BTC/USD'.
        :return: The minimum order cost.
        """
        currency = symbol.split("/")[1]
        if currency == 'BTC':
            return 0.00101
        elif 'USD' in currency:
            return 10.2
        else:
            return 0  # default value

    def create_stop_order(self, symbol: str, side: str, volume: float, price: float,
                          params: Optional[List] = []) -> Dict:
        """
        Emulate stop loss with stop limit for the given symbol, side, volume, and price.

        :param symbol: The trading pair symbol, e.g., 'BTC/USD'.
        :param side: The side of the trade, 'buy' or 'sell'.
        :param volume: The order volume.
        :param price: The stop price.
        :param params: Additional parameters for the order.
        :return: A dictionary containing the created order information.
        """
        final_price = price * (1.01 if side == "Buy" else 0.99)
        final_price = self.decimal_rules(final_price, symbol)
        price = self.decimal_rules(price, symbol)

        kucoin_params = {
            'type': 'STOP_LOSS_LIMIT',
            'stopPrice': price,
            'timeInForce': 'GTC',
            'price': final_price
        }
        kucoin_params.update(params)

        order = self.execute_ws("create_order", [symbol, 'market', side, volume, price, kucoin_params])

        return order

    def create_stop_limit_order(self, symbol: str, side: str, volume: float, price: float, stop_limit: float,
                                params: Optional[Dict] = {}) -> Dict:
        """
        Emulate stop loss with stop limit order for the given symbol, side, volume, and price.

        :param symbol: The trading pair symbol, e.g., 'BTC/USD'.
        :param side: The side of the trade, 'buy' or 'sell'.
        :param volume: The order volume.
        :param price: The stop price.
        :param stop_limit: The stop limit price.
        :param params: Additional parameters for the order.
        :return: A dictionary containing the created order information.
        """
        stop_limit = self.decimal_rules(stop_limit, symbol)
        price = self.decimal_rules(price, symbol)

        kucoin_params = {
            'type': 'STOP_LOSS_LIMIT',
            'stopPrice': stop_limit,
            'timeInForce': 'GTC',
            'price': price
        }
        kucoin_params.update(params)

        order = self.execute_ws("create_order", [symbol, 'market', side, volume, price, kucoin_params])

        return order

    def get_open_orders(self, symbol: Optional[str] = None, since: Optional[int] = None,
                        limit: Optional[int] = None, params: Optional[Dict] = {}) -> Dict[str, str]:
        """
        Get the open orders for the specified symbol, since, and limit.

        :param symbol: The trading pair symbol, e.g., 'BTC/USD'.
        :param since: Timestamp in milliseconds for filtering orders.
        :param limit: Maximum number of orders to fetch.
        :param params: Additional parameters for the request.
        :return: A dictionary of order IDs and their corresponding status ('New' or 'Open').
        """
        ret_orders = {}
        if limit is None:
            limit = 300
        if since:
            import arrow
            since = int(float(arrow.get(since).shift(days=-3).format('X')))

        symbols = []
        if not symbol:
            tmp = self.db.get_my_symbols(uid=self.uid, ex_id=self.ex_id)
            for s in tmp:
                symbols.append(s.symbol)
        else:
            symbols.append(symbol)

        for symbol in symbols:
            orders = self.execute_ws("fetch_orders", [symbol, since, limit, params])

            for o in orders:
                status = o['status'].capitalize()
                if status == 'New' or status == 'Open':
                    ret_orders[o['id']] = status

            time.sleep(settings.INTERVAL)

        time.sleep(1)

        return ret_orders