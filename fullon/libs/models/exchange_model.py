import psycopg2
import psycopg2.extras
import base64
from libs.structs.exchange_struct import ExchangeStruct
from libs import log
from libs.models import user_model as database
from libs import database_helpers as dbhelpers
from typing import Tuple, Dict, Any, Optional, List


logger = log.fullon_logger(__name__)


class Database(database.Database):

    def get_user_exchanges(self, uid: int) -> List[Dict[str, Any]]:
        """
        Get user exchanges.

        Args:
            uid (str): The user ID.

        Returns:
            Optional[List[Dict[str, Any]]]: A list of dictionaries containing the user exchanges, or None if an error occurs.
        """
        sql = ""
        try:
            sql = """SELECT public.cat_exchanges.name as ex_name, public.exchanges.ex_id, public.exchanges.cat_ex_id, public.exchanges.name as ex_named FROM public.cat_exchanges
            INNER JOIN public.exchanges ON public.cat_exchanges.cat_ex_id = public.exchanges.cat_ex_id WHERE public.exchanges.uid='%s'""" % (uid)
            with self.con.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(sql)
                rows = cur.fetchall()
            # Convert each row to a dictionary
            formatted_rows = [dict(row) for row in rows]
            return formatted_rows
        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(self.error_print(error=error,
                                         method="get_user_exchanges",
                                         query=sql))
            return []

    def install_exchange(self, name: str, ohlcv: str = "", params: List[Dict[str, Any]] = []) -> None:
        """
        Install an exchange in the database.

        Args:
            name (str): The name of the exchange.
            ohlcv (str, optional): The ohlcv_view value. Defaults to an empty string.
            params (List[Dict[str, Any]], optional): A list of parameter dictionaries. Defaults to an empty list.

        Raises:
            psycopg2.DatabaseError: If there's an error executing the SQL statements.

        Returns:
            None
        """
        # Encode the ohlcv string if provided
        if ohlcv:
            message_bytes = ohlcv.encode('ascii')
            ohlcv = base64.b64encode(message_bytes).decode('ascii')

        try:
            with self.con.cursor() as cur:
                # Insert the exchange into the cat_exchanges table
                sql = (f"INSERT INTO cat_exchanges(name, ohlcv_view) "
                       f"VALUES (%s, %s) ON CONFLICT (name) DO NOTHING")
                cur.execute(sql, (name, ohlcv))
                self.con.commit()

                # Get the exchange ID
                ex_id = self.get_id("cat_exchanges", "cat_ex_id", "name", name)

                # Insert the exchange parameters into the cat_exchanges_params table
                if params:
                    sql = (f"INSERT INTO cat_exchanges_params (cat_ex_id, name, value) "
                           f"VALUES (%s, %s, %s) ON CONFLICT (cat_ex_id, name) DO NOTHING")
                    cur.executemany(sql, [(ex_id, param['name'], str(param['default'])) for param in params])
                    self.con.commit()

        except psycopg2.DatabaseError as error:
            error_msg = "Error cant install_exchange, postgres says: " + str(error)
            logger.error(error_msg)
            raise
        return None

    # gets the params from an exchage set by a user or default
    def get_exchanges_params(self, cat_ex_id):
        try:
            sql = (
                "select name,value from cat_exchanges_params where cat_ex_id='%s'" %
                (cat_ex_id))
            cur = self.con.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
            cur.close()
            return rows
        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(
                self.error_print(
                    error=error,
                    method="get_exchanges_params",
                    query=sql))
            if cur:
                cur.close()
            return None
        except BaseException:
            raise

    def add_user_exchange(self, exchange: ExchangeStruct) -> int:
        """
        Add a new user exchange.

        Args:
            exchange (dict): A dictionary containing exchange details.

        Returns:
            int: The ID of the added exchange.

        Raises:
            psycopg2.DatabaseError: If an error occurs while inserting the exchange.
        """
        # SQL query to insert the exchange and return the auto-incremented ID
        sql = """INSERT INTO exchanges
                 (uid, cat_ex_id, name, test, active)
                 VALUES (%s, %s, %s, %s, %s)
                 RETURNING ex_id"""  # Assuming 'ex_id' is the auto-increment ID column
        values = (exchange.uid, exchange.cat_ex_id, exchange.name,
                  exchange.test, exchange.active)
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, values)
                ex_id = cur.fetchone()[0]  # Fetch the returned id
                self.con.commit()
            return ex_id  # Return the fetched id
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.warning(
                self.error_print(
                    error=error,
                    method="add_user_exchange",
                    query=sql))
            raise

    def remove_user_exchange(self, ex_id: int) -> bool:
        """
        Remove a user exchange by its ID.

        Args:
            ex_id (int): The ID of the exchange to be removed.

        Returns:
            bool: True if the exchange was successfully deleted, False otherwise.

        Raises:
            psycopg2.DatabaseError: If an error occurs while deleting the exchange.
        """
        # SQL query to delete the exchange
        sql = "DELETE FROM exchanges WHERE ex_id = %s"
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (ex_id,))
                deleted_count = cur.rowcount  # Number of rows affected by the delete operation
                self.con.commit()
                return deleted_count > 0  # True if any row was deleted, False otherwise
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()  # Rollback transaction in case of error
            logger.warning(
                self.error_print(
                    error=error,
                    method="remove_user_exchange",
                    query=sql))
            # Consider whether you want to re-raise the exception or handle it differently
            return False

    def get_exchange_cat_id(self, name: str = "", ex_id: str = "") -> Optional[int]:
        """
        Gets the exchange cat_id from the exchange name or ex_id.

        Args:
            name (Optional[str], optional): The exchange name. Defaults to None.
            ex_id (Optional[str], optional): The exchange ID. Defaults to None.

        Returns:
            Optional[int]: The cat_id if found, otherwise None.
        """
        if name:
            sql = f"SELECT cat_ex_id from cat_exchanges WHERE name = '{name}'"
            param = (name,)
        elif ex_id:
            sql = f"SELECT cat_ex_id from cat_exchanges WHERE ex_id = '{ex_id}'"
            param = (ex_id,)
        else:
            return None

        try:
            with self.con.cursor() as cur:
                cur.execute(sql, param)
                row = cur.fetchone()
                return row[0] if row else None
        except (Exception, psycopg2.DatabaseError) as error:
            logger.warning(self.error_print(error=error, method="get_exchange_cat_id", query=sql))
            return None

    def get_cat_exchanges(self,
                          exchange: Optional[str] = "",
                          page: int = 1,
                          page_size: int = 10,
                          all: bool = False) -> List[Tuple]:
        """
        Get the exchange IDs from the cat_exchanges table.

        Args:
            exchange (Optional[str], optional): The exchange name. If provided, filters the results by exchange. Defaults to "".
            page (int, optional): The page number for pagination. Defaults to 1.
            page_size (int, optional): The number of results per page for pagination. Defaults to 10.
            all (bool, optional): If True, retrieves all results without pagination. Defaults to False.

        Returns:
            Optional[List[Tuple]]: A list of tuples containing the exchange information, or None if an error occurs.
        """
        sql = ''
        try:
            if exchange != "":
                sql = "SELECT * FROM cat_exchanges WHERE name = %s"
                params = (exchange,)
            else:
                sql = "SELECT * FROM cat_exchanges"
                params = ()
            # Add pagination to the query if the 'all' parameter is False
            if not all:
                start = (page - 1) * page_size
                sql += " ORDER BY name LIMIT %s OFFSET %s"
                params += (page_size, start)
            with self.con.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
            return rows
        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(self.error_print(error=error,
                                         method="get_cat_exchanges",
                                         query=sql))
            return [('error',)]

    #gets exchange cat_id form exchange name
    def get_exchange_id(self, exchange_name, uid):
        sql = f"SELECT ex_id from exchanges where name='{exchange_name}' and uid = '{uid}'"
        try:
            cur = self.con.cursor()
            cur.execute(sql)
            row =  cur.fetchone()
            cur.close()
            return row[0]
        except (Exception, psycopg2.DatabaseError) as error:
            logger.warning(self.error_print(error = error, method = "get_exchange_id", query = sql))
            return None

    def get_exchange(self,
                     ex_id: Optional[str] = None,
                     user_id: Optional[str] = None) -> List[ExchangeStruct]:
        """
        Retrieve exchanges based on the input parameters.

        Args:
            ex_id (Optional[str]): The exchange ID.
            user_id (Optional[str]): User ID for filtering exchanges.

        Returns:
            List[ExchangeStruct]: A list of 'ExchangeStruct' objects.
        """
        sql = """SELECT DISTINCT public.cat_exchanges.name as cat_name,
                       public.exchanges.name,
                       public.exchanges.ex_id,
                       public.exchanges.uid,
                       public.exchanges.test,
                       public.exchanges.cat_ex_id
                FROM public.cat_exchanges
                INNER JOIN public.exchanges
                ON public.cat_exchanges.cat_ex_id = public.exchanges.cat_ex_id
                WHERE public.exchanges.active=True"""
        params = []
        if ex_id:
            sql += " AND public.exchanges.ex_id=%s"
            params.append(ex_id)
        if user_id:
            sql += " AND public.exchanges.uid=%s"
            params.append(user_id)
        try:
            with self.con.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                rows = []
                cur.execute(sql, params)
                for row in cur.fetchall():
                    exchange = ExchangeStruct(**row)
                    rows.append(exchange)
            return rows
        except (Exception, psycopg2.DatabaseError) as error:
            logger.warning(self.error_print(
                error=error, method="get_exchange", query=sql))
            return []

    def get_exchange_symbols(self, cat_ex_id: str) -> List[Tuple[str]]:
        """Gets exchange symbols ready to be loaded to the bot.

        Args:
            cat_ex_id (str): The category exchange ID.

        Returns:
            List[Tuple[str]]: A list of tuples, each containing a symbol.
        """
        if not cat_ex_id:
            return []
        try:
            sql = f"""SELECT symbol
                      FROM SYMBOLS
                      WHERE cat_ex_id = %s"""
            cur = self.con.cursor()
            cur.execute(sql, (cat_ex_id,))
            rows = []
            for row in cur.fetchall():
                rows.append(dbhelpers.reg(cur, row))
            cur.close()
            return rows
        except (Exception, psycopg2.DatabaseError) as error:
            logger.warning(self.error_print(error=error, method="get_exchange_symbols", query=sql))
            return []
