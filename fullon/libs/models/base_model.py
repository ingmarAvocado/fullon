import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import time
from libs import settings, log, cache

logger = log.fullon_logger(__name__)


class Database():
    con = None

    def __init__(self, max_conn=1):
        self.get_connection()
        self.cache = cache.Cache()

    def __del__(self):
        self.endthis()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.endthis()

    def endthis(self):
        try:
            if self.con:
                self.con.close()
                del self.cache
                del self.con
        except AttributeError:
            pass

    def get_connection(self, retries: int = 10, delay: int = 1):
        for _ in range(retries):
            try:
                self.con = psycopg2.connect(
                    dbname=settings.DBNAME,
                    user=settings.DBUSER,
                    password=settings.DBPASSWD,
                    host=settings.DBHOST,  # Assuming pgBouncer is running on this host
                    port=settings.DBPORT  # The port pgBouncer is listening on
                )
                if self.is_connection_valid(self.con):
                    break  # Break the loop if connection is valid
                else:
                    time.sleep(delay)  # Wait before retrying if connection is not valid
            except psycopg2.DatabaseError as e:
                logger.error(f"Failed to obtain a database connection: {e}")
                time.sleep(delay)  # Wait before retrying

        if self.con is None:
            logger.error("Failed to obtain a valid database connection after retries")
            raise Exception("Database connection failed")

    @staticmethod
    def is_connection_valid(conn):
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return True
        except (psycopg2.DatabaseError, psycopg2.OperationalError):
            return False

    def error_print(self, error, method, query):
        error = "Error: " + str(error)
        error = error + "\nMethod "+method
        error = error + "\nQuery " +query
        return error

    #gets an id from a table, probided a table a return field a validating field and the value of the validating field
    def get_id(self, table, ret_field, field, name):
        try:
            sql = ("SELECT "+ret_field+" from "+table+" where "+field+"='"+name+"'")
            cur = self.con.cursor()
            cur.execute(sql)
            row = cur.fetchone()
            cur.close()
            return row[0]
        except (Exception, psycopg2.DatabaseError) as error:
            error = "Error cant get_id, postgres says: " +str(error)
            logger.info(error)
            raise
