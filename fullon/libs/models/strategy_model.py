from pandas.core import base
import psycopg2
from libs import log
from libs import database_helpers as dbhelpers
from libs.models import exchange_model as database
from libs.structs.strategy_struct import StrategyStruct
from libs.structs.cat_strategy_struct import CatStrategyStruct
from typing import List, Dict, Any, Optional


logger = log.fullon_logger(__name__)


class Database(database.Database):

    def get_base_str_params(self, bot_id: int) -> Optional[List[dict]]:
        """
        Fetches strategy parameters based on provided bot ID and wraps them in a StrategyStruct.

        :param bot_id: Bot ID.
        :return: A list of dictionaries, each containing the strategy ID and its parameters wrapped in a StrategyStruct, if successful. None is returned if an error occurs or no data is found.
        """
        if bot_id is None:
            logger.error("bot_id must not be None")
            return None

        sql = """SELECT
                    s.str_id, s.cat_str_id, cs.name as cat_name, s.take_profit, s.stop_loss,
                    s.trailing_stop, s.timeout, s.size_pct, s.size, s.size_currency, s.leverage,
                    s.pre_load_bars, s.feeds, s.pairs
                 FROM strategies s
                 INNER JOIN cat_strategies cs ON s.cat_str_id = cs.cat_str_id
                 WHERE s.bot_id = %s
              """
        try:
            with self.con.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:  # Use DictCursor for easy dict conversion
                cur.execute(sql, (bot_id,))
                rows = cur.fetchall()
                if rows:
                    return [StrategyStruct.from_dict(row) for row in rows]
                else:
                    return None
        except psycopg2.DatabaseError as error:
            logger.error(
                self.error_print(
                    error=error,
                    method="get_base_str_params",
                    query=sql
                )
            )
            return None

    def get_str_params(self, bot_id: int) -> List[Dict[str, Any]]:
        """
        Gets strategy parameters associated with a given bot_id, dynamically adding parameters as key-value pairs in dictionaries.

        Args:
            bot_id (int): The ID of the bot for which to retrieve strategy parameters.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing a strategy with its ID ('str_id') and
                                   dynamic keys for each parameter name with their corresponding values.
        """
        sql = """
        SELECT sp.str_id, sp.name, sp.value
        FROM strategies_params sp
        INNER JOIN strategies s ON sp.str_id = s.str_id
        WHERE s.bot_id = %s
        """
        try:
            with self.con.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(sql, (bot_id,))
                rows = cur.fetchall()

                strategy_params = {}
                for row in rows:
                    # If the strategy ID hasn't been seen before, initialize a new dictionary for it
                    if row['str_id'] not in strategy_params:
                        strategy_params[row['str_id']] = {'str_id': row['str_id']}
                    # Add or update the parameter in the strategy's dictionary
                    strategy_params[row['str_id']][row['name']] = row['value']

                # Convert the dictionary to a list of its values for the final return
                return list(strategy_params.values())

        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(
                f"Error fetching strategy parameters for bot_id {bot_id}: {error}")
            return []

    def edit_base_strat_params(self, str_id: int, params: dict) -> bool:
        """
        Edits parameters for a given strategy in the database.

        :param bot_id: The ID of the strategy to edit
        :param params: A dictionary where keys correspond to parameter names and values correspond to new parameter values
        :return: True if the operation was successful, False otherwise
        """
        # Build the SQL statement
        sql = "UPDATE strategies SET "
        sql += ", ".join(f"{key} = %s" for key in params.keys())
        sql += " WHERE  str_id = %s"

        # Create a list of values in the same order as in the SQL statement
        values = list(params.values()) + [str_id]

        # Execute the SQL statement
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, values)
                self.con.commit()
            return True
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(f"Error in edit_base_strat_params: {error}")
            return False

    def edit_strat_params(self, str_id: int, params: dict) -> bool:
        """
        Edits parameters for a given strategy in the database.

        :param str_id: The ID of the strategy to edit
        :param params: A dictionary where keys correspond to parameter names and values correspond to new parameter values
        :return: True if the operation was successful, False otherwise
        """

        '''
        here i need to query table params to get the bo_id. help me me out?
        '''
        try:
            with self.con.cursor() as cur:
                for name, value in params.items():
                    # SQL query to update the existing row or insert a new one
                    sql = """
                    INSERT INTO strategies_params (str_id, name, value) VALUES (%s, %s, %s)
                    ON CONFLICT (str_id, name) DO UPDATE SET value = EXCLUDED.value;
                    """
                    cur.execute(sql, (str_id, name, value))
                self.con.commit()
            return True
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(f"Error in edit_strat_params: {error}")
            return False

    def get_bots_strategies(self, cat_str_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get bots that use a cat_strategy

        Args:
            cat_str_name (str): The category strategy name.

        Returns:
            Optional[List[Dict[str, Any]]]: A list of dictionaries containing the bots or None if an error occurs.
        """
        sql = """
                SELECT DISTINCT
                    b.bot_id,
                    b.name,
                    b.uid,
                    u.mail
                FROM
                    public.bots b
                    INNER JOIN public.strategies s ON b.bot_id = s.bot_id
                    INNER JOIN public.cat_strategies cs ON s.cat_str_id = cs.cat_str_id
                    INNER JOIN public.users u ON b.uid = u.uid
                WHERE cs.name = %s
                """
        try:
            with self.con.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(sql, (cat_str_name,))
                strats = []
                for row in cur.fetchall():
                    # Assuming dbhelpers.reg function is available and formats a single row into a structured dictionary
                    strats.append(dbhelpers.reg(cur, row))
            return strats
        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(
                self.error_print(
                    error=error,
                    method="get_strategies_bots",
                    query=sql))
            return None

    def add_bot_strategy(self, strategy: dict) -> Optional[int]:
        """
        Adds a strategy to the database.

        Args:
            strategy (dict): A dictionary containing the strategy details.

        Returns:
            bool: True if success.

        Raises:
            psycopg2.DatabaseError: If an error occurs while inserting the strategy or its parameters.
        """
        defaults = self.get_cat_strategy(cat_str_id=strategy['cat_str_id']).to_dict()
        strategy = {**defaults, **strategy}
        insert_strategy_sql = """
            INSERT INTO strategies (
                bot_id, cat_str_id, take_profit, stop_loss,
                trailing_stop, timeout, leverage, size_pct,
                size, size_currency, pre_load_bars, feeds, pairs
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING str_id
        """
        insert_params_sql = "INSERT INTO strategies_params(str_id, name, value) VALUES(%s, %s, %s)"
        try:
            with self.con.cursor() as cur:
                # Insert strategy and get str_id
                cur.execute(insert_strategy_sql, (
                    strategy.get('bot_id'),
                    strategy['cat_str_id'],
                    strategy.get('take_profit'),
                    strategy.get('stop_loss'),
                    strategy.get('trailing_stop'),
                    strategy.get('timeout'),
                    strategy.get('leverage', 2),  # Fixed typo here from 'levergage' to 'leverage'
                    strategy.get('size_pct', 10),
                    strategy.get('size'),
                    strategy.get('size_currency', 'USD'),
                    strategy.get('pre_load_bars'),
                    strategy.get('feeds'),
                    strategy.get('pairs')
                ))
                str_id = cur.fetchone()[0]  # Assuming RETURNING str_id works as expected
                # Insert parameters for the strategy
                if str_id:
                    params = self.get_cat_strategies_params(cat_str_id=strategy['cat_str_id'])
                    if params:
                        for param in params:
                            cur.execute(insert_params_sql, (str_id, param.name, param.value))
                    # Link the strategy with a bot
                    self.con.commit()
                    return str_id
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.warning(f"Error in add_bot_strategy: {error}")
        return False

    def del_bot_strategy(self, bot_id: int) -> bool:
        """
        Removes strategies associated with a bot from the database based on its bot ID.

        Args:
            bot_id (int): The bot ID whose strategies are to be removed.

        Returns:
            bool: True if the strategies were successfully deleted, False otherwise.

        Raises:
            psycopg2.DatabaseError: If an error occurs while deleting the strategies or its parameters.
        """
        try:
            with self.con.cursor() as cur:
                # Delete strategy parameters for strategies associated with the bot
                cur.execute("""
                    DELETE FROM strategies_params
                    WHERE str_id IN (
                        SELECT str_id FROM strategies WHERE bot_id = %s
                    )
                """, (bot_id,))

                # Delete feeds associated with these strategies
                cur.execute("""
                    DELETE FROM feeds
                    WHERE str_id IN (
                        SELECT str_id FROM strategies WHERE bot_id = %s
                    )
                """, (bot_id,))

                # Delete the strategies themselves
                cur.execute("DELETE FROM strategies WHERE bot_id = %s", (bot_id,))

                self.con.commit()
                return True
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.warning(f"Error in del_bot_strategy: {error}")
            return False

    def install_strategy(self, name: str, base_params: Dict[str, any], params: Dict[str, any] = {}) -> Optional[int]:
        """
        Installs a strategy in the database, including base and additional parameters.

        Args:
            name (str): The name of the strategy.
            base_params (Dict[str, Any]): Essential parameters for the strategy.
            params (Dict[str, Any], optional): Supplementary parameters for the strategy. Defaults to an empty dict.

        Returns:
            Optional[int]: The ID of the installed/updated strategy, or None if the operation failed.

        Raises:
            psycopg2.DatabaseError: If an error occurs during the strategy installation process.
        """
        # Prepare SQL for inserting/updating the base strategy details
        insert_strategy_sql = """
            INSERT INTO cat_strategies (name, take_profit, stop_loss, trailing_stop, timeout, pre_load_bars, feeds, pairs)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
                take_profit = EXCLUDED.take_profit,
                stop_loss = EXCLUDED.stop_loss,
                trailing_stop = EXCLUDED.trailing_stop,
                timeout = EXCLUDED.timeout,
                pre_load_bars = EXCLUDED.pre_load_bars,
                feeds = EXCLUDED.feeds,
                pairs = EXCLUDED.pairs
            RETURNING cat_str_id;
        """
        try:
            with self.con.cursor() as cur:
                # Insert/Update the base strategy and retrieve its ID
                cur.execute(insert_strategy_sql, (
                    name,
                    base_params.get('take_profit'),
                    base_params.get('stop_loss'),
                    base_params.get('trailing_stop'),
                    base_params.get('timeout'),
                    base_params.get('pre_load_bars', 200),
                    base_params.get('feeds', 2),
                    base_params.get('pairs', False),
                ))
                cat_str_id = cur.fetchone()[0]

                # Insert additional parameters, if any
                if params:
                    insert_params_sql = """
                        INSERT INTO cat_strategies_params (cat_str_id, name, value)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (cat_str_id, name) DO NOTHING;
                    """
                    for name, value in params.items():
                        cur.execute(insert_params_sql, (cat_str_id, name, value))

                self.con.commit()
                return cat_str_id
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.exception(f"Failed to install strategy '{name}': {error}")
            return None

    def get_user_strategies(self, uid: str) -> List[Dict[str, str]]:
        """
        Fetches user strategies from the database.

        Args:
            uid: User ID.

        Returns:
            A list of dictionaries containing strategy details or None if an error occurred.
        """
        sql = """
            SELECT
                cs.name AS cat_name,
                s.str_id,
                s.bot_id,
                b.uid
            FROM
                public.strategies s
                INNER JOIN public.cat_strategies cs ON s.cat_str_id = cs.cat_str_id
                INNER JOIN public.bots b ON s.bot_id = b.bot_id
            WHERE b.uid = %s
        """
        try:
            with self.con.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(sql, (uid,))
                rows = cur.fetchall()
                strats = []
                for row in rows:
                    # Assuming that StrategyStruct or similar data mapping handles this row structure
                    strat = StrategyStruct.from_dict(dict(row))
                    strats.append(strat)
            return strats
        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(self.error_print(error=error, method="get_user_strategies", query=sql))
            # Consider handling or logging the error appropriately instead of raising an exception directly
        return []

    def get_cat_strategies(self, page: int = 1, page_size: int = 10, all=False) -> List[Dict[str, str]]:
        """
        Retrieves strategy details from the `cat_strategies` table in the database,
        and returns the results in a paginated format.

        Parameters:
        - page (int): The current page number. Defaults to 1.
        - page_size (int): The number of records to return per page. Defaults to 10.

        Raises:
            psycopg2.DatabaseError: If an error occurs during the database operation.

        Returns:
            List[Dict[str, str]]: A list of strategies for the current page. Each strategy is represented as a dictionary.
        """

        offset = (page - 1) * page_size
        sql = "SELECT * FROM cat_strategies ORDER BY name "
        if not all:
            sql += "LIMIT %s OFFSET %s"
        strats = []
        try:
            with self.con.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(sql, (page_size, offset))
                for row in cur.fetchall():
                    strat = CatStrategyStruct.from_dict(dict(row))
                    strats.append(strat)
        except (Exception, psycopg2.DatabaseError) as error:
            error_msg = self.error_print(error=error, method="get_cat_strategies", query=sql)
            logger.warning(error_msg)
            raise psycopg2.DatabaseError(error_msg) from error
        return strats

    def get_cat_strategies_params(self, cat_str_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves strategy details from the `cat_strategies_params` table in the database.

        Args:
            cat_str_id (str): The id of the strategy.

        Raises:
            psycopg2.DatabaseError: If an error occurs during database operation.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries with strategy parameters.
        """
        sql = "SELECT * FROM cat_strategies_params WHERE cat_str_id = %s"
        rows = []

        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (cat_str_id,))  # Pass the argument as a tuple
                for row in cur.fetchall():
                    rows.append(dbhelpers.reg(cur, row))
        except (Exception, psycopg2.DatabaseError) as error:
            error_msg = self.error_print(error=error, method="get_cat_strategies_params", query=sql)
            logger.warning(error_msg)
            raise psycopg2.DatabaseError(error_msg) from error
        return rows

    def get_cat_str_id(self, name: str) -> str:
        """
        Retrieves strategy id from the `cat_strategies` table in the database based on the strategy name.

        Args:
            name (str): The name of the strategy.

        Raises:
            psycopg2.DatabaseError: If an error occurs during database operation.

        Returns:
            str: The id of the strategy.
        """
        sql = "SELECT cat_str_id FROM cat_strategies WHERE name = %s"
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (name,))  # Pass the argument as a tuple
                cat_str_id = cur.fetchone()
                if cat_str_id is not None:
                    return cat_str_id[0]
        except (Exception, psycopg2.DatabaseError) as error:
            error_msg = self.error_print(error=error, method="get_cat_str_id", query=sql)
            logger.warning(error_msg)
            raise psycopg2.DatabaseError(error_msg) from error
        return ''

    def get_cat_strategy(self, cat_str_id: str) -> Optional[StrategyStruct]:
        """
        Retrieves strategy from the `cat_strategies` table in the database.

        Args:
            cat_str_id (str): The id of the strategy.

        Raises:
            psycopg2.DatabaseError: If an error occurs during database operation.

        Returns:
            Dict[str, Any]: A dictionary with strategy parameters where the key is 'name' and the value is 'value'.
        """
        sql = "SELECT * FROM cat_strategies WHERE cat_str_id = %s"
        try:
            with self.con.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(sql, (cat_str_id,))  # Pass the argument as a tuple
                row = cur.fetchone()
                if row is not None:
                    strat = StrategyStruct.from_dict(dict(row))
                return strat
        except (Exception, psycopg2.DatabaseError) as error:
            error_msg = self.error_print(error=error, method="get_cat_strategy", query=sql)
            logger.warning(error_msg)
        return None

    def del_cat_strategy(self,
                         cat_str_id: Optional[int] = None,
                         cat_str_name: str = '') -> bool:
        """
        Retrieves strategy from the `cat_strategies` table in the database.

        Args:
            cat_str_name (str): The name of the strategy.

        Raises:
            psycopg2.DatabaseError: If an error occurs during database operation.

        Returns:
            bool: True if successful.
        """
        if cat_str_id:
            sql = "DELETE FROM cat_strategies WHERE cat_str_id = %s"
        if cat_str_name:
            sql = "DELETE FROM cat_strategies WHERE name = %s"
        try:
            with self.con.cursor() as cur:
                if cat_str_id:
                    cur.execute(sql, (cat_str_id,))
                else:
                    cur.execute(sql, (cat_str_name,))
                self.con.commit()  # Commit the transaction
                return cur.rowcount > 0  # True if rows were affected
        except psycopg2.DatabaseError as error:
            error_msg = self.error_print(error=error,
                                         method="del_cat_strategy",
                                         query=sql)
            logger.warning(error_msg)
            raise psycopg2.DatabaseError(error_msg) from error
