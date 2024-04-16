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

    def stop_all(self):
        """
        Compatability
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

    def remove_exchange(self, ex_id: int) -> bool:
        """
        Removes a user exchange

        Args:
            ex_id (int): The exchange to remove

        Returns:
            bool: True if deleted
        """
        logger.info("Adding exchange account of a user_ex...")
        with Database() as dbase:
            result = dbase.remove_user_exchange(ex_id=ex_id)
        return result

    def add_bot_strategy(self, strategy: dict) -> int:
        """
        Links a strategy to a user.

        Args:
            strategy (dict): The strategy struct

        Returns:
            int: The strategy ID.
        """
        logger.info("Linking strategies to user_ex...")
        with Database() as dbase:
            strategy_id = dbase.add_bot_strategy(strategy=strategy)
        return strategy_id

    def del_bot_strategy(self, str_id: int) -> bool:
        """
        Links a strategy to a user.

        Args:
            bot_id: The id to delete

        Returns:
            str: The strategy ID.
        """
        logger.info("Deleting strategy %s", str_id)
        res = False
        with Database() as dbase:
            res = dbase.del_bot_strategy(str_id=str_id)
        return res

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
            return dbase.add_feed_to_bot(feed=feed)

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

    def remove_bot(self, bot_id: int) -> bool:
        """
        removes a bot.

        Args:
            bot_id (int): The bot id

        Returns:
            bool: if bot was removed
        """
        logger.info("removed bot...")
        with Database() as dbase:
            result = dbase.delete_bot(bot_id=bot_id)
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
        if uid:
            with Database() as dbase:
                return  dbase.get_user_exchanges(uid=uid)
        return []

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

    def add_user(self, user: dict) -> None:
        """
        Adds a new user to the database.

        Args:
            user (dict): The user dict
        """
        with Database() as dbase:
            dbase.add_user(user=user)

    def remove_user(self, user_id: Optional[str] = None, email: Optional[str] = None) -> bool:
        """
        Adds a new user to the database.

        Args:
            username (str): The username for the new user.
            password (str): The password for the new user.
            email (str): The email address for the new user.
        """
        with Database() as dbase:
            return dbase.remove_user(user_id=user_id, email=email)
