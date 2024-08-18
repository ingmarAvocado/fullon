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
from typing import Dict, List, Optional, Union
from os import listdir
import arrow

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

    def push_trade_list(self,
                        symbol: str,
                        exchange: str,
                        trade: Dict = {}) -> int:
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
        symbol = symbol.replace("/", "")
        redis_key = f"trades:{exchange}:{symbol}"
        res = self.conn.rpush(redis_key, json.dumps(trade))
        if self.update_trade_status(key=f"{exchange}"):
            return res
        return 0

    def update_trade_status(self, key: str) -> bool:
        """
        Updates status variable for trades.

        Args:
            key (str): The key to update

        Returns:
            None:
        """
        #try:
        key = f"TRADE:STATUS:{key}"
        value = arrow.utcnow().timestamp()
        try:
            with self.conn.pipeline() as pipe:
                pipe.set(key, value)
                trick = pipe.execute()
                return trick[0]
        except redis.RedisError as error:
            logger.error("update_trade_status error: %s", str(error))
        return False

    def update_user_trade_status(self, key: str, timestamp: Optional[float] = None) -> bool:
        """
        Updates status variable for trades.

        Args:
            key (str): The key to update

        Returns:
            None:
        """
        key = f"USER_TRADE:STATUS:{key}"
        if not timestamp:
            timestamp = arrow.utcnow().timestamp()
        try:
            with self.conn.pipeline() as pipe:
                pipe.set(key, timestamp)
                trick = pipe.execute()
                return trick[0]
        except redis.RedisError as error:
            logger.error("update_trade_status error: %s", str(error))
        return False

    def get_trade_status(self, key: str) -> Union[float, None]:
        """
        Retrieves status variable for trades.

        Args:
            key (str): The key to update

        Returns:
            None:
        """
        try:
            key = f"TRADE:STATUS:{key}"
            value = self.conn.get(key)
            return float(value.decode('utf-8')) if value is not None else None
        except redis.RedisError as error:
            logger.error("get_trade_status error: %s", str(error))
        return None

    def get_all_trade_statuses(self, prefix: str = "TRADE:STATUS") -> dict:
        """
        Retrieves all trade statuses for keys with the given prefix.
        Args:
            prefix (str): The prefix to search for. Defaults to "TRADE:STATUS".
        Returns:
            dict: A dictionary of key-value pairs where key is the Redis key and value is the status timestamp.
        """
        try:
            keys = self.get_trade_status_keys(prefix=prefix)
            if not keys:
                return {}
            # Use pipeline for efficient bulk retrieval
            pipe = self.conn.pipeline()
            for key in keys:
                pipe.get(key)
            values = pipe.execute()
            return {
                key: float(value.decode('utf-8')) if value else None
                for key, value in zip(keys, values)
            }
        except (redis.RedisError, ValueError, AttributeError) as error:
            logger.error(f"get_all_trade_statuses error: {str(error)}")
            return {}

    def get_trade_status_keys(self, prefix: str = "TRADE:STATUS") -> List[str]:
        """
        Retrieves all keys starting with the given prefix.
        Args:
            prefix (str): The prefix to search for. Defaults to "TRADE:STATUS".
        Returns:
            List[str]: A list of keys matching the prefix.
        """
        try:
            keys = []
            cursor = '0'
            while cursor != 0:
                cursor, partial_keys = self.conn.scan(cursor=cursor, match=f"{prefix}*", count=1000)
                keys.extend([key.decode('utf-8') for key in partial_keys])
            return keys
        except redis.RedisError as error:
            logger.error(f"get_trade_status_keys error: {str(error)}")
            return []

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

    def pop_my_trade(self, uid: str, exchange: str) -> Optional[TradeStruct]:
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
        symbol = symbol.replace("/", "")
        redis_key = f"trades:{exchange}:{symbol}"
        trades = self.conn.lrange(redis_key, 0, -1)
        self.conn.delete(redis_key)
        ret_trades = []
        for trade in trades:
            ret_trades.append(TradeStruct.from_dict(json.loads(trade)))
        return ret_trades
