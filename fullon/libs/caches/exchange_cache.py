"""
"""

import json
from libs import log, database
from libs.structs.exchange_struct import ExchangeStruct
from libs.caches import process_cache as cache
from typing import Dict, List
import time
import redis

logger = log.fullon_logger(__name__)


class Cache(cache.Cache):
    """
    A class for managing caching operations with Redis.
    Attributes:
    """

    def get_cat_exchanges(self) -> List[Dict[str, str]]:
        """
        Fetch a list of exchanges from Redis cache or PostgreSQL.
        If the data is not in Redis cache, it will be fetched from PostgreSQL and cached in Redis.

        Returns:
            List[Dict[str, str]]: A list of dictionaries representing the exchanges.
        """
        redis_key = 'cat_exchanges'

        # check if the data is in Redis cache
        if self.conn.exists(redis_key):
            exchanges_json = self.conn.get(redis_key)
            exchanges = json.loads(exchanges_json)
        else:
            # fetch data from the database
            with database.Database() as dbase:
                rows = dbase.get_cat_exchanges(all=True)
                exchanges = [{'name': exch[1], 'id': str(exch[0])} for exch in rows]
                expires_at = int(time.time() + 24 * 60 * 60)
                self.conn.set(redis_key, json.dumps(exchanges), ex=expires_at)
        return exchanges

    def get_cat_ex_id(self, exchange: str) -> str:
        """
        Fetch an exchange id from Redis cache or PostgreSQL.
        If the data is not in Redis cache, it will be fetched from PostgreSQL and cached in Redis.

        Returns:
            List[Dict[str, str]]: A list of dictionaries representing the exchanges.
        """
        redis_key = f'cat_ex_id'
        # check if the data is in Redis cache
        res = ''
        if self.conn.exists(f"{redis_key}"):
            res = self.conn.hget(redis_key, exchange)
        if res:
            return res.decode('utf-8')
        else:
            # fetch data from the database
            with database.Database() as dbase:
                exchanges = dbase.get_cat_exchanges(all=True)
            for exch in exchanges:
                try:
                    self.conn.hset(redis_key, exch[1], exch[0])
                    expires_at = int(time.time() + 24 * 60 * 60 * 3)
                    self.conn.expire(redis_key, expires_at)
                except KeyError:
                    pass
        res = self.conn.hget(redis_key, exchange)
        if res:
            return res.decode('utf-8')
        return ''

    def get_exchange_name(self, cat_ex_id: str, loop: int = 0) -> List[Dict[str, str]]:
        """
        Fetch an exchange id from Redis cache or PostgreSQL.
        If the data is not in Redis cache, it will be fetched from PostgreSQL and cached in Redis.

        Returns:
            exchange name from cat_ex_id
        """
        redis_key = f'exchange_names'
        # check if the data is in Redis cache

        def from_database():
            with database.Database() as dbase:
                exchs = dbase.get_cat_exchanges(all=True)
                for exch in exchs:
                    self.conn.hset(redis_key, exch[0], exch[1])
                    expires_at = int(time.time() + 24 * 60 * 60 * 3)
                    self.conn.expire(redis_key, expires_at)

        if self.conn.exists(f"{redis_key}"):
            res = self.conn.hget(redis_key, cat_ex_id).decode('utf-8')
        else:
            if loop == 0:
                from_database()
                self.get_exchange_name(cat_ex_id=cat_ex_id, loop=1)
            res = []
        return res

    def get_exchange_symbols(self, exchange: str) -> List[Dict[str, str]]:
        """
        Fetch a list of symbols from an exchanges from Redis cache or PostgreSQL.
        If the data is not in Redis cache, it will be fetched from PostgreSQL and cached in Redis.

        Returns:
            List[Dict[str, str]]: A list of dictionaries representing the exchanges.
        """
        redis_key = f'exchange_symbols:{exchange}'

        def from_database(exchange):
            with database.Database() as dbase:
                rows = dbase.get_exchange_symbols(cat_ex_id=exchange)
                symbols = []
                for symbol in rows:
                    symbols.append(symbol.symbol)
                expires_at = int(time.time() + 24 * 60 * 60)
                if symbols:
                    self.conn.set(redis_key, json.dumps(symbols), ex=expires_at)
            return symbols

        # check if the data is in Redis cache
        if self.conn.exists(redis_key):
            symbols_json = self.conn.get(redis_key)
            symbols = json.loads(symbols_json)
        else:
            symbols = from_database(exchange=exchange)
        if not symbols:
            symbols = from_database(exchange=exchange)
        return symbols

    def get_exchange(self, ex_id: str) -> ExchangeStruct:
        """
        Retrieve exchange information from Redis cache or database.

        Args:
            ex_id (str): The exchange ID.

        Returns:
            ExchangeStruct: An ExchangeStruct instance representing the exchange information.
        """
        redis_key = f'exchange_info:{ex_id}'

        # Define a function to retrieve data from the database
        def from_database(ex_id: str) -> ExchangeStruct:
            with database.Database() as dbase:
                exchange = dbase.get_exchange(ex_id=ex_id)
                exchange_struct = ExchangeStruct()
                if exchange:
                    exchange_struct = exchange[0]
                    exchange_dict = exchange_struct.to_dict()
                    expires_at = int(time.time() + 24 * 60 * 60)
                    self.conn.set(redis_key,
                                  json.dumps(exchange_dict), ex=expires_at)
                return exchange_struct

        if self.conn.exists(redis_key):
            exchange_dict = self.conn.get(redis_key)
            exchange_info: ExchangeStruct = ExchangeStruct()
            if exchange_dict:
                exchange_dict = json.loads(exchange_dict)
                exchange_info = ExchangeStruct(**exchange_dict)
        else:
            exchange_info = from_database(ex_id=ex_id)
        if not exchange_info:
            exchange_info = from_database(ex_id=ex_id)
        return exchange_info

    def get_exchanges(self) -> List[ExchangeStruct]:
        """
        Retrieve exchange information from Redis cache or database.

        Returns:
            List[ExchangeStruct]: A list of ExchangeStruct instances representing the exchange information.
        """
        redis_key = f'exchanges_list'

        # Define a function to retrieve data from the database
        def from_database() -> None:
            with database.Database() as dbase:
                exchanges = dbase.get_exchange()
                for exch in exchanges:
                    exchange_dict = exch.to_dict()
                    self.conn.hset(redis_key,
                                   exch.ex_id,
                                   json.dumps(exchange_dict))
                    self.conn.expire(redis_key, 24 * 60 * 60)  # expire after 24 hours

        exchange_list: List[ExchangeStruct] = []
        if self.conn.exists(redis_key):
            exchanges = self.conn.hgetall(redis_key)
            for ex_id, exchange in exchanges.items():
                exchange_dict = json.loads(exchange)
                exchange_struct = ExchangeStruct(**exchange_dict)
                exchange_list.append(exchange_struct)
        else:
            from_database()
            exchange_list = self.get_exchanges()
        return exchange_list

    def push_ws_error(self, error: str, ex_id: str) -> None:
        """
        Push the ID of an open order to a Redis list.

        Args:
            ex_id (str): The exchange ID.
            oid (str): The ID of the open order.

        Returns:
            None
        """
        redis_key = f"ws_error:{ex_id}"
        self.conn.rpush(redis_key, error)

    def pop_ws_error(self, ex_id: str) -> bool:
        """
        Pop the next open order from the Redis list.

        Args:
            ex_id (str): The exchange ID.

        Returns:
            str: The ID of the next open order.

        Raises:
            TimeoutError: If the open order queue is empty and the timeout period has expired.
        """
        redis_key = f"ws_error:{ex_id}"
        try:
            _, error = self.conn.blpop(redis_key, timeout=0)
            if error:
                return False
        except redis.exceptions.TimeoutError:
            pass
        except KeyboardInterrupt:
            pass
        return False
