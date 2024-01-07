import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from libs import settings, log
from typing import Optional

logger = log.fullon_logger(__name__)

_pool_instance: dict = {}
_pool_instance[settings.DBNAME] = None
_pool_instance[settings.DBNAME_OHLCV] = None
_min_conn: int
_max_conn: int


def create_connection_pool(min_conn: int = 1,
                           max_conn: int = 20,
                           database: str = settings.DBNAME) -> Optional[ThreadedConnectionPool]:
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
    global _pool_instance, _min_conn, _max_conn
    _min_conn = min_conn
    _max_conn = max_conn
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
            #logger.warning(f"Connection pool created for database {database}")
        except (psycopg2.DatabaseError) as error:
            #logger.error("Error while creating connection pool: " + str(error))
            return
    return _pool_instance[database]


def close_connection_pool(pool: ThreadedConnectionPool,
                          database: str = settings.DBNAME) -> None:
    """
    Closes all the connections in the given connection pool.
    Args:
        pool (ThreadedConnectionPool): A psycopg2 ThreadedConnectionPool instance.
    """
    try:
        pool.closeall()
        logger.warning(f"Connection pool closed for database {database}")
    except Exception as e:
        logger.error(f"Error closing connection pool for database {database}: {e}")
        raise Exception("Closing connection pool failed")


def close_all_database_pools():
    """
    Resets the connection pool by closing all existing connections and reinitializing the pool.
    """
    global _pool_instance, _min_conn, _max_conn
    # Close existing connection pools for each database
    for db_name, pool in _pool_instance.items():
        if pool is not None:
            close_connection_pool(pool, database=db_name)
            _pool_instance[db_name] = None
