"""
Cache class for managing caching operations with Redis.
The Cache class provides functionality to interact with
a Redis cache server, including creating, updating,
and retrieving cache entries. It also includes utility
methods for testing the connection to the cache server,
preparing the cache, and filtering cache entries based
on timestamps and component types.
"""

import json
from libs import log
from libs.caches import trades_cache as cache
from typing import List, Dict, Union
import arrow
import redis

logger = log.fullon_logger(__name__)


class Cache(cache.Cache):
    """
    A class for managing caching operations with Redis.
    Attributes:
    """

    def is_blocked(self, ex_id: str, symbol: str) -> str:
        """
        Returns the position for a bot.

        Args:
            ex_id (str): The exchange ID.
            symbol (str): The trading symbol.

        Returns:
            str:  This exchange and symbol has a position.
        """
        data = self.conn.hget(f"block_exchange", f"{ex_id}:{symbol}")
        if data:
            return data.decode()
        return ""

    def get_blocks(self) -> List:
        """
        Returns the position for a bot.

        Args:
            ex_id (str): The exchange ID.
            symbol (str): The trading symbol.

        Returns:
            Bool:  This exchange and symbol has a position.
        """
        data = self.conn.hgetall(f"block_exchange")
        blocks: List = []
        if data:
            for key, value in data.items():
                ex_id, symbol = key.decode('utf-8').split(":")
                blocks.append({"ex_id": ex_id,
                               "symbol": symbol,
                               "bot": value.decode('utf-8')})
        return blocks

    def block_exchange(self, ex_id: str, symbol: str, bot_id: int) -> bool:
        """
        In key blocked it will indicate if an exchange is blocked.
        """
        if self.conn.hset("block_exchange", f"{ex_id}:{symbol}", bot_id):
            return True
        return False

    def unblock_exchange(self, ex_id: str, symbol: str) -> bool:
        """
        In key blocked it will indicate if an exchange is blocked.
        """
        if self.conn.delete("block_exchange", f"{ex_id}:{symbol}"):
            return True
        return False

    def is_opening_position(self, ex_id: str, symbol: str) -> bool:
        """
        Returns if some bot is opening a position with same exchange/symbol

        Args:
            ex_id (str): The exchange ID.
            symbol (str): The trading symbol.

        Returns:
            Bool:  This exchange and symbol has a position.
        """
        data = self.conn.hget(f"opening_position", f"{ex_id}:{symbol}")
        if data:
            return True
        return False

    def mark_opening_position(self, ex_id: str, symbol: str, bot_id: int) -> bool:
        """
        blah
        """
        if self.conn.hset("opening_position", f"{ex_id}:{symbol}",
                          f"{bot_id}:{arrow.utcnow()}"):
            return True
        return False

    def unmark_opening_position(self, ex_id: str, symbol: str) -> bool:
        """
        In key blocked it will indicate if an exchange is blocked.
        """
        if self.conn.delete("opening_position", f"{ex_id}:{symbol}"):
            return True
        return False

    def update_bot(self, bot_id: str, bot: Dict[str, Union[str, int, float]]) -> bool:
        """
        Update a bot's status in the cache.

        Args:
            bot_id (str): The ID of the bot.
            bot (Dict[str, Union[str, int, float]]): A dictionary containing the bot's status.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """

        # Iterate over each feed's status in the bot dictionary
        for feed_status in bot.values():
            # Set the timestamp for each feed's status
            feed_status["timestamp"] = arrow.utcnow().format()

        # Save the updated bot status to the cache
        if self.conn.hset("bot_status", bot_id, json.dumps(bot)):
            return True
        return False

    def del_bot(self, bot_id: str) -> bool:
        """
        Dels a bot's status in the cache.

        Args:
            bot_id (str): The ID of the bot.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        # Save the updated bot status to the cache
        if self.conn.hdel("bot_status", bot_id):
            return True
        return False

    def del_status(self) -> bool:
        """
        Dels a bots' status in the cache.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        # Save the updated bot status to the cache
        if self.conn.delete("bot_status"):
            return True
        return False

    def get_bots(self) -> Dict:
        """
        Retrieve all bots and their corresponding statuses from the cache.

        Returns:
            bots_dict (Dict): A dictionary where each key-value pair represents a bot and its status. 
            The key is the bot_id and the value is another dictionary with detailed status information of the bot.

        Raises:
            RedisError: If there is an error while attempting to get data from Redis.
        """
        try:
            # Attempt to get all bots from Redis
            bots_bytes = self.conn.hgetall("bot_status")
        except redis.RedisError as error:
            # Log and re-raise the error
            logger.error(f"Failed to get bot statuses from Redis: {error}")
            raise
        # Decode bytes object to string and parse string to Python dict
        bots_dict = {bot_id.decode(): json.loads(bot_status.decode()) for bot_id, bot_status in bots_bytes.items()}
        return bots_dict
