"""
"""

import json
from libs import log, database
from libs.caches import exchange_cache as cache
from libs.structs.symbol_struct import SymbolStruct
from typing import Optional, List

logger = log.fullon_logger(__name__)


class Cache(cache.Cache):
    """
    A class for managing caching operations with Redis.
    Attributes:
    """

    def get_symbols(self, exchange: str, loop: int = 0, force=False) -> List[SymbolStruct]:
        """
        Retrieve symbol information from Redis cache or database.

        Returns:
            List[SymbolStruct]: A list of SymbolStruct instances representing the symbol information.
        """
        redis_key = f"symbols_list:{exchange}"
        symbol_list: List[SymbolStruct] = []

        if force:
            with database.Database() as dbase:
                symbols = dbase.get_symbols(exchange=exchange, all=True)
                for sym in symbols:
                    sym_dict = sym.to_dict()
                    self.conn.hset(redis_key, sym.symbol, json.dumps(sym_dict))
                    self.conn.expire(redis_key, 24 * 60 * 60)  # expire after 24 hours

        if self.conn.exists(redis_key):
            symbols = self.conn.hgetall(redis_key)
            symbol_list = [SymbolStruct(**json.loads(symbol[1])) for symbol in symbols.items()]
        elif loop == 0:
            self.get_symbols(exchange=exchange, force=True)
            symbol_list = self.get_symbols(exchange=exchange, loop=1)

        return symbol_list

    def get_symbol(self,
                   symbol: str,
                   cat_ex_id: Optional[str] = None,
                   exchange_name: Optional[str] = None,
                   loop=0) -> SymbolStruct:
        """
        Retrieve symbol information from Redis cache or database.

        Args:
            symbol (str): The symbol to search for.
            cat_ex_id (Optional[str], optional): The cat_ex_id. Defaults to None.
            exchange_name (Optional[str], optional): The exchange name. Defaults to None.

        Returns:
            Optional[SymbolStruct]: A SymbolStruct instance representing the symbol information, or None if the symbol is not found.
        """
        if not exchange_name:
            exchange_name = self.get_exchange_name(cat_ex_id)
        redis_key = f'symbols_list:{exchange_name}'
        symbol_struct = None
        while not symbol_struct:
            if self.conn.exists(redis_key):
                symbol_dict = self.conn.hget(redis_key, symbol)
                if symbol_dict:
                    symbol_struct = SymbolStruct(**json.loads(symbol_dict))
                elif loop == 0:
                    self.get_symbols(exchange=exchange_name, force=True)
                    loop = 1
                else:
                    break
            else:
                if loop == 0:
                    self.get_symbols(exchange=exchange_name, force=True)
                    loop = 1
                else:
                    break
        return symbol_struct

    def delete_symbol(self, symbol: str, cat_ex_id: Optional[str] = None, exchange_name: Optional[str] = None) -> None:
        """
        Remove a symbol from the database and Redis cache.

        Args:
            symbol (str): The symbol to remove.
            cat_ex_id (Optional[str], optional): The cat_ex_id. Defaults to None.
            exchange_name (Optional[str], optional): The exchange name. Defaults to None.

        Raises:
            psycopg2.DatabaseError: If an error occurs during the removal of the symbol.

        Returns:
            None
        """
        if not exchange_name:
            exchange_name = self.get_exchange_name(cat_ex_id)
        redis_key = f'symbols_list:{exchange_name}'
        if self.conn.exists(redis_key):
            self.conn.hdel(redis_key, symbol)
        redis_key = f'tickers:{exchange_name}'
        if self.conn.exists(redis_key):
            self.conn.hdel(redis_key, symbol)
