"""
"""

import json
from libs import log
from libs.caches import base_cache as cache
from typing import Dict, Optional, List, Any
import arrow

logger = log.fullon_logger(__name__)


class Cache(cache.Cache):
    """
    A class for managing caching operations with Redis.
    Attributes:

    """
    _process_types = ['tick', 'ohlcv', 'bot', 'account', 'order', 'bot_status_service']

    def delete_from_top(self, component: Optional[str] = None) -> int:
        """
        Delete a process entry from the top of the cache.

        Args:
            component (Optional[str], optional): The component type to delete. Defaults to None.
            pid (Optional[int], optional): The process ID to delete. Defaults to None.

        Returns:
            int: The number of deleted entries.
        """
        if component:
            return self.conn.delete(component)
        return 0

    def get_top(self, deltatime: Optional[int] = None, comp: Optional[str] = None) -> List[dict]:
        """
        Returns a list of dictionaries stored in Redis that have a timestamp within a certain delta time.

        Args:
            deltatime (int, optional): The delta time in seconds. If provided, only objects with a timestamp within
                the past deltatime seconds will be returned. Defaults to None.
            comp (str, optional): The component type to filter on. If provided, only objects with a type matching
                the given component will be returned. Defaults to None.

        Returns:
            list: A list of dictionaries stored in Redis that meet the filtering criteria.
        """
        rows = []
        for component in self._process_types:
            for key, values in self.conn.hgetall(component).items():
                obj = json.loads(values)
                obj.update({"type": component, "key": key.decode()})
                try:
                    tstamp1 = arrow.utcnow().shift(seconds=deltatime*-1).timestamp()
                    tstamp2 = arrow.get(obj['timestamp']).timestamp()
                except TypeError:
                    tstamp2, tstamp1 = (0, 0)
                obj['timestamp'] = obj['timestamp'].format('YYYY-MM-DD HH:mm:ss')
                if comp and deltatime:
                    if tstamp2 < tstamp1 and obj['type'] == comp:
                        rows.append(obj)
                elif tstamp2 < tstamp1 and not comp:
                    rows.append(obj)
                elif tstamp1 == 0 and comp:
                    if obj['type'] == comp:
                        rows.append(obj)
                else:
                    rows.append(obj)
        return rows

    def update_process(self, tipe: str, key: str, message: str = "") -> bool:
        """
        Update a process entry in the cache.

        Args:
            tipe (str): The type of process (e.g., "tick").
            key (str): The key identifying the process.
            message (str, optional): An optional message to include with the process update. Defaults to an empty string.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        try:
            data = json.loads(self.conn.hget(tipe, key))
        except TypeError:
            logger.warning("No record for %s:%s attempting to create", tipe, key)
            return False
        data['message'] = message
        data['timestamp'] = arrow.utcnow().format()
        data = json.dumps(data)
        if tipe in self._process_types:
            self.conn.hset(tipe, key, data)
            return True
        return False

    def new_process(self,
                    tipe: str,
                    key: str,
                    params: Dict[str, Any],
                    pid: Optional[Any] = None,
                    message: str = "") -> int:
        """
        Add a new process entry to the cache.

        Args:
            tipe (str): The type of process (e.g., "tick").
            key (str): The key identifying the process.
            params (Dict[str, Any]): A dictionary containing the process parameters.
            pid (int): The process ID. Obsolete
            message (str, optional): An optional message to include with the new process. Defaults to an empty string.

        Returns:
            bool: True if added, false if not
        """
        values = {"params": params,
                  "message": message,
                  "timestamp": arrow.utcnow().format()}
        data = json.dumps(values)
        if tipe in self._process_types:
            return self.conn.hset(tipe, key, data)
        return 0

    def get_process(self, tipe: str, key: str) -> Dict[str, Any]:
        """
        Get process information from Redis.

        Args:
            tipe (str): Type of process (e.g. "tick", "ohlcv", "account").
            key (str): Key identifying the process.

        Returns:
            dict: Process information, or None if not found.
        """
        data = self.conn.hget(tipe, key)
        if not data:
            return {}
        return json.loads(data)

    def delete_process(self, tipe: str, key: str = '') -> bool:
        """
        Delete a process from the cache.

        Args:
            tipe (str): The type of process to delete.
            key (str): The key identifying the process to delete.

        Returns:
            bool: True if the process was deleted, False otherwise.
        """
        if key:
            if tipe in self._process_types:
                self.conn.hdel(tipe, key)
                return True
        else:
            self.conn.delete(tipe)
            return True
        return False
