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

    def push_global_error(self, msg: str, component: str) -> None:
        """
        Push the ID of an open order to a Redis list.

        Args:
            error (str): The error text.
            component (str): Component Error.

        Returns:
            None
        """
        msg = f"{msg}:{component}"
        redis_key = f"global_error"
        self.conn.rpush(redis_key, msg)

    def pop_global_error(self):
        """
        Pop the next global error from the Redis list.

        Returns:
            bool: False if an error was popped successfully, True otherwise.

        Raises:
            TimeoutError: If the global error queue is empty and the timeout period has expired.
        """
        redis_key = "global_error"
        try:
            result = self.conn.blpop(redis_key, timeout=0.5)
            if result is not None:
                _, error = result
                if error:
                    # Handle the error here, for example, log it or process it
                    # Since you mentioned returning False if an error is popped,
                    # you can continue with that logic.
                    return error
            # If result is None, it means the timeout expired without any errors to pop.
        except redis.exceptions.TimeoutError:
            # You might want to handle a timeout specifically if needed.
            pass
        except KeyboardInterrupt:
            # It's not typical to handle KeyboardInterrupt in such functions,
            # unless you have a specific reason to do so.
            pass
        # If the function hasn't returned False by now, it means no error was popped or an exception occurred.
        return False
