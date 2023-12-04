"""
Cache class for managing caching operations with Redis.
The Cache class provides functionality to interact with
a Redis cache server, including creating, updating,
and retrieving cache entries. It also includes utility
methods for testing the connection to the cache server,
preparing the cache, and filtering cache entries based
on timestamps and component types.
"""

import sys
import redis
from libs import settings, log
from typing import List

logger = log.fullon_logger(__name__)

EXCHANGES_DIR = ['kraken', 'kucoin_futures']


class Cache:
    """
    A class for managing caching operations with Redis.
    Attributes:
    db_cache (None): Placeholder for the cache instance.
    conn (redis.Redis): The Redis connection.
    _process_types (List[str]): A list of process types used in the cache.
    _test (bool): Flag indicating whether the class is running in test mode.
    """

    connection_pool = None
    db_cache = None
    conn: redis.Redis
    _test = False

    def __init__(self, reset: bool = False, test: bool = False) -> None:
        """
        Initialize the Cache instance and set up the Redis connection.

        Args:
            test (bool, optional): Set to True to run in test mode. Defaults to False.
        """
        self._test = test
        if Cache.connection_pool is None:
            Cache.connection_pool = self._create_connection_pool()
        self._init_redis()
        if reset:
            pass

    def __del__(self) -> None:
        """Clean up the Redis connection when the Cache instance is deleted."""
        try:
            del self.conn
        except AttributeError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.__del__()

    def _create_connection_pool(self) -> redis.ConnectionPool:
        """
        Create a connection pool for the Redis connection.

        Returns:
            ConnectionPool: A new connection pool instance.
        """
        param = True
        if settings.CACHE_HOST in ["localhost", "127.0.0.1"]:
            param = False

        return redis.ConnectionPool(host=settings.CACHE_HOST,
                                    port=settings.CACHE_PORT,
                                    db=settings.CACHE_DB,
                                    password=settings.CACHE_PASSWORD,
                                    socket_timeout=settings.CACHE_TIMEOUT,
                                    decode_responses=param)

    def _init_redis(self) -> None:
        """
        Initialize the Redis connection based on the settings and connection pool.

        Raises:
            SystemExit: If the connection to the cache server fails.
        """
        self.conn = None
        self.conn = redis.Redis(connection_pool=Cache.connection_pool)

        if not self.test():
            sys.exit("Cant connect to cache server. Exiting...")

    def test(self) -> bool:
        """
        Test the Redis connection by pinging the server.

        Returns:
            bool: True if the connection is successful, False otherwise.
        """
        try:
            self.conn.ping()
            return True
        except redis.exceptions.ConnectionError as error:
            mesg = f"Error, cant ping redis server ({str(error)})"
            logger.error(mesg)
            return False

    def prepare_cache(self) -> None:
        """Prepare the cache by flushing all data."""
        self.conn.flushall()

    def get_keys(self, key: str) -> List:
        """
        Returns all keys that come in string key

        Args:
            key (str): String containing key to return
        """
        return self.conn.keys(key)
