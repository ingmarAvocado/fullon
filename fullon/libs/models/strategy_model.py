from pandas.core import base
import psycopg2
from libs import log
from libs import database_helpers as dbhelpers
from libs.models import exchange_model as database
from libs.structs.strategy_struct import StrategyStruct
from typing import List, Dict, Any, Optional
import uuid


logger = log.fullon_logger(__name__)


class Database(database.Database):

    def get_base_str_params(self, bot_id: int) -> Optional[dbhelpers.reg]:
        """
        Fetches strategy parameters based on provided strategy ID.

        :param bot_id: Strategy ID
        :return: A dbhelper object of strategy parameters if successful, else None.
        """
        if bot_id is None:
            logger.error("bot_id must not be None")
            return None

        sql = """
        SELECT take_profit, stop_loss, trailing_stop,
               timeout, size_pct, size, size_currency, leverage, pre_load_bars
        FROM strategies
        WHERE bot_id = %s
        """
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (bot_id,))  # use a parameterized query
                row = cur.fetchone()
                self.con.commit()  # commit the transaction
                if row is not None:
                    # assuming dbhelpers.reg returns a dictionary of parameters
                    return dbhelpers.reg(cur, row)
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
        finally:
            self.con.autocommit = True  # return to default transaction handling

    # gets the params from an strategy set by a user
    def get_str_params(self, bot_id: int) -> list:
        """
        gets strategy parameters
        """
        sql = f"select name,value from strategies_params where bot_id='{bot_id}'"
        try:
            with self.con.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                cur.close()
                return rows
        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(
                self.error_print(
                    error=error,
                    method="get_str_params",
                    query=sql))
            return []
        except BaseException:
            raise

    def edit_base_strat_params(self, bot_id: int, params: dict) -> bool:
        """
        Edits parameters for a given strategy in the database.

        :param bot_id: The ID of the strategy to edit
        :param params: A dictionary where keys correspond to parameter names and values correspond to new parameter values
        :return: True if the operation was successful, False otherwise
        """
        # Build the SQL statement
        sql = "UPDATE strategies SET "
        sql += ", ".join(f"{key} = %s" for key in params.keys())
        sql += " WHERE  bot_id = %s"

        # Create a list of values in the same order as in the SQL statement
        values = list(params.values()) + [bot_id]

        # Execute the SQL statement
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, values)
                self.con.commit()

            return True
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(f"Error in edit_base_strat_params: {error}")
            return False

    def edit_strat_params(self, bot_id: int, params: dict) -> bool:
        """
        Edits parameters for a given strategy in the database.

        :param bot_id: The ID of the strategy to edit
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
                    INSERT INTO strategies_params (bot_id, name, value) VALUES (%s, %s, %s)
                    ON CONFLICT (bot_id, name) DO UPDATE SET value = EXCLUDED.value;
                    """
                    cur.execute(sql, (bot_id, name, value))
                self.con.commit()

            return True
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(f"Error in edit_strat_params: {error}")
            return False

    # gets the params from an strategy set by a user
    def get_str_name(self, bot_id: int):
        """
        gets the strategy name
        """
        sql = f"select cat_strategies.name FROM cat_strategies  WHERE  cat_strategies.cat_str_id  =  (SELECT cat_str_id FROM strategies WHERE bot_id = '{bot_id}')"
        try:
            cur = self.con.cursor()
            cur.execute(sql)
            row = cur.fetchone()
            cur.close()
            return row[0]
        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(
                self.error_print(
                    error=error,
                    method="get_str_params",
                    query=sql))
            if cur:
                cur.close()
            return None
        except BaseException:
            raise

    def get_strategies_bots(self, cat_str_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get bots that use a cat_strategy

        Args:
            cat_str_name (int): The cat  strategy name.

        Returns:
            Optional[List[Dict[str, Any]]]: A list of dictionaries containing the bots  or None if an error occurs.
        """
        try:
            sql = """
                    SELECT
                        public.bots.bot_id,
                        public.bots.name,
                        public.bots.uid,
                        public.users.mail
                    FROM
                        public.bots
                        INNER JOIN public.strategies
                         ON public.bots.bot_id = public.strategies.bot_id
                        INNER JOIN public.cat_strategies
                         ON public.strategies.cat_str_id = public.cat_strategies.cat_str_id
                        INNER JOIN public.users
                         ON public.bots.uid = public.users.uid
                    WHERE public.cat_strategies.name = %s
                    """
            strats = []
            with self.con.cursor() as cur:
                cur.execute(sql, (cat_str_name,))
                for row in cur.fetchall():
                    strats.append(dbhelpers.reg(cur, row))
            return strats
        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(
                self.error_print(
                    error=error,
                    method="get_user_strat_params",
                    query=sql))
            return None

    def get_user_strat_params(self, bot_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Get user strategy parameters.

        Args:
            bot_id (int): The strategy ID.

        Returns:
            Optional[List[Dict[str, Any]]]: A list of dictionaries containing the strategy parameters, or None if an error occurs.
        """
        try:
            sql = f"""SELECT public.strategies_params.name as name,
                      public.strategies_params.value as value,
                      public.strategies.uid,
                      public.cat_strategies.name  as str_name
                      FROM public.strategies
                      INNER JOIN public.strategies_params ON public.strategies.bot_id = public.strategies_params.bot_id
                      INNER JOIN public.cat_strategies ON public.strategies.cat_str_id = public.cat_strategies.cat_str_id
                      WHERE public.strategies.bot_id='{bot_id}'"""
            with self.con.cursor() as cur:
                cur.execute(sql)
                rows = []
                for row in cur.fetchall():
                    rows.append(dbhelpers.reg(cur, row))
                cur.close()
            return rows
        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(
                self.error_print(
                    error=error,
                    method="get_user_strat_params",
                    query=sql))
            return None
        except BaseException:
            raise

    def add_params_to_strategy(self, strategy: dict, params: dict) -> bool:
        """
        Add parameters to a strategy.

        Args:
            strategy (dict): A dictionary containing strategy details.
            params (dict): A dictionary containing the parameters to be added to the strategy.

        Returns:
            bool: True if the operation is successful, otherwise an exception is raised.

        Raises:
            psycopg2.DatabaseError: If an error occurs while inserting the parameters.
        """
        sql = ""
        for p in params.items():
            sql = sql + \
                f"""INSERT INTO strategies_params
                    VALUES ((SELECT bot_id FROM strategies
                    WHERE uid = (SELECT UID FROM users WHERE mail='{strategy['user']}')
                    AND name ='{strategy['name']}'),'{p[0]}','{p[1]}');"""
        cur = None
        try:
            cur = self.con.cursor()
            cur.execute(sql)
            self.con.commit()
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            if cur:
                del (cur)
            logger.warning(
                self.error_print(
                    error=error,
                    method="add_params_to_strategy",
                    query=sql))
        return True

    def add_bot_strategy(self, strategy: dict) -> bool:
        """
        Adds a strategy to the database.

        Args:
            strategy (dict): A dictionary containing the strategy details.

        Returns:
            bool: True if success.

        Raises:
            psycopg2.DatabaseError: If an error occurs while inserting the strategy or its parameters.
        """
        defaults = self.get_cat_strategy(cat_str_id=strategy['cat_str_id'])
        strategy = {**defaults, **strategy}
        insert_strategy_sql = """
            INSERT INTO strategies (
                bot_id, cat_str_id, take_profit, stop_loss,
                trailing_stop, timeout, leverage, size_pct, size, size_currency, pre_load_bars
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        insert_params_sql = "INSERT INTO strategies_params(bot_id, name, value) VALUES(%s, %s, %s)"
        try:
            with self.con.cursor() as cur:
                cur.execute(insert_strategy_sql, (

                    strategy['bot_id'],
                    strategy['cat_str_id'],
                    strategy.get('take_profit'),
                    strategy.get('stop_loss'),
                    strategy.get('trailing_stop'),
                    strategy.get('timeout'),
                    strategy.get('levergage', 2),
                    strategy.get('size_pct', 10),
                    strategy.get('size'),
                    strategy.get('size_currency', 'USD'),
                    strategy.get('pre_load_bars')
                ))
                params = self.get_cat_strategies_params(cat_str_id=strategy['cat_str_id'])
                if params:
                    for param in params:
                        cur.execute(insert_params_sql, (strategy['bot_id'], param.name, param.value))
                self.con.commit()
                return True
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.warning(f"Error in add_user_strategy: {error}")
            return False

    def del_bot_strategy(self, bot_id: int) -> bool:
        """
        Removes a strategy from the database based on its strategy ID.

        Args:
            bot_id (int): The strategy ID to be removed.

        Returns:
            bool: True if the strategy was successfully deleted, False otherwise.

        Raises:
            psycopg2.DatabaseError: If an error occurs while deleting the strategy or its parameters.
        """
        delete_strategy_sql = """
            DELETE FROM strategies WHERE bot_id = %s
        """
        delete_params_sql = """
            DELETE FROM strategies_params WHERE bot_id = %s
        """
        try:
            with self.con.cursor() as cur:
                # First, delete any parameters associated with the strategy
                cur.execute(delete_params_sql, (bot_id,))
                deleted_params_count = cur.rowcount
                # Then, delete the strategy itself
                cur.execute(delete_strategy_sql, (bot_id,))
                deleted_strategy_count = cur.rowcount
                self.con.commit()
                # If any rows (either strategy or its parameters) were deleted, return True
                if deleted_params_count > 0 or deleted_strategy_count > 0:
                    return True
                else:
                    return False
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            logger.warning(f"Error in del_bot_strategy: {error}")
            return False

    def install_strategy(self,
                         name: str,
                         base_params: Dict[str, Any],
                         params: Dict[str, Any] = {}) -> None:
        """
        Installs a strategy in the database.

        Args:
            name (str): The name of the strategy.
            params (Dict[str, Any], optional): A dictionary containing the strategy parameters. Defaults to None.

        Raises:
            psycopg2.DatabaseError: If an error occurs during the installation of the strategy.
        """

        if params is None:
            params = {}

        try:
            sql = (
                "INSERT INTO CAT_STRATEGIES(cat_str_id, name, take_profit,\
                    stop_loss, trailing_stop, timeout, pre_load_bars)"
                " VALUES (uuid_generate_v4(), %s, %s, %s, %s, %s, %s) ON CONFLICT (name) DO NOTHING"
            )
            with self.con.cursor() as cur:
                cur.execute(sql, (
                    name,
                    base_params.get('take_profit'),
                    base_params.get('stop_loss'),
                    base_params.get('trailing_stop'),
                    base_params.get('timeout'),
                    base_params.get('pre_load_bars', 200)
                    ))
        except (Exception, psycopg2.DatabaseError) as error:
            raise psycopg2.DatabaseError("Error installing strategy: " + str(error)) from error

        _cat_str_id = self.get_id("cat_strategies", "cat_str_id", "name", name)

        for param_name, param_value in params.items():
            sql = (
                "INSERT INTO cat_strategies_params (cat_str_id, name, value)"
                " VALUES (%s, %s, %s) ON CONFLICT (cat_str_id, name) DO NOTHING"
            )
            try:
                with self.con.cursor() as cur:
                    cur.execute(sql, (_cat_str_id, param_name, param_value))
            except (Exception, psycopg2.DatabaseError) as error:
                raise psycopg2.DatabaseError(
                    "Error installing strategy parameters: " + str(error)) from error

        self.con.commit()

    def get_user_strategies(self, uid: str) -> Optional[List[Dict[str, str]]]:
        """
        Fetches user strategies from the database.

        Args:
            uid: User ID.

        Returns:
            A list of dictionaries containing strategy details or None if an error occurred.
        """
        sql = """
            SELECT
                public.cat_strategies.name AS cat_name,
                public.strategies.bot_id
            FROM
                public.cat_strategies
            INNER JOIN public.strategies
                ON public.cat_strategies.cat_str_id = public.strategies.cat_str_id
            INNER JOIN public.bots
                ON public.strategies.bot_id = public.bots.bot_id
            WHERE public.bots.uid = %s
        """
        strats = []
        try:
            with self.con.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(sql, (uid,))
                for row in cur.fetchall():
                    strat = StrategyStruct.from_dict(dict(row))
                    strats.append(strat)
        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(self.error_print(error=error, method="get_user_strategies", query=sql))
            raise
        return strats

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
                    strat = StrategyStruct.from_dict(dict(row))
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

    def get_cat_strategy(self, cat_str_id: str) -> Dict[str, Any]:
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
        strategy_params = {}
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (cat_str_id,))  # Pass the argument as a tuple
                result = cur.fetchone()
                if result is not None:
                    column_names = [desc[0] for desc in cur.description]
                    strategy_params = dict(zip(column_names, result))
        except (Exception, psycopg2.DatabaseError) as error:
            error_msg = self.error_print(error=error, method="get_cat_strategy", query=sql)
            logger.warning(error_msg)
            raise psycopg2.DatabaseError(error_msg) from error
        return strategy_params

    def del_cat_strategy(self, cat_str_name: str) -> bool:
        """
        Retrieves strategy from the `cat_strategies` table in the database.

        Args:
            cat_str_name (str): The name of the strategy.

        Raises:
            psycopg2.DatabaseError: If an error occurs during database operation.

        Returns:
            bool: True if successful.
        """
        sql = "DELETE FROM cat_strategies WHERE name = %s"
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (cat_str_name,))
                self.con.commit()  # Commit the transaction
                return cur.rowcount > 0  # True if rows were affected
        except psycopg2.DatabaseError as error:
            error_msg = self.error_print(error=error,
                                         method="del_cat_strategy",
                                         query=sql)
            logger.warning(error_msg)
            raise psycopg2.DatabaseError(error_msg) from error

