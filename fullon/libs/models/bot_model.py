import psycopg2
from psycopg2.extras import DictCursor
import arrow
from libs import log
from libs import database_helpers as dbhelpers
from libs.models import trades_model as database
from typing import List, Dict, Optional, Tuple, Any
import json

logger = log.fullon_logger(__name__)


class Database(database.Database):

    def get_bot_feeds(self, bot_id: Optional[int] = None) -> List[Any]:
        """
        Fetches and returns all the feeds associated with a bot from the database.

        Parameters:
        bot_id (int): An integer representing the unique identifier of the bot.

        Returns:
        list[dict]: A list of dictionaries where each dictionary represents a feed and its associated details.
                    If no data is found or an error occurs, an empty list is returned.
        """
        if bot_id is None:
            return []

        # Corrected SQL query string
        sql = """
            SELECT DISTINCT
                e.ex_id,
                f.period,
                f.compression,
                f.feed_id,
                f.str_id,
                f."order" as feed_order,
                ce.name as exchange_name,
                ce.cat_ex_id,
                s.symbol,
                s.base,
                s.futures,
                s.ex_base
            FROM
                public.feeds f
                INNER JOIN public.strategies str ON f.str_id = str.str_id
                INNER JOIN public.symbols s ON f.symbol_id = s.symbol_id
                INNER JOIN public.exchanges e ON s.cat_ex_id = e.cat_ex_id
                INNER JOIN public.cat_exchanges ce ON e.cat_ex_id = ce.cat_ex_id
            WHERE
                str.bot_id = %s
            ORDER BY
                f."order" ASC
        """
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (bot_id,))
                return [dbhelpers.reg(cur, row) for row in cur.fetchall()]
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(f"Error fetching bot feeds for bot_id {bot_id}: {error}")
            return []

    def edit_feeds(self, str_id: int, feeds: dict) -> bool:
        """
        Updates feeds table for each feed_id in the provided list.

        Args:
            bot_id (int): The new bot id
            feeds dict

        Returns:
            bool: True if the feeds were successfully updated, False otherwise
        """
        try:
            # Open a new cursor
            with self.con.cursor() as cur:

                # SQL query to update the feeds for all feeds in the list
                sql = """
                UPDATE feeds
                SET str_id = %s, symbol_id = %s, period = %s, compression = %s 
                WHERE feed_id = %s
                """

                # Iterate over feeds dictionary
                for feed_data in feeds.values():
                    # Get symbol_id from symbol and exchange
                    symbol_id = self.get_symbol_id(symbol=feed_data['symbol'],
                                                   exchange_name=feed_data['exchange'])
                    # Execute the SQL query for each feed
                    cur.execute(sql, (str_id, symbol_id, feed_data['period'], feed_data['compression'], feed_data['feed_id']))

                # Commit changes
                self.con.commit()
            return True
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(f"Error in edit_feeds: {error}")
            return False

    def add_exchange_to_bot(self, bot_id: str, exchange: dict) -> bool:
        """
        Add an exchange to a bot.

        Args:
            bot_id (str): The bot ID.
            exchange (dict): A dictionary containing the exchange details.

        Returns:
            bool: True if the operation is successful, otherwise an exception is raised.

        Raises:
            psycopg2.DatabaseError: If an error occurs while inserting the exchange.
        """
        exchange_id = exchange['exchange_id']
        sql = f"""INSERT INTO bot_exchanges VALUES('{bot_id}','{exchange_id}')"""
        try:
            with self.con.cursor() as cur:
                cur.execute(sql)
                self.con.commit()
                cur.close()
            return True
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            cur.close() if cur else cur
            logger.error(
                self.error_print(
                    error=error,
                    method="add_bot",
                    query=sql))
            return False

    def get_last_bot_log(self, bot_id, last_candle, feed_num):
        sql = f"SELECT message FROM  bot_log  where bot_id='{bot_id}' and feed_num = {feed_num} and timestamp > '{last_candle}' order by timestamp desc limit 1" 
        #print(sql)
        try:
            cur = self.con.cursor()
            cur.execute(sql)
            row = cur.fetchone()
            cur.close()
            if row:
                return row[0]
            else:
                return ""
        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(self.error_print(error=error, method="get_last_bot_log", query = sql))
            raise
        return None

    def get_last_actions(self, symbol: str, ex_id: str) -> List:
        """
        Retrieves the last 10 actions for a given user, symbol, and exchange ID.
        Parameters:
        symbol (str): The trading symbol.
        ex_id (str): The exchange ID.
        Returns:
        List[Tuple]: A list of tuples, each containing the bot ID, feed number, timestamp, and symbol.
        """
        sql = '''
            SELECT
                bot_log.bot_id,
                bot_log.feed_num,
                bot_log.symbol,
                bot_log.position,
                bot_log.timestamp AS log_timestamp
            FROM
                bot_log
            WHERE
                bot_log.ex_id = %s
                AND bot_log.symbol = %s
                AND bot_log.message LIKE '%%created%%'
            ORDER BY
                LOG_TIMESTAMP ASC
            LIMIT 20;
        '''
        rows = []
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (ex_id, symbol))
                rows = [dbhelpers.reg(cur, row) for row in cur.fetchall()]
        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(self.error_print(error=error, method="get_last_actions", query=sql))
            raise
        return rows

    def save_bot_log(self, bot_id: int, message: str, position: str, feed_num: int, ex_id: str, symbol: str) -> Optional[bool]:
        """
        Save a log message for the bot in the database.

        :param bot_id: The ID of the bot.
        :param message: The log message to save.
        :param position: The position (Decimal).
        :param feed_num: The feed number associated with the log.
        :param ex_id: The exchange ID associated with the log.
        :param symbol: The symbol associated with the log.
        :return: True if the log was saved successfully, None otherwise.
        :raises Exception: If there is an issue executing the database operation.
        """
        sql = "INSERT INTO bot_log (bot_id, feed_num, ex_id, position, symbol, message, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        timestamp = arrow.utcnow().format()
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (bot_id,
                                  feed_num,
                                  ex_id,
                                  position,
                                  symbol,
                                  message.lower(),
                                  timestamp))
                self.con.commit()
            return True
        except psycopg2.DatabaseError:
            # Handle or log the error as needed
            raise

    def get_trading_currency(self, bot_id, ex_id, symbol):
        sql = f"""SELECT symbols.base
                FROM bots
                INNER JOIN bot_exchanges  ON bots.bot_id = bot_exchanges.bot_id
                INNER JOIN symbols
                ON bot_exchanges.symbol_id = symbols.symbol_id
                WHERE bots.bot_id = '{bot_id}' and bot_exchanges.ex_id = '{ex_id}' and symbols.symbol = '{symbol}'
                """
        try:
            cur = self.con.cursor()
            cur.execute(sql)
            row = cur.fetchone()
            cur.close()
            if row:
                return row[0]
            else:
                return []
        except (Exception, psycopg2.DatabaseError) as error:
            error="Error cant get_currency postgres says: " +str(error)
            logger.info(error)
            raise

    def add_bot(self, bot: dict) -> int:
        """
        Add a bot to the database.

        Args:
            bot (dict): A dictionary containing the bot details.

        Returns:
            int: The bot ID if the operation is successful, otherwise an exception is raised.

        Raises:
            psycopg2.DatabaseError: If an error occurs while inserting the bot.
        """
        insert_sql = "INSERT INTO bots (uid, name, dry_run, active) VALUES (%s, %s, %s, %s) RETURNING bot_id"
        try:
            with self.con.cursor() as cur:
                uid = bot['user']
                cur.execute(insert_sql, (uid, bot['name'], bot['dry_run'], bot['active']))
                bot_id = cur.fetchone()[0]
                self.con.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            if cur:
                cur.close()
            if 'not-null' in str(error):
                error = "Some of the parameters of the Bot are wrong, such as the exchange or missing strategy.\n" + str(error)
            logger.warning(self.error_print(error=error,
                                            method="add_bot",
                                            query=insert_sql,),)
            raise
        return bot_id

    def delete_bot(self, bot_id: str) -> bool:
        """
        Delete bot

        Args:
            bot_id (str): The bot ID.

        Returns:
            bool: True if the operation is successful, otherwise an exception is raised.

        Raises:
            psycopg2.DatabaseError: If an error occurs while inserting the exchange.
        """
        sql = "delete from bots where bot_id = %s"
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (bot_id,))
                self.con.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.warning(self.error_print(error=error,
                                            method="add_bot",
                                            query=sql))
            return False
        return True

    def get_bot_timestamp(self, bot_id):
        sql = """SELECT timestamp from bots where bot_id='%s'""" % (bot_id)
        try:
            cur = self.con.cursor()
            cur.execute(sql)
            rows = []
            for row in cur.fetchall():
                rows.append(dbhelpers.reg(cur, row))
            cur.close()
            return rows[0].timestamp
        except (Exception, psycopg2.DatabaseError) as error:
            logger.warning(
                self.error_print(
                    error=error,
                    method="get_bot_timestamp",
                    query=sql))
            sys.exit()

    def edit_bot(self, bot):
        """
        Edits the specified bot in the database.

        The 'bot' parameter is expected to be a dictionary where the keys are the field names in
        the 'bots' table and their corresponding values are the new values to be updated in
        the database for the given bot_id.

        Parameters
        ----------
        bot : dict
            The bot to be edited with its new values. The 'bot_id' key-value pair is mandatory.

        Returns
        -------
        bool
            True if the bot was successfully edited, False otherwise.

        """
        # Extract bot_id from the bot dict
        bot_id = bot.pop('bot_id')
        _ = bot.pop('timestamp', None)
        # Prepare SQL query
        sql = "UPDATE bots SET " + ", ".join(f"{key} = %s" for key in bot.keys()) + " WHERE bot_id = %s"

        # Prepare values
        values = list(bot.values()) + [bot_id]

        try:
            with self.con.cursor() as cur:
                cur.execute(sql, values)
                self.con.commit()
                return True
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(f"Error editing bot: {error}")
            return False

    def get_bot_params(self, bot_id: int) -> List[Dict]:
        """
        Fetches and returns details of all strategies associated with a bot from the database.
        The details include the bot's information, its strategies, and various parameters for each strategy.

        Args:
            bot_id (int): The ID of the bot.

        Returns:
            List[Dict]: A list of dictionaries, each containing the details of each strategy associated with the bot.
        """
        sql = """
            SELECT
                b.bot_id,
                b.dry_run,
                b.active,
                b.uid,
                s.str_id,
                st.name as strategy,
                s.take_profit,
                s.stop_loss,
                s.trailing_stop,
                s.timeout,
                s.leverage,
                s.size_pct,
                s.size,
                s.size_currency,
                s.pre_load_bars
            FROM
                public.bots b
                INNER JOIN public.strategies s ON b.bot_id = s.bot_id
                INNER JOIN public.cat_strategies st ON s.cat_str_id = st.cat_str_id -- Use the aliases here
            WHERE
                b.bot_id = %s
            ORDER BY
                s.str_id
        """
        try:
            with self.con.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(sql, (bot_id,))
                results = cur.fetchall()
                if not results:
                    logger.warning(f"No strategies found for bot_id: {bot_id}")
                    return []
                # Convert each row to a dictionary and collect in a list
                return [dict(row) for row in results]

        except psycopg2.DatabaseError as error:
            logger.error(f"Database error in get_bot_params: {error}")
            return []

    def get_bot_list(self, uid: Optional[str] = None, bot_id: Optional[str] = None, active: bool = False) -> Optional[List[Dict[str, str]]]:
        """
        Fetches bot list from the database.

        Args:
            uid: User ID.
            bot_id: Bot ID.
            active: Fetch active bots only.

        Returns:
            A list of dictionaries containing bot details or None if an error occurred.
        """
        cur: Optional[PgCursor] = None
        try:
            with self.con.cursor() as cur:
                if uid:
                    sql = "SELECT * FROM bots WHERE uid = %s ORDER BY bot_id"
                    cur.execute(sql, (uid,))
                elif bot_id:
                    sql = "SELECT * FROM bots WHERE bot_id = %s ORDER BY bot_id"
                    cur.execute(sql, (bot_id,))
                elif active:
                    sql = "SELECT * FROM bots WHERE active = 't' ORDER BY bot_id"
                    cur.execute(sql)
                else:
                    sql = "SELECT * FROM bots ORDER BY bot_id"
                    cur.execute(sql)

                rows = [dbhelpers.reg(cur, row) for row in cur.fetchall()]
            return rows
        except (Exception, psycopg2.DatabaseError) as error:
            if "current transaction is aborted" in str(error):
                return None
            logger.info(self.error_print(error=error, method="get_bot_list", query=sql))
        finally:
            if cur is not None:
                cur.close()

    def get_bot_full_list(self,
                          page: int = 1,
                          page_size: int = 10) -> Optional[List[Dict[str, str]]]:
        """
        Fetches a page of bots from the database.

        Args:
            page: The page number to fetch, with the first page being 1.
            page_size: The number of records per page.

        Returns:
            A list of dictionaries containing bot details or None if an error occurred.
        """
        sql = """

            SELECT
                b.bot_id,
                u.mail,
                STRING_AGG(cs.name, ', ') AS strategy,  -- Aggregate strategy names
                b.name,
                b.dry_run,
                b.active,
                b.timestamp
            FROM
                public.bots b
                INNER JOIN public.users u ON b.uid = u.uid
                INNER JOIN public.strategies s ON b.bot_id = s.bot_id
                INNER JOIN public.cat_strategies cs ON s.cat_str_id = cs.cat_str_id
            GROUP BY
                b.bot_id, u.mail, b.name, b.dry_run, b.active, b.timestamp
            ORDER BY
                b.bot_id ASC
            LIMIT %s OFFSET %s
        """
        try:
            with self.con.cursor(cursor_factory=DictCursor) as cur:
                # calculate offset
                offset = (page - 1) * page_size
                cur.execute(sql, (page_size, offset))
                rows = cur.fetchall()
            return [dict(row) for row in rows]
        except (Exception, psycopg2.DatabaseError) as error:
            if "current transaction is aborted" in str(error):
                return []
            logger.error(self.error_print(error=error, method="get_bot_list", query=sql))
        return []

    def get_feed_id(self, symbol_id: str, period: str, compression: str) -> str:
        """
        Retrieve the feed_id for a specific symbol, period and compression from the database.

        Args:
            symbol_id (str): The symbol_id of the feed.
            period (str): The period of the feed.
            compression (str): The compression of the feed.

        Returns:
            str: The feed_id if found, otherwise an empty string.

        Raises:
            psycopg2.DatabaseError: If an error occurs while retrieving the feed_id from the database.
        """
        sql = """
            SELECT feed_id FROM feeds
            WHERE symbol_id = %s AND period = %s AND compression = %s
        """
        data = (symbol_id, period, compression)

        try:
            with self.con.cursor() as cur:
                cur.execute(sql, data)  # Use SQL parameter substitution
                rows = [dbhelpers.reg(cur, row) for row in cur.fetchall()]

            return rows[0].feed_id if rows else ''

        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(self.error_print(error=error, method="get_feed_id", query=sql))
            raise

    def add_feed_to_bot(self, feed: dict) -> bool:
        """
        Add a feed to a strategy.

        Args:
            feed (dict): A dictionary containing feed details.

        Returns:
            bool: True if the operation is successful, otherwise an exception is raised.

        Raises:
            psycopg2.DatabaseError: If an error occurs while inserting the feed.
        """
        sql = """
            INSERT INTO public.feeds (str_id, symbol_id, period, compression, "order")
            VALUES (%s, %s, %s, %s, %s)
        """
        data = (feed['str_id'], feed['symbol_id'], feed['period'], feed['compression'], feed['order'])
        cur = None
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, data)  # Use SQL parameter substitution
                self.con.commit()
                cur.close()
                return True
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.error(
                self.error_print(
                    error=error,
                    method="add_feed_to_bot",
                    query=sql))
            return False

    def save_simulation(self, bot_id: str, name: str, payload: dict) -> None:
        """
        Save a simulation into the database. If a simulation with the same bot_id and name exists,
        the existing simulation is updated.

        Args:
            bot_id (str): The id of the bot.
            name (str): The name of the simulation.
            payload (dict): The simulation payload to be saved as JSON.

        Returns:
            None

        Raises:
            psycopg2.DatabaseError: If an error occurs while saving the simulation into the database.
        """
        sql = """
            INSERT INTO simulations (bot_id, name, json)
            VALUES (%s, %s, %s)
            ON CONFLICT (bot_id, name) 
            DO UPDATE SET json = EXCLUDED.json
        """
        data = (bot_id, name, json.dumps(payload))

        try:
            with self.con.cursor() as cur:
                cur.execute(sql, data)
                self.con.commit()

        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.errr(self.error_print(error=error, method="save_simulation", query=sql))
            raise

    def load_simulations_catalog(self, limit: int = 20, starts_with: str = '', offset: int = 0) -> List[Tuple[str, str]]:
        """
        Retrieve a list of bot_id and names from the simulations in the database, 
        limited to a certain number of rows and optionally filtered by name.

        Args:
            limit (int): The maximum number of rows to return.
            starts_with (str): An optional filter for the simulation names.
            offset (int): The number of rows to skip before starting to return rows.

        Returns:
            List[Tuple[str, str]]: A list of tuples containing bot_id and name.

        Raises:
            psycopg2.DatabaseError: If an error occurs while retrieving simulations from the database.
        """
        sql = """
            SELECT num, name FROM simulations
            WHERE name LIKE %s
            ORDER BY name
            OFFSET %s
            LIMIT %s
        """
        data = (starts_with + '%', offset, limit)  # Use SQL LIKE operator to filter names

        try:
            with self.con.cursor() as cur:
                cur.execute(sql, data)  # Use SQL parameter substitution
                rows = [row for row in cur.fetchall()]

            return rows

        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(self.error_print(error=error, method="load_simulations_catalog", query=sql))
            raise

    def load_simulation(self, num: int) -> list:
        """
        Retrieve json string form simulation.

        Args:
            num (int): Simulation id

        Returns:
            Dict[str, str]: A dict containing simulation parameters

        Raises:
            psycopg2.DatabaseError: If an error occurs while retrieving simulations from the database.
        """
        sql = "SELECT json, name FROM simulations WHERE num = %s"
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (num,))  # Use a tuple for SQL parameter substitution
                row = cur.fetchone()
                if row:
                    return row
                else:
                    return {}

        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(self.error_print(error=error, method="load_simulation", query=sql))
            raise

    def get_dry_margin(self, bot_id: str) -> float:
        """
        Retrieves the sum of ROI from dry_trades for a given bot_id.

        Args:
            bot_id (str): The ID of the bot whose dry margin needs to be retrieved.

        Returns:
            float: The sum of ROI for the given bot_id. Returns 0 if no entry found.
        Raises:
            Exception: If there's an error during the database operation.
        """
        try:
            sql = "SELECT SUM(roi) FROM dry_trades WHERE bot_id=%s"
            with self.con.cursor() as cur:
                cur.execute(sql, (bot_id,))
                row = cur.fetchone()
                return row[0] if row[0] else 0

        except (Exception, psycopg2.DatabaseError) as error:
            error_message = "Error can't get dry margin, postgres says: " + str(error)
            logger.error(error_message)
            raise Exception(error_message) from error
