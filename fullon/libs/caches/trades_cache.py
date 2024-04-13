"""
Cache class for managing caching operations with Redis.
The Cache class provides functionality to interact with
a Redis cache server, including creating, updating,
and retrieving cache entries. It also includes utility
methods for testing the connection to the cache server,
preparing the cache, and filtering cache entries based
on timestamps and component types.
"""

import json
import redis
from libs import log
from libs.caches import orders_cache as cache
from libs.structs.trade_struct import TradeStruct
from typing import Dict, List
from os import listdir

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
    """

    def push_trade_list(self, symbol: str, exchange: str, trade: Dict = {}) -> int:
        """
        Push trade data to a Redis list.

        Args:
            symbol (str): The trading symbol for the asset pair.
            exchange (str): The name of the exchange where the trade occurred.
            trade (dict, optional): The trade data as a dictionary. Defaults to an empty dictionary.

        Returns:
            int: The new length of the list after the push operation.
        """
        # Create a Redis key using the exchange and symbol
        redis_key = f"trades:{exchange}:{symbol}"
        return self.conn.rpush(redis_key, json.dumps(trade))

    def push_my_trades_list(self, uid: str, exchange: str, trade: Dict = {}) -> int:
        """
        Push user trade data to a Redis list.

        Args:
            symbol (str): The trading symbol for the asset pair.
            exchange (str): The name of the exchange where the trade occurred.
            trade (dict, optional): The trade data as a dictionary. Defaults to an empty dictionary.

        Returns:
            int: The new length of the list after the push operation.
        """
        # Create a Redis key using the exchange and symbol
        redis_key = f"user_trades:{uid}:{exchange}"
        return self.conn.rpush(redis_key, json.dumps(trade))

    def pop_my_trade(self, uid: str, exchange: str) -> TradeStruct:
        """
        Pop the next trade from the user's trade queue for a specific exchange.

        Args:
            uid (str): The user ID.
            exchange (str): The name of the exchange.

        Returns:
            TradeStruct: A TradeStruct instance representing the popped trade.

        Raises:
            TimeoutError: If the trade queue is empty and the timeout period has expired.
        """
        redis_key = f"user_trades:{uid}:{exchange}"
        try:
            _, trade_json = self.conn.blpop(redis_key, timeout=0)
            return TradeStruct.from_dict(json.loads(trade_json))
        except redis.exceptions.TimeoutError:
            return None
        except KeyboardInterrupt:
            exit()

    def get_trades_list(self, symbol: str, exchange: str) -> List[TradeStruct]:
        """
        Retrieve a list of TradeStruct instances representing the trades for a specific exchange.

        Args:
            symbol (str): The user ID.
            exchange (str): The name of the exchange.

        Returns:
            List[TradeStruct]: A list of TradeStruct instances representing the user's trades for the exchange.
        """
        redis_key = f"trades:{exchange}:{symbol}"
        trades = self.conn.lrange(redis_key, 0, -1)
        self.conn.delete(redis_key)
        ret_trades = []
        for trade in trades:
            ret_trades.append(TradeStruct.from_dict(json.loads(trade)))
        return ret_trades
