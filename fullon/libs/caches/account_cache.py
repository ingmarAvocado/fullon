"""
Cache class for managing caching operations with Redis.
The Cache class provides functionality to interact with
a Redis cache server, including creating, updating,
and retrieving cache entries. It also includes utility
methods for testing the connection to the cache server,
preparing the cache, and filtering cache entries based
on timestamps and component types.
"""

import time
import json
import redis
import arrow
from libs import log
from libs.caches import tick_cache as cache
from libs.structs.position_struct import PositionStruct
from typing import Dict, Optional, List

logger = log.fullon_logger(__name__)

'''
try:
    EXCHANGES_DIR = os.listdir('exchanges/')
except FileNotFoundError:
    EXCHANGES_DIR = os.listdir('fullon/exchanges/')
'''
EXCHANGES_DIR = ['kraken', 'kucoin_futures']


class Cache(cache.Cache):
    """
    A class for managing caching operations with Redis.
    Attributes:
.
    """

    def upsert_positions(self, ex_id: int, positions: Dict) -> bool:
        """
        Upserts account information by symbol.

        :param user_ex: UserEx object containing user and exchange information.
        :param account: A dictionary containing account information.
        :param date: The date when the account information is updated.
        :param futures: A boolean flag indicating if the exchange is a futures exchange.
        :return: True if the operation is successful, False otherwise.
        """
        try:
            user_ex = self.get_exchange(ex_id=ex_id)
            if user_ex.ex_id == '':
                return False
            key = f"account_positions"
            subkey = ex_id
            if positions == {} or self._check_position_dict(pos=positions) is False:
                if self.conn.hdel(key, subkey):
                    return True
                return False
            positions['timestamp'] = arrow.utcnow().timestamp()
            self.conn.hset(key, subkey, json.dumps(positions))
        except AttributeError as error:
            print(str(error))
            return False
        return True

    def upsert_user_account(self,
                            ex_id: int,
                            account: dict,
                            date: Optional[str] = None) -> bool:
        """
        Upserts user account.

        Args:
            ex_id (int): Exchange ID.
            account (dict): Account information.
            date (str): Date information.

        Returns:
            bool: True if successful, False otherwise.
        """
        if not date:
            date = arrow.utcnow().format('YYYY-MM-DD HH:mm:ss')
        try:
            key = f"{ex_id}"
            account['date'] = date
            self.conn.hset("accounts", key, json.dumps(account))
            return True
        except AttributeError:
            pass
        return False

    def clean_positions(self) -> int:
        """
        removes all positions from redis

        """
        return self.conn.delete("account_positions")

    def get_all_positions(self) -> List[PositionStruct]:
        positions = []
        try:
            datas = self.conn.hgetall("account_positions")
            if not datas:
                return positions

            for key, value in datas.items():
                account_data = json.loads(value.decode('utf-8'))
                timestamp = account_data.get('timestamp')
                ex_id = key.decode('utf-8')

                for symbol, data in account_data.items():
                    if symbol != 'timestamp':
                        data['symbol'] = symbol
                        if timestamp:
                            data['timestamp'] = timestamp
                        data['ex_id'] = ex_id
                        position = PositionStruct.from_dict(data)
                        positions.append(position)

        except (KeyError, TypeError, json.JSONDecodeError) as error:
            logger.error(f"Error getting all positions: {error}")
            return []
        return positions

    @staticmethod
    def _check_position_dict(pos: Dict) -> bool:
        """
        Check if all items in the input dictionary have the same set of subkeys.

        :param pos: A dictionary containing pairs as keys and dictionaries with subkeys as values.
        :return: True if all items have the same set of subkeys, False otherwise.
        """
        subkeys = {'cost', 'volume', 'fee', 'price'}
        for pair_data in pos.values():
            if set(pair_data.keys()) != subkeys:
                return False
        return True

    def get_position(self,
                     symbol: str,
                     ex_id: str,
                     latest: bool = False,
                     cur_timestamp: Optional[float] = None) -> PositionStruct:
        """
        Returns position from account by symbol.

        Args:
            symbol (str): Trading symbol.
            uid (str): User ID.
            ex_id (str): Exchange ID.
            latest (bool, optional): Whether to get the latest position or not. Defaults to False.
            cur_timestamp (int, optional): Current timestamp. Defaults to None.

        Returns:
            DefaultMunch or None: Position data or None if not found.
        """
        try:
            if ex_id == '':
                return PositionStruct(symbol=symbol)
            datas = self.conn.hget(f"account_positions", ex_id)
            if not datas:
                return PositionStruct(symbol=symbol)
            datas = json.loads(datas)
            data = datas[symbol]
            data['symbol'] = symbol
            data['timestamp'] = datas['timestamp']
            data = PositionStruct.from_dict(data)
            if latest:
                if not cur_timestamp:
                    cur_timestamp = arrow.utcnow().shift(seconds=-1).timestamp()
                ws_timestamp = arrow.get(data.timestamp).timestamp()
                if ws_timestamp < cur_timestamp:
                    time.sleep(1)
                    return self.get_position(symbol=symbol,
                                             ex_id=ex_id,
                                             latest=latest,
                                             cur_timestamp=cur_timestamp)
        except (KeyError, TypeError) as error:
            logger.error('%s', str(error))
            data = PositionStruct(symbol=symbol)
        return data

    def get_full_account(self, exchange: str, currency: str) -> dict:
        """
        Returns account with date.

        Args:
            exchange (str): exchange_id.
            currency (str, optional): Base currency. Defaults to "BTC".

        Returns:
           Dict: Account data
        """
        try:
            key = f"{exchange}"
            data = json.loads(self.conn.hget("accounts", key))
            return data[currency]
        except (TypeError, KeyError) as error:
            logger.error("We get error %s", str(error))
            return {}

    def get_all_accounts(self) -> dict:
        """
        Returns account crawler with all records, decoded from JSON
        Returns:
           Dict: Account data
        """
        try:
            raw_data = self.conn.hgetall("accounts")
            decoded_data = {}
            for key, value in raw_data.items():
                try:
                    # Decode bytes to string if necessary
                    if isinstance(key, bytes):
                        key = key.decode('utf-8')
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    # Parse JSON
                    decoded_data[key] = json.loads(value)
                except json.JSONDecodeError as json_error:
                    logger.warning(f"Failed to decode JSON for key {key}: {str(json_error)}")
                    decoded_data[key] = value  # Store original value if JSON parsing fails
            return decoded_data
        except (TypeError, KeyError, redis.RedisError) as error:
            logger.error("Error retrieving accounts: %s", str(error))
            return {}
