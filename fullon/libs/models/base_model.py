import sys
from typing import Optional
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import time
from libs import settings, log, cache
from libs.connection_pg_pool import create_connection_pool, close_all_database_pools

logger = log.fullon_logger(__name__)


class Database():

    pool: Optional[ThreadedConnectionPool]
    _max_conn: int

    def __init__(self, max_conn: int = settings.DBPOOLSIZE):
        self._max_conn = max_conn
        self.get_connection(max_conn=max_conn)
        self.cache = cache.Cache()
        return None

    def __del__(self):
        self.endthis()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.endthis()

    def endthis(self):
        try:
            self.pool.putconn(self.con)
            del self.pool
            del self.cache
            del self.con
        except AttributeError:
            pass
        except psycopg2.pool.PoolError:
            logger.error("Error returning connection to pool")
            pass

    def reset_connection_pool(self):
        """
        Now some times due to some raise errors my code needs
        to reset the connection pool.

        Help with the the reseting here

        """
        close_all_database_pools()
        self.get_connection(max_conn=self._max_conn)

    @staticmethod
    def is_connection_valid(conn):
        """
        Check if the database connection is open and valid.
        """
        try:
            # Use a simple query to test the connection
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return True
        except (psycopg2.DatabaseError, psycopg2.OperationalError):
            # If there's any error, the connection is not valid
            return False

    # Usage in get_connection method
    def get_connection(self, max_conn: int, retries: int = 3, delay: int = 1):
        self.pool = create_connection_pool(max_conn=max_conn)
        self.con = None
        for _ in range(retries):
            try:
                temp_con = self.pool.getconn()
                if self.is_connection_valid(temp_con):
                    self.con = temp_con
                    break
                else:
                    self.pool.putconn(temp_con, close=True)
            except psycopg2.pool.PoolError:
                time.sleep(delay)  # Wait before retrying
        if self.con is None:
            # Handle the case where a valid connection could not be obtained
            logger.error("Failed to obtain a valid database connection after retries")
            raise Exception("Database connection failed")  # Or another appropriate action

    def error_print(self, error, method, query):
        error = "Error: " + str(error)
        error = error + "\nMethod "+method
        error = error + "\nQuery " +query
        return error

    def create_uuid_extension(self):
        sql = 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'
        try:
            cur = self.con.cursor()
            cur.execute(sql)
            cur.close()
        except:
            raise
        return True

    #gets exchanges read to be loaded to the bot
    def generate_uuid(self):
        sql="select uuid_generate_v4()"
        cur = self.con.cursor()
        try:
            cur.execute(sql)
            row = cur.fetchone()
            cur.close()
            return row[0] if row else  False
        except (Exception, psycopg2.DatabaseError) as error:
            logger.warning(self.error_print(error = error, method = "generate_uuid", query = sql))
            sys.exit()

    #gets an id from a table, probided a table a return field a validating field and the value of the validating field
    def get_id(self, table, ret_field, field,name):
        try:
            sql=("SELECT "+ret_field+" from "+table+" where "+field+"='"+name+"'")
            cur = self.con.cursor()
            cur.execute(sql)
            row =  cur.fetchone()
            cur.close()
            return row[0]
        except (Exception, psycopg2.DatabaseError) as error:
            error="Error cant get_id, postgres says: " +str(error)
            logger.info(error)
            raise
        return None
