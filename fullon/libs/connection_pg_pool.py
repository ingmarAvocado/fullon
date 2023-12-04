import psycopg2
import sys
from psycopg2.pool import ThreadedConnectionPool
from libs import settings, log

logger = log.fullon_logger(__name__)

_pool_instance: dict = {}
_pool_instance[settings.DBNAME] = None
_pool_instance[settings.DBNAME_OHLCV] = None


def create_connection_pool(min_conn: int = 1,
                           max_conn: int = 20,
                           database: str = settings.DBNAME) -> ThreadedConnectionPool:
    """
    Creates a threaded connection pool for the PostgreSQL database.

    Args:
        min_conn (int, optional): The minimum number of connections in the pool. Defaults to 3.
        max_conn (int, optional): The maximum number of connections in the pool. Defaults to 5.

    Returns:
        ThreadedConnectionPool: A psycopg2 ThreadedConnectionPool instance.

    Raises:
        psycopg2.DatabaseError: If there is a problem connecting to the database.
    """
    global _pool_instance
    if _pool_instance[database] is None:
        try:
            if settings.DBPORT != "":
                _pool_instance[database] = ThreadedConnectionPool(
                    minconn=min_conn, maxconn=max_conn,
                    dbname=database, user=settings.DBUSER, host=settings.DBHOST,
                    port=settings.DBPORT, password=settings.DBPASSWD
                )
            else:
                _pool_instance[database] = ThreadedConnectionPool(
                    minconn=min_conn, maxconn=max_conn,
                    dbname=database, user=settings.DBUSER, host=settings.DBHOST,
                    password=settings.DBPASSWD
                )
        except (psycopg2.DatabaseError) as error:
            logger.error("Error while creating connection pool: " + str(error))
            return {}

    return _pool_instance[database]


def close_connection_pool(pool: ThreadedConnectionPool,
                          database: str = settings.DBNAME) -> None:
    """
    Closes all the connections in the given connection pool.
    Args:
        pool (ThreadedConnectionPool): A psycopg2 ThreadedConnectionPool instance.
    """
    pool.closeall()
    global _pool_instance
    _pool_instance[database] = None
