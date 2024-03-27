"""
comment
"""
from typing import Dict, Union, Optional, List, Any
from libs import log
from libs.secret import SecretManager
from libs.structs.exchange_struct import ExchangeStruct
from libs.database import Database
import json

logger = log.fullon_logger(__name__)


class UserManager:
    """
    Main account class for managing users, strategies, and bots.
    """

    def __init__(self):
        """
        Initializes the User Manager and creates a connection pool.
        """

    def __del__(self):
        """
        Closes the connection pool and deletes the pool object.
        """
        pass

    def add_exchange(self, exch: ExchangeStruct) -> str:
        """
        Adds an exchange account for a user.

        Args:
            exch (Dict): The exchange account data.

        Returns:
            int: The result of adding the exchange.
        """
        logger.info("Adding exchange account of a user_ex...")
        with Database() as dbase:
            result = dbase.add_user_exchange(exchange=exch)
        return result

    def add_bot_strategy(self, strategy: dict) -> str:
        """
        Links a strategy to a user.

        Args:
            strategy (dict): The strategy struct

        Returns:
            str: The strategy ID.
        """
        logger.info("Linking strategies to user_ex...")
        with Database() as dbase:
            strategy_id = dbase.add_bot_strategy(strategy=strategy)
        return strategy_id

    def del_bot_strategy(self, bot_id: int) -> bool:
        """
        Links a strategy to a user.

        Args:
            bot_id: The id to delete

        Returns:
            str: The strategy ID.
        """
        logger.info("Deleting strategy %s", bot_id)
        res = False
        with Database() as dbase:
            res = dbase.del_bot_strategy(bot_id=bot_id)
        return res

    def add_params_to_strategy(self, strategy: str, params: Dict) -> bool:
        """
        Adds parameters to a strategy.

        Args:
            strategy (str): The strategy name.
            params (Dict): The parameters to add to the strategy.

        Returns:
            bool: The result of adding parameters to the strategy.
        """
        logger.info("Adding params to strategies...")
        with Database() as dbase:
            strategy = dbase.add_params_to_strategy(strategy=strategy, params=params)
        del dbase
        return bool(strategy)

    def add_feed_to_bot(self, feed: Dict) -> bool:
        """
        Adds a feed to a strategy.

        Args:
            feed (Dict): The feed data.

        Returns:
            bool: The result of adding the feed to the strategy.
        """
        logger.info("Adding feeds to bot...")
        with Database() as dbase:
            strategy = False
            if feed['bot_id']:
                strategy = dbase.add_feed_to_bot(feed=feed)
        return bool(strategy)

    def add_bot(self, bot: Dict) -> int:
        """
        Adds a bot.

        Args:
            bot (Dict): The bot data.

        Returns:
            int: The result of adding the bot.
        """
        logger.info("Adding bot...")
        with Database() as dbase:
            result = dbase.add_bot(bot=bot)
        return result

    def add_bot_exchange(self, bot_id: int, exchange: Dict) -> bool:
        """
        Adds an exchange to a bot.

        Args:
            bot_id (int): The bot ID.
            exchange (Dict): The exchange data.

        Returns:
            bool: The result of adding the exchange to the bot.
        """
        logger.info("Adding exchange to a bot...")
        with Database() as dbase:
            result = dbase.add_exchange_to_bot(bot_id=bot_id, exchange=exchange)
        return bool(result)

    def list_user_strats(self, bot_id: int) -> str:
        """
        Lists user strategies (currently not used).

        Args:
            bot_id (int): The strategy ID.

        Returns:
            str: A formatted string containing the user strategies.
        """
        dbase = Database()
        params = dbase.get_user_strat_params(bot_id=bot_id)
        del dbase
        msg = ""
        for param in params:
            string = f'"str_name": "{param.str_name}",\
                       "name":"{param.name}",\
                       "value":"{param.value}"'
            msg = msg + '{' + string + '}\n'
        return msg

    def list_users(self, page=1, page_size=10, all=False) -> List[Dict]:
        """
        Lists all users.

        Returns:
            str: A formatted string containing the user list.
        """
        users = []
        with Database() as dbase:
            users = dbase.get_user_list(page=page, page_size=page_size, all=all)
        return users

    def get_user_id(self, mail: str) -> Optional[int]:
        """
        returns user uid

        Args:

            mail: str - email of user

        Returns:

            str: int of user or empty string if not found
        """
        uid = ""
        try:
            with Database() as dbase:
                uid = dbase.get_user_id(mail=mail)
        except AttributeError:
            uid = None
        return uid

    def get_user_exchanges(self, uid: int) -> List[Dict]:
        """
        Lists all users.

        Returns:
            str: A formatted string containing the user list.
        """
        with Database() as dbase:
            exchanges: List[Dict[str, Any]] = dbase.get_user_exchanges(uid=uid)
        return exchanges

    def user_details(self, uid: int) -> Dict[str, Dict[str, Dict[str, Union[str, int]]]]:
        """
        Retrieves user details.

        Args:
            uid (int): The user ID.

        Returns:
            Dict[str, Dict[str, Dict[str, Union[str, int]]]]: A dictionary containing the user details.
        """
        with Database() as dbase:
            details = {"exchanges": {}, "strategies": {}, "bots": {}}
            exchanges = dbase.get_user_exchanges(uid=uid)
            if exchanges:
                for exch in exchanges:
                    details["exchanges"][exch['ex_name']] = {
                                "exchange": exch['ex_name'],
                                "ex_id": exch['ex_id'],
                                "cat_ex_id": exch['cat_ex_id'],
                                "ex_named": exch['ex_named']}

            strategies = dbase.get_user_strategies(uid=uid)
            if strategies:
                for strat in strategies:
                    details["strategies"][strat.name] = {
                        "strategy": strat.name,
                        "str_named": strat.cat_name
                    }

            bots = dbase.get_bot_list(uid=uid)
            if bots:
                for bot in bots:
                    bot_id_str = str(bot.bot_id)
                    details["bots"][bot_id_str] = {
                        "bot_id": bot.bot_id,
                        "dry_run": bot.dry_run
                        }

        return details

    def set_secret_key(self, user_id: int, exchange: str, key: str, secret: str) -> bool:
        """
        Adds a new user key to secret database.

        Args:
            user_id (int): The user id
            exchange (str): the exchange
            secret (str): the api secret
            key (str): the api key

        Return:
            bool: on success

        """
        hush = SecretManager()
        _user_id = str(user_id)
        payload = hush.access_secret_version(_user_id)
        sec_key = f'{key}:{secret}'
        if not payload:
            """ new key """
            payload = {exchange: sec_key}
        else:
            """ there where keys """
            payload = json.loads(payload)
            payload[exchange] = sec_key
        if hush.add_secret_version(secret_id=_user_id, payload=json.dumps(payload)):
            del hush
            return True
        return False

    def del_secret_key(self, user_id: int, exchange: str) -> bool:
        """
        Removes a user key to secret database.

        Args:
            user_id (int): The user id
            exchange (str): the exchange
            key (str): the api key

        Return:
            bool: on success

        """
        hush = SecretManager()
        _user_id = str(user_id)
        payload = hush.access_secret_version(_user_id)
        if payload:
            """ there where keys """
            payload = json.loads(payload)
            try:
                if payload[exchange]:
                    del payload[exchange]
                    if len(payload) > 0:
                        hush.add_secret_version(secret_id=_user_id,
                                                payload=json.dumps(payload))
                    else:
                        hush.delete_secret(secret_id=_user_id)
                    del hush
                    return True
            except KeyError:
                pass
        del hush
        return False
