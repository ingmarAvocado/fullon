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
import arrow
from libs import log
from libs.caches import account_cache as cache
from libs.structs.order_struct import OrderStruct
from typing import Dict, Any, Optional, List

logger = log.fullon_logger(__name__)

'''
try:
    EXCHANGES_DIR = os.listdir('exchanges/')
except FileNotFoundError:
    EXCHANGES_DIR = os.listdir('fullon/exchanges/')
'''
EXCHANGES_DIR = ['kraken', 'kucoin_futures']


class Cache(cache.Cache):
    """
    A class for managing caching operations with Redis.
    Attributes:
    """

    def push_open_order(self, oid: str, local_oid: str) -> None:
        """
        Push the ID of an open order to a Redis list.

        Args:
            ex_id (str): The exchange ID.
            oid (str): The ID of the open order.

        Returns:
            None
        """
        redis_key = f"new_orders:{local_oid}"
        self.conn.rpush(redis_key, oid)

    def pop_open_order(self, local_oid: str) -> str:
        """
        Pop the next open order from the Redis list.

        Args:
            ex_id (str): The exchange ID.

        Returns:
            str: The ID of the next open order.

        Raises:
            TimeoutError: If the open order queue is empty and the timeout period has expired.
        """
        redis_key = f"new_orders:{local_oid}"
        try:
            _, oid = self.conn.blpop(redis_key, timeout=0)
            del redis_key
            return oid.decode('utf-8')
        except redis.exceptions.TimeoutError:
            raise TimeoutError("Not getting any trade")
        except KeyboardInterrupt:
            return ''

    def save_order_data(self, ex_id: str, oid: str, data: Dict = {}) -> None:
        """
        Save the status of an order to Redis.

        Args:
            ex_id (str): The exchange ID.
            oid (str): The ID of the order.
            status (str): Status of the order

        Returns:
            None

        Raises:
            Exception: If there was an error saving the order status to Redis.
        """
        redis_key = f"order_status:{ex_id}"
        second_key = f"{oid}"
        try:
            existing_data = self.conn.hget(redis_key, second_key)
            if existing_data:
                existing_data = json.loads(existing_data)
                existing_data.update(data)
                data = existing_data
                data['timestamp'] = arrow.utcnow().format('YYYY-MM-DD HH:mm:ss.SSS')
            data['order_id'] = oid
            self.conn.hset(redis_key, second_key, json.dumps(data))

            if data['status'] == "canceled":
                self.conn.expire(redis_key, 60 * 60)  # Expire the key after 1 hour

        except redis.exceptions.RedisError as error:
            logger.exception(f"Error saving order status to Redis: {error}")
            raise Exception("Error saving order status to Redis") from error

    def get_order_status(self,  ex_id: str, oid: str) -> Optional[OrderStruct]:
        """
        Gets the status of an order to Redis.

        Args:
            ex_id (str): The exchange ID.
            oid (str): The ID of the order.

        Returns:
            Dict

        Raises:
            Exception: If there was an error saving the order status to Redis.
        """
        redis_key = f"order_status:{ex_id}"
        second_key = f"{oid}"
        try:
            res = self.conn.hget(redis_key, second_key)
            if res:
                return OrderStruct.from_dict(json.loads(res))
        except AttributeError:
            pass
        return None

    def get_orders(self,  ex_id: str) -> List:
        """
        Save the status of an order to Redis.

        Args:
            ex_id (str): The exchange ID.

        Returns:
            List: list of dictionaries

        Raises:
            Exception: If there was an error saving the order status to Redis.
        """
        redis_key = f"order_status:{ex_id}"
        orders = []
        try:
            _orders = self.conn.hgetall(redis_key)
            if _orders:
                for key, value in _orders.items():
                    order = json.loads(value.decode('utf-8'))  # Decode the bytes to a string before loading as JSON
                    orders.append(OrderStruct.from_dict(order))
        except AttributeError:
            pass
        return orders

    def get_full_accounts(self, ex_id: str) -> Any:
        """
        Returns full account for user in exchange.

        Args:
            uid (str): User ID.
            ex_id (str): Exchange ID.

        Returns:
            list: A list of full accounts.
        """
        try:
            key = f"{ex_id}"
            data = self.conn.hget("accounts", key)
            return json.loads(data)
        except (TypeError, KeyError) as error:
            return None
