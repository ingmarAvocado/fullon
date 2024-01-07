from typing import List, Optional, Union, Tuple, Any
import psycopg2
from psycopg2.extensions import AsIs, ISOLATION_LEVEL_AUTOCOMMIT, ISOLATION_LEVEL_DEFAULT
from psycopg2.pool import PoolError
from psycopg2 import OperationalError
import arrow
import time
from libs import settings, log
from libs import database_helpers as dbhelpers
from libs.connection_pg_pool import create_connection_pool, close_all_database_pools
from libs.structs.trade_struct import TradeStruct
from datetime import datetime


logger = log.fullon_logger(__name__)
_max_conn: int


class Database:

    def __init__(self, exchange: str, symbol: str, max_conn: int = settings.DBPOOLSIZE, simul: bool = False):
        self._max_conn = max_conn
        self.exchange = exchange
        symbol = exchange + "_" + symbol.replace("/", "_")
        symbol = symbol.replace(":", "_")
        self.schema = symbol.replace("-", "_")
        self.get_connection(max_conn=max_conn)

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
            del self.con
        except AttributeError:
            pass
        except PoolError as error:
            logger.error(str(error))

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

    def get_connection(self, max_conn: int, retries: int = 60, delay: int = 1) -> None:
        """
        Attempt to obtain a connection from the pool, with retries.

        :param retries: The number of retry attempts to make.
        :param delay: The delay between retry attempts in seconds.
        :return: The connection object if successful, or None if all attempts fail.
        """
        self.pool = create_connection_pool(min_conn=1,
                                           max_conn=max_conn,
                                           database=settings.DBNAME_OHLCV)
        while retries > 0:
            try:
                temp_con = self.pool.getconn()
                if self.is_connection_valid(temp_con):
                    self.con = temp_con
                    break
                else:
                    self.pool.putconn(temp_con, close=True)
            except (PoolError, OperationalError) as error:
                logger.error(f"Connection attempt failed: {error}")
                time.sleep(delay)  # Wait for a while before retrying
                retries -= 1  # Decrement the retry counter

        if retries == 0:
            logger.error("All connection attempts failed.")
            # Handle the situation where connection could not be established
            # For example, raise an exception or return a specific value

    def fetch_ohlcv(self,
                    table: str,
                    compression: int,
                    period: str,
                    fromdate: datetime,
                    todate: datetime) -> List[Any]:
        """
        Fetches OHLCV data from a PostgreSQL database.

        Args:
            table (str): The name of the table to fetch data from.
            compression (int): The compression factor for the time buckets.
            period (str): The period  for the time buckets. minutes, days, etc
            fromdate (str): The starting date for the data range (inclusive), in 'YYYY-MM-DD' format.
            todate (str): The ending date for the data range (inclusive), in 'YYYY-MM-DD' format.

        Returns:
            A list of tuples representing the OHLCV data. Each tuple contains:
            - The timestamp for the time bucket.
            - The opening price for the time bucket.
            - The highest price for the time bucket.
            - The lowest price for the time bucket.
            - The closing price for the time bucket.
            - The total trading volume for the time bucket.
        """
        # Determine column names based on table type
        if "trades" in table:
            open_col, high_col, low_col, close_col, vol_col = [
                "price", "price", "price", "price", "volume"]
        else:
            open_col, high_col, low_col, close_col, vol_col = [
                "open", "high", "low", "close", "vol"]

        # Construct SQL query
        sql = f"""
            SELECT time_bucket_gapfill('{compression} {period}', timestamp) AS ts,
            LOCF(FIRST({open_col}, "timestamp")) AS open,
            LOCF(MAX({high_col})) AS high,
            LOCF(MIN({low_col})) AS low,
            LOCF(LAST({close_col}, "timestamp")) AS close,
            COALESCE(SUM({vol_col}), 0) AS vol
            FROM {table}
            WHERE timestamp BETWEEN '{fromdate}' AND '{todate}'
            GROUP BY ts
            ORDER BY ts ASC
        """
        # Execute query and return results
        try:
            with self.con.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
            # If any of the initial rows are empty, fetch data from one hour before the fromdate.
            for i in range(len(rows)):
                if any(v is None for v in rows[i]):
                    fromdate_new = arrow.get(fromdate).shift(hours=-1).format('YYYY-MM-DD HH:mm:ss')
                    todate_new = fromdate
                    rows_new = self.fetch_ohlcv(table, compression, period, fromdate_new, todate_new)
                    # Use the last row of the new data to fill the current empty row of the original data.
                    if rows_new:
                        rows[i] = (rows[i][0],) + rows_new[-1][1:]
                    else:
                        break  # Break the loop once a non-empty row is encountered
            return rows
        except psycopg2.DatabaseError as error:
            raise ValueError(f"Failed to fetch OHLCV data with query: {sql}")

    def install_timescale(self):
        cur = self.con.cursor()
        try:
            logger.info("Installing timescaledb....")
            sql = 'CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;'
            cur.execute(sql)
            self.con.commit()
            del (cur)
            logger.info("timescaledb extension created")
            return True
        except (Exception) as error:
            logger.info(self.error_print(error=error, method="install_timescale_2", query=sql))
            del (cur)
        cur = self.con.cursor()
        try:
            sql = 'ALTER EXTENSION timescaledb UPDATE'
            cur.execute(sql)
            self.con.commit()
            logger.info("timescaledb updated")
            del (cur)
            return True
        except (Exception) as error:
            logger.info(self.error_print(error=error, method="install_timescale_1", query=sql))
            self.con.rollback()
            del (cur)

        return None
        # need to install timescaledb tools?

    def install_timescale_tools(self):
        return None
        cur = self.con.cursor()
        try:
            logger.info("\nInstalling timescaled tools....")
            sql = 'CREATE EXTENSION IF NOT EXISTS timescaledb_toolkit CASCADE;'
            cur.execute(sql)
            self.con.commit()
            del (cur)
            logger.info("timescaledb_tools extension created")
            return True
        except (Exception) as error:
            logger.info(
                self.error_print(
                    error=error,
                    method="install_timescale_tools_2",
                    query=sql))
            del (cur)
        cur = self.con.cursor()
        try:
            sql = 'ALTER EXTENSION timescaledb_toolkit UPDATE'
            cur.execute(sql)
            self.con.commit()
            logger.info("timescaledb_tools updated")
            del (cur)
            return True
        except (Exception) as error:
            logger.info(
                self.error_print(
                    error=error,
                    method="install_timescale_tools_1",
                    query=sql))
            self.con.rollback()
            del (cur)
        return None

    def error_print(self,  error: Exception, method: str, query: str) -> str:
        """Prepares error message.

        Args:
            error (Exception): The error occurred.
            method (str): The method in which the error occurred.
            query (str): The SQL query during which the error occurred.

        Returns:
            str
        """
        strerror = "Error: " + str(error)
        strerror = strerror + "\nMethod " + method
        strerror = strerror + "\nQuery " + query
        return strerror

    def set_symbol(self, symbol):
        symbol = self.exchange + "_" + symbol.replace("/", "_")
        symbol = symbol.replace(":", "_")
        self.schema = symbol.replace("-", "_")
        return None

    def install_schema(self, ohlcv):
        if not self.table_exists():
            self.make_schema()
            self.make_trade_table()
            self.make_candle_table(ohlcv=ohlcv)

    def table_used(self, table='trades'):
        try:
            cur = self.con.cursor()
            # sql = f"select exists(select * from information_schema.tables where table_schema = '{self.schema.lower()}' and table_name='{table}')"
            sql = f"SELECT COUNT(*) FROM {self.schema.lower()}.trades"
            cur.execute(sql)
            r = cur.fetchone()[0]
            cur.close()
            del (cur)
            return True if r > 0 else False
        except (Exception, psycopg2.DatabaseError) as error:
            cur.close()
            del (cur)
            (f"Cant execute query {sql}")
            raise
        return False

    def table_exists(self, table: str = 'trades', schema: str = "") -> bool:
        """Checks if the given table exists.

        Args:
            table (str): Name of the table to check.

        Returns:
            bool: True if the table exists, False otherwise.
        """
        if not schema:
            schema = self.schema
        try:
            cur = self.con.cursor()
            sql = f"select exists(select * from information_schema.tables where table_schema = '{schema.lower()}' and table_name='{table.lower()}')"
            cur.execute(sql)
            r = cur.fetchone()[0]
            cur.close()
            del (cur)
            return r
        except (Exception, psycopg2.DatabaseError) as error:
            cur.close()
            del (cur)
            raise DatabaseError(f"Cant execute query {sql}")
        except BaseException:
            raise
        return False

    def delete_schema(self):
        try:
            sql = "DROP SCHEMA %s CASCADE " % (self.schema)
            with self.con.cursor() as cur:
                cur.execute(sql)
                self.con.commit()
                logger.info("Schema dropped")
            return True
        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(str(error))
        return False

    def delete_test_view(self, view_name):
        try:
            sql = f"DROP MATERIALIZED VIEW {view_name} CASCADE"
            cur = self.con.cursor()
            cur.execute(sql)
            cur.close()
            self.con.commit()
            logger.info("Test materialized view deleted")
            return True
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            cur.close()
            error = "Error cant delete_test_view, postgres says: " + str(error)
            logger.info(self.error_print(error=error, method="delete_test_view", query=sql))

            logger.info(error)
        return False

    def save_symbol_trades(self, data: List[TradeStruct]) -> None:
        """
        Save all trades from exchanges into a trade table.

        Args:
            data (List[Dict[str, Union[str, float]]]): List of trade data dictionaries.
            symbol (Optional[str], optional): Symbol for the trade table. Defaults to None.

        Returns:
            None
        """

        table = self.schema

        sql = """
        INSERT INTO %s.trades (timestamp, price, volume, side, type, ord)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (timestamp) DO NOTHING;
        """

        prepared_data = [(line.time, line.price, line.volume, line.side, line.order_type, line.ex_trade_id)
                         for line in data]

        try:
            cur = self.con.cursor()
            cur.executemany(sql, ([AsIs(table), *row] for row in prepared_data))
            self.con.commit()
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            cur.close()
            logger.info(self.error_print(error=error, method="save_symbol_trades", query=sql))

    def make_schema(self):
        """
        Creates a new schema in the database if it does not exist.

        Raises:
            psycopg2.DatabaseError: If an error occurs during schema creation.
        """

        sql = f"CREATE SCHEMA IF NOT EXISTS {self.schema}"

        try:
            with self.con.cursor() as cur:
                cur.execute(sql)
                self.con.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.error(self.error_print(error=error, method="make_schema", query=sql))
            raise psycopg2.DatabaseError(f"Error creating schema: {str(error)}") from error

    def make_trade_table(self) -> bool:
        """
        Creates a table for trades in the database if it does not exist.

        Returns:
            bool: True if the table creation is successful, raises an exception otherwise.

        Raises:
            psycopg2.DatabaseError: If an error occurs during the creation of the table.
        """
        sql = f"""
            CREATE TABLE IF NOT EXISTS {self.schema}.trades(
            timestamp  TIMESTAMPTZ NOT NULL PRIMARY KEY,
            price DOUBLE PRECISION NOT NULL,
            volume DOUBLE PRECISION NOT NULL,
            side TEXT NOT NULL,
            type TEXT NOT NULL,
            ord TEXT NULL);
            """
        try:
            with self.con.cursor() as cur:
                cur.execute(sql)
                self.con.commit()
                hypertable_sql = f"SELECT create_hypertable('{self.schema}.trades', 'timestamp')"
                cur.execute(hypertable_sql)
                self.con.commit()

            logger.info("Trade hypertable created")
            return True
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.info(self.error_print(error=error, method="make_trade_table", query=sql))
            raise

    def make_candle_table(self, ohlcv: Optional[str] = None) -> None:
        """
        Creates a table for candles in the database if it does not exist.

        Args:
            ohlcv (Optional[str], default=None): An optional base64 encoded SQL statement to customize table creation.

        Raises:
            psycopg2.DatabaseError: If an error occurs during the creation of the table.
        """
        if ohlcv == "False":
            ohlcv = None

        if ohlcv:
            import base64
            base64_bytes = ohlcv.encode('ascii')
            message_bytes = base64.b64decode(base64_bytes)
            sql = message_bytes.decode('ascii').replace('SCHEMA', self.schema)
        else:
            sql = f"""
                CREATE TABLE IF NOT EXISTS {self.schema}.candles1m (
                    timestamp TIMESTAMPTZ NOT NULL PRIMARY KEY,
                    open DOUBLE PRECISION NOT NULL,
                    high DOUBLE PRECISION NOT NULL,
                    low DOUBLE PRECISION NOT NULL,
                    close DOUBLE PRECISION NOT NULL,
                    vol DOUBLE PRECISION NOT NULL);
            """
        try:
            self.con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            with self.con.cursor() as cur:
                cur.execute(sql)
                self.con.set_isolation_level(ISOLATION_LEVEL_DEFAULT)
                if not ohlcv:
                    hypertable_sql = f"SELECT create_hypertable('{self.schema}.candles1m', 'timestamp')"
                    cur.execute(hypertable_sql)
                    self.con.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.info(self.error_print(error=error, method="make_candle_tables", query=sql))
            raise

    def get_latest_timestamp(self, table: str = "", table2: str = "") -> Optional[str]:
        """
        Retrieves the latest timestamp from the specified table or from the default tables (trades or candles1m).
        Args:
            table (str, optional): Name of the primary table from which to retrieve the latest timestamp.
            table2 (str, optional): Name of the secondary table from which to retrieve the timestamp if `table` is not provided.
        Returns:
            datetime | None: Returns the latest timestamp as a datetime object if found, otherwise None.
        Raises:
            psycopg2.DatabaseError: If an error occurs during the retrieval of the timestamp.
        """
        # Check if table2 is provided and table is not, then query table2
        if table2:
            sql = f'select max(timestamp) from {table2}'
        elif table:
            sql = f'select max(timestamp) from {self.schema}.{table}'
        else:
            table = "trades" if self.table_exists(table='trades') else "candles1m"
            sql = f'select max(timestamp) from {self.schema}.{table}'
        try:
            with self.con.cursor() as cur:
                cur.execute(sql)
                row = cur.fetchone()
                if row:
                    return row[0]
        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(self.error_print(error=error, method="get_latest_timestamp", query=sql))
            raise

    def get_oldest_timestamp(self) -> Optional[str]:
        """Fetches the oldest timestamp from the database.

        The method looks for the oldest timestamp in the "trades" table if it exists,
        otherwise it checks in the "candles1m" table.

        Returns:
            Optional[str]: The oldest timestamp if found, None otherwise.
        """
        values = None
        table = "trades" if self.table_exists(table='trades') else "candles1m"
        sql = f'SELECT MIN(timestamp) FROM {self.schema}.{table}'
        try:
            with self.con.cursor() as cur:
                cur.execute(sql)
                row = cur.fetchone()
                if row:
                    values = row[0]
        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(self.error_print(error=error, method="get_oldest_timestamp", query=sql))
        finally:
            return values

    def delete_before_midnight(self) -> None:
        """
        Deletes all the records in the `candles1m` table before the midnight timestamp of the oldest timestamp present.
        If the oldest timestamp is already at midnight, the function does nothing.

        Returns:
            None

        Raises:
            psycopg2.DatabaseError: If an error occurs during the deletion process.
        """
        # If trades table exists, exit function
        if self.table_exists(table='trades'):
            return

        # Fetch the oldest timestamp
        ts = self.get_oldest_timestamp()
        if not ts:
            return

        # Use arrow to get the datetime representation and to modify it
        d1 = arrow.get(ts)
        hour, minute = d1.hour, d1.minute

        # If timestamp is already midnight, no operation needed
        if hour == 0 and minute == 0:
            return

        # Get the timestamp for the end of the day (1 second before midnight)
        end_of_day = d1.replace(hour=23, minute=59, second=59)
        delete_before = end_of_day.format()

        try:
            with self.con.cursor() as cur:
                sql = "DELETE FROM {}.candles1m WHERE timestamp < %s".format(self.schema)
                cur.execute(sql, (delete_before,))
                self.con.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(self.error_print(error=error, method="delete_before_midnight", query=sql))
            raise

    def fill_candle_table(self, table: str, data: List[Union[dbhelpers.ohlcv, List]]) -> None:
        """
        Fills the candle table with provided OHLCV data.

        Args:
            table (str): The name of the table to fill.
            data (List[Union[dbhelpers.ohlcv, List]]): List of OHLCV data.

        Returns:
            None
        """

        if not self.table_used(table='trades'):
            data.pop()  # Remove the last minute as it is never fully filled.

            sql = """
            INSERT INTO %s (timestamp, open, high, low, close, vol)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp)
            DO UPDATE SET
                timestamp = EXCLUDED.timestamp,
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                vol = EXCLUDED.vol;
            """

            prepared_data = []
            for line in data:
                if isinstance(line, list):
                    line = dbhelpers.ohlcv(t2=line)
                else:
                    line = dbhelpers.ohlcv(t1=line)

                prepared_data.append((line.ts, line.open, line.high, line.low, line.close, line.vol))

            try:
                cur = self.con.cursor()
                cur.executemany(sql, ([AsIs(f"{self.schema}.{table}"), *row] for row in prepared_data))
                self.con.commit()
                cur.close()
            except (Exception, psycopg2.DatabaseError) as error:
                logger.info(self.error_print(error=error, method="fill_candle_table", query=sql))
                sys.exit()

    def vwap(self, compression: int, period: str) -> List[Tuple[str, float]]:
        """
        Fetches VWAP data from a PostgreSQL database.

        Args:
            compression (int): The compression factor for the time buckets.
            period (str): The period size for the time buckets, e.g., 'minutes', 'days'.

        Returns:
            A list of tuples representing the VWAP data. Each tuple contains:
            - The timestamp for the time bucket.
            - The VWAP for the time bucket.
        """
        price_col, vol_col = "price", "volume"
        table = self.schema + ".trades"
        todate = arrow.utcnow()
        match period.lower():
            case 'minutes':
                fromdate = todate.shift(minutes=-compression*8)
            case 'days':
                fromdate = todate.shift(days=-compression*8)
            case _:
                raise ValueError(f"Unsupported period: {period}")

        sql = f"""
            SELECT time_bucket_gapfill('{compression} {period}', timestamp) AS ts,
                   SUM({price_col} * {vol_col}) / SUM({vol_col}) as vwap
            FROM {table}
            WHERE timestamp BETWEEN '{fromdate}' AND '{todate}'
            GROUP BY ts
            ORDER BY ts ASC
        """
        try:
            with self.con.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                return rows
        except psycopg2.DatabaseError as error:
            self.con.rollback()
            raise error

    def twap(self, compression: int, period: str) -> List[Tuple[str, float]]:
        """
        Fetches TWAP data from a PostgreSQL database.

        Args:
            compression (int): The compression factor for the time buckets.
            period (str): The period size for the time buckets, e.g., 'minutes', 'days'.

        Returns:
            A list of tuples representing the TWAP data. Each tuple contains:
            - The timestamp for the time bucket (arrow.Arrow).
            - The TWAP for the time bucket (Decimal).
        """
        price_col = "price"
        table = self.schema + ".trades"
        todate = arrow.utcnow()
        match period.lower():
            case 'minutes':
                fromdate = todate.shift(minutes=-compression*8)
            case 'days':
                fromdate = todate.shift(days=-compression*8)
            case _:
                raise ValueError(f"Unsupported period: {period}")

        sql = f"""
            SELECT time_bucket_gapfill('{compression} {period}', timestamp) AS ts,
                   AVG({price_col}) as twap
            FROM {table}
            WHERE timestamp BETWEEN '{fromdate}' AND '{todate}'
            GROUP BY ts
            ORDER BY ts ASC
        """

        try:
            with self.con.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                return rows
        except (TypeError, psycopg2.DatabaseError) as error:
            logger.error(f"Failed to get TWAP data: {error}")
            return []

    def fetch_event_date(self, event: str, cur_ts: str, limit: str, price: float, pos: int):
        """
        Fetches the timestamp from the trades table based on the provided event type.

        Args:
            event (str): The type of event ('take_profit', 'stop_loss', or 'trailing_stop').
            cur_ts (str): Current timestamp.
            limit (str): Limit timestamp.
            price (float): Price value to compare against.
            pos (int): Position value.

        Returns:
            tuple: The timestamp and price for the specified event or None if not found.  
        Raises:
            ValueError: For unsupported event types.
        """

        # Create conditions for the SQL WHERE clause based on the event type
        if event == "take_profit":
            condition = f"price {'>=' if pos > 0 else '<'} {price}"
        elif event == "stop_loss":
            condition = f"price {'<=' if pos > 0 else '>'} {price}"
        elif event == "trailing_stop":
            # TODO: Add specific condition for this event
            raise ValueError(f"'{event}' not yet supported.")
        else:
            raise ValueError(f"Unsupported event type '{event}'.")

        query = f"""
            SELECT timestamp, price FROM {self.exchange}_{self.symbol}.trades
            WHERE timestamp >= %s AND timestamp <= %s AND {condition}
            ORDER BY timestamp ASC
            LIMIT 1;
        """
        with self.con.cursor() as cur:
            cur.execute(query, (cur_ts, limit))
            result = cur.fetchone()
        return result
