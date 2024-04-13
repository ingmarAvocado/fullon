"""
Cache class for managing caching operations with Redis.
The Cache class provides functionality to interact with
a Redis cache server, including creating, updating,
and retrieving cache entries. It also includes utility
methods for testing the connection to the cache server,
preparing the cache, and filtering cache entries based
on timestamps and component types.
"""

import time
import json
import redis
from  os import listdir
from redis.exceptions import RedisError
from libs import settings, log
from libs.caches import symbol_cache as cache
from libs.structs.tick_struct import TickStruct
from typing import Dict, Any, Optional, List, Tuple

logger = log.fullon_logger(__name__)

try:
    EXCHANGES_DIR = listdir('exchanges/')
except FileNotFoundError:
    EXCHANGES_DIR = listdir('fullon/exchanges/')

for folder in ['ccxt','__init__.py','__pycache__']:
    try:
        EXCHANGES_DIR.remove(folder)
    except ValueError:
        pass


class Cache(cache.Cache):
    """
    A class for managing caching operations with Redis.
    Attributes:
    db_cache (None): Placeholder for the cache instance.
    """

    def get_price(self, symbol: str, exchange: Optional[str] = None) -> Any:
        """
        Get the price for a symbol, optionally using a specific exchange.

        Args:
            symbol (str): The trading symbol to get the price for.
            cat_ex_id (str, optional): The exchange ID to use. Defaults to None.

        Returns:
            float: The price of the symbol.
        """
        if exchange:
            price = self.get_ticker(symbol=symbol, exchange=exchange)[0]
        else:
            price = self.get_ticker_any(symbol=symbol)
        return price

    def update_ticker(self, symbol: str, exchange: str, data: Dict[str, Any]) -> int:
        """
        Update the ticker data for a symbol on a specific exchange and notify subscribers.

        Args:
            symbol (str): The trading symbol to update the ticker for.
            exchange (str): The exchange to update the ticker on.
            data (dict): The new ticker data.

        Returns:
            bool: True if the ticker was updated successfully, False otherwise.
        """
        try:
            # Update the ticker
            self.conn.hset(f"tickers:{exchange}", symbol, json.dumps(data))

            # Publish a message to inform the subscribers of the price update
            # Use a combined exchange:symbol as the channel name for fine-grained subscriptions
            self.conn.publish(f'next_ticker:{exchange}:{symbol}', json.dumps(data))

            return 1
        except RedisError as error:
            return 0

    def del_exchange_ticker(self, exchange: str) -> int:
        """
        Delete the ticker on a specific exchange.

        Args:
            exchange (str): The exchange to update the ticker on.

        Returns:
            bool: True if the ticker was updated successfully, False otherwise.
        """
        try:
            # Update the ticker
            return self.conn.delete(f"tickers:{exchange}")
        except RedisError as error:
            return 0

    def get_next_ticker(self, symbol: str, exchange: str) -> Tuple[float, Optional[str]]:
        """
        Subscribe to a ticker update channel and return the price and timestamp once a message is received.  
        Args:
            symbol (str): The trading symbol for which ticker updates are being listened.
            exchange (str): The exchange that the symbol belongs to.

        Returns:
            Tuple[float, Optional[str]]: A tuple containing the updated price as a float and the timestamp as a string.
            If an error occurs, (0, None) is returned.
        """
        try:
            pubsub = self.conn.pubsub()
            pubsub.subscribe(f'next_ticker:{exchange}:{symbol}')

            for message in pubsub.listen():
                if message['type'] == 'message':
                    ticker = json.loads(message['data'])
                    pubsub.unsubscribe(f'next_ticker:{exchange}:{symbol}')
                    return (float(ticker['price']), ticker['time'])

            return (0, None)
        except (redis.exceptions.TimeoutError, TimeoutError) as e:
            logger.warning(f"No ticker ({exchange}:{symbol}) data received, trying again...")
            time.sleep(0.1)
            pubsub.unsubscribe(f'next_ticker:{exchange}:{symbol}')
            return self.get_next_ticker(symbol=symbol, exchange=exchange)
        except redis.ConnectionError as error:
            # If any error occurred, log it and return (0, None)
            logger.error(f"Error in get_next_ticker: {error}")
            exit()
        except json.JSONDecodeError as e:
            # Log and return (0, None) if there was an error parsing the message
            logger.error(f"Error parsing message in get_next_ticker: {e}")
            exit()

    def get_ticker_any(self, symbol: str) -> float:
        """
        Gets ticker from the database for any exchange given the symbol.

        Args:
        - symbol (str): the symbol to look for (e.g. BTC/USD)

        Returns:
        - float or None: the ticker value or None if not found

        """
        for exchange in EXCHANGES_DIR:
            try:
                ticker = self.conn.hget(name=f"tickers:{exchange}", key=symbol)
                if ticker:
                    return float(json.loads(ticker)['price'])
            except (TypeError, ValueError):
                pass
        return 0

    def get_ticker(self, exchange: str,
                   symbol: str) -> Tuple[Optional[float], Optional[str]]:
        """
        Gets ticker from the database, from exchange_id and symbol.

        Args:
            exchange (str): The exchange name
            symbol (str): The symbol to look for (e.g. BTC/USD).

        Returns:
            tuple: A tuple containing the ticker value (float) and timestamp (str), or (None, None) if not found.
        """
        try:
            ticker = json.loads(self.conn.hget(name=f"tickers:{exchange}", key=symbol))
            return (float(ticker['price']), ticker['time'])
        except TypeError:
            return (0, None)

    def get_tickers(self, exchange: Optional[str] = "") -> List[TickStruct]:
        """
        Gets all tickers from the database, from the specified exchange or all exchanges.

        Args:
            cat_ex_id (str, optional): The exchange ID to use. Defaults to False.

        Returns:
            list: A list of tickers.
        """
        rows = []
        if exchange:
            exchanges = [exchange]
        else:
            exchanges = EXCHANGES_DIR
        for exch in exchanges:
            cursor = 0
            while True:
                cursor, keys = self.conn.hscan(f"tickers:{exch}", cursor, match=f"*")
                for key, value in keys.items():
                    symbol = key.decode()
                    value = value.decode()
                    values = json.loads(value)
                    values['exchange'] = exch
                    values['symbol'] = symbol
                    rows.append(TickStruct.from_dict(values))
                if cursor == 0:
                    break
        return rows

    def round_down(self,
                   symbol: str,
                   exchange: str,
                   sizes: List[float],
                   futures: bool) -> Tuple[float, float, float]:
        """
        Rounds down the sizes for a symbol on a specific exchange.

        Args:
            symbol (str): The trading symbol to round down.
            cat_ex_id (str): The exchange ID to use.
            sizes (list): A list of sizes (free, used, and total).
            futures (bool): Whether to use futures or not.

        Returns:
            tuple: The rounded down sizes.
        """
        if sizes[0] == 0 and sizes[1] == 0 and sizes[2] == 0:
            return 0, 0, 0
        if '/' in symbol:
            currency = symbol.split('/')[0]
            if currency == 'BTC' or futures:
                return sizes
        else:
            return sizes
        price = self.get_ticker(exchange=exchange,
                                symbol=symbol)[0]
        base_currency = symbol.split('/')[1]
        tsymbol = base_currency + "/" + settings.STABLECOIN
        for count, value in enumerate(sizes):
            base = value * price
            if 'USD' in base_currency:
                sizes[count] = base
            else:
                sizes[count] = base * self.get_price(tsymbol)
        if sizes[0] < 2:  # less than 2 usd in value
            return 0, 0, 0
        return sizes
