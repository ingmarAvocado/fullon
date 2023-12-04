import sys
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import time
from libs import settings, log, cache
from libs.connection_pg_pool import create_connection_pool

logger = log.fullon_logger(__name__)


class Database():

    pool: ThreadedConnectionPool

    def __init__(self, max_conn: int = settings.DBPOOLSIZE):
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

    def get_connection(self,  max_conn: int, retries: int = 3, delay: int = 1) -> None:
        """
        Attempt to obtain a connection from the pool, with retries.

        :param retries: The number of retry attempts to make.
        :param delay: The delay between retry attempts in seconds.
        :return: The connection object if successful, or None if all attempts fail.
        """
        self.pool = create_connection_pool(max_conn=max_conn)
        self.con = ""
        for _ in range(retries):
            try:
                self.con = self.pool.getconn()
                break
            except psycopg2.pool.PoolError:
                time.sleep(delay)  # Wait for a while before retrying

    def error_print(self, error, method, query):
        error = "Error: " +str(error)
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
