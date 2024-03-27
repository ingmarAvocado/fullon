import sys
from libs import log
from libs.models import base_model as database
from libs.structs.symbol_struct import SymbolStruct
from typing import List, Optional
import psycopg2


logger = log.fullon_logger(__name__)


class Database(database.Database):

    def remove_symbol(self, symbol: SymbolStruct) -> bool:
        """
        Removes a symbol from the database.

        Args:
            symbol (SymbolStruct): The symbol to be removed.

        Raises:
            psycopg2.DatabaseError: If an error occurs during the removal of the symbol.

        Returns:
            bool: True if the symbol was deleted, False otherwise.
        """
        try:
            with self.con.cursor() as cur:
                if symbol.symbol_id:
                    sql = "DELETE FROM symbols WHERE symbol_id = %s"
                    params = (symbol.symbol_id,)
                else:
                    sql = "DELETE FROM symbols WHERE symbol = %s and cat_ex_id = %s"
                    params = (symbol.symbol, symbol.cat_ex_id)

                cur.execute(sql, params)
                self.con.commit()

                # Check if any row was affected (i.e., the symbol was deleted)
                return cur.rowcount > 0

        except (Exception, psycopg2.DatabaseError) as error:
            self.con
        return False

    def install_symbol(self, symbol: SymbolStruct) -> int:
        """
        Installs a symbol in the database.

        Args:
            symbol (SymbolStruct): A symbolstruct containing the symbol information.

        Raises:
            psycopg2.DatabaseError: If an error occurs during the installation of the symbol.

        Returns:
            int: The auto-incremented symbol_id of the inserted symbol.
        """
        if not symbol.cat_ex_id:
            cat_ex_id = self.get_cat_exchanges(exchange=symbol.exchange_name)
            if cat_ex_id:
                cat_ex_id = cat_ex_id[0][0]
            else:
                raise ValueError("Couldn't find exchange in the database")
        else:
            cat_ex_id = symbol.cat_ex_id

        futures = symbol.futures if hasattr(symbol, 'futures') else 'f'

        sql = """
            INSERT INTO symbols (
                symbol, cat_ex_id, updateframe, backtest,
                decimals, base, ex_base, futures
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING symbol_id
        """
        values = (
            symbol.symbol, cat_ex_id, symbol.updateframe,
            symbol.backtest, symbol.decimals, symbol.base, symbol.ex_base, futures
        )

        try:
            with self.con.cursor() as cur:
                cur.execute(sql, values)
                symbol_id = cur.fetchone()[0]
                self.con.commit()
            return symbol_id
        except (Exception, psycopg2.DatabaseError) as error:
            self.con.rollback()
            if 'duplicate' in str(error):
                logger.info("Cant install duplicate symbol %s", symbol.symbol)
            else:
                raise psycopg2.DatabaseError("Error installing symbol: " + str(error)) from error

    def get_symbol_decimals(self, symbol, cat_ex_id):
        sql = "SELECT decimals from symbols where  cat_ex_id ='"+cat_ex_id+"' and symbol ='"+symbol+"'"
        try:
            #print(sql)
            cur = self.con.cursor()
            cur.execute(sql)
            row =  cur.fetchone()
            cur.close()
            if row:
                return row[0]
            else:
                return 8
        except (Exception, psycopg2.DatabaseError) as error:
            logger.info(self.error_print(error = error, method = "get_symbol_decimals", query = sql))
            sys.exit()
        return None

    def get_symbols(self, exchange: Optional[str] = None, page: int = 1,
                    page_size: int = 10, all: bool = False) -> List[SymbolStruct]:
        """
        Get a list of symbols from the database.

        Args:
            exchange (str): The name of the exchange to filter symbols by.
            page (int): The current page number. Defaults to 1.
            page_size (int): The number of records to return per page. Defaults to 10.
            all (bool): If True, retrieves all records without pagination. Defaults to False.

        Returns:
            List[StructSymbol]: A list of StructSymbol instances representing the symbols.
        """
        sql = """
              SELECT
                 public.symbols.symbol_id,
                 public.symbols.symbol,
                 public.symbols.cat_ex_id,
                 public.symbols.updateframe,
                 public.symbols.backtest,
                 public.symbols.decimals,
                 public.symbols.base,
                 public.symbols.ex_base,
                 public.symbols.only_ticker,
                 public.cat_exchanges.name as exchange_name,
                 public.cat_exchanges.ohlcv_view
              FROM
                 public.cat_exchanges
              INNER JOIN public.symbols
              ON public.cat_exchanges.cat_ex_id = public.symbols.cat_ex_id
        """

        params = []
        if exchange:
            sql += " WHERE public.cat_exchanges.name=%s"
            params.append(exchange)

        sql += " ORDER BY exchange_name, symbol"

        if not all:
            offset = (page - 1) * page_size
            sql += " LIMIT %s OFFSET %s"
            params.extend([page_size, offset])

        cur = self.con.cursor()
        try:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            symbols = [SymbolStruct(*row) for row in rows]
            cur.close()
            return symbols

        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(self.error_print(
                error=error, method="get_symbols", query=sql))
            cur.close()
            raise

    def get_symbol(self, symbol: str, cat_ex_id: Optional[str] = None, exchange_name: Optional[str] = None) -> Optional[SymbolStruct]:
        """
        Get symbol information from the database.

        Args:
            symbol (str): The symbol to search for.
            cat_ex_id (Optional[str], optional): The cat_ex_id. Defaults to None.
            exchange_name (Optional[str], optional): The exchange name. Defaults to None.

        Returns:
            Optional[SymbolStruct]: Returns symbol information as a SymbolStruct instance or None if symbol is not found or both cat_ex_id and exchange_name are not provided.
        """
        if not cat_ex_id and not exchange_name:
            return None

        sql = """
            SELECT
                 public.symbols.symbol_id,
                 public.symbols.symbol,
                 public.symbols.cat_ex_id,
                 public.symbols.updateframe,
                 public.symbols.backtest,
                 public.symbols.decimals,
                 public.symbols.base,
                 public.symbols.ex_base,
                 public.symbols.only_ticker,
                 public.cat_exchanges.name as exchange_name,
                 public.cat_exchanges.ohlcv_view
            FROM
                public.cat_exchanges
            INNER JOIN public.symbols
            ON public.cat_exchanges.cat_ex_id = public.symbols.cat_ex_id
            WHERE symbol = %s
        """

        if exchange_name:
            sql += " AND public.cat_exchanges.cat_ex_id in (SELECT cat_ex_id FROM cat_exchanges WHERE name = %s)"
            params = (symbol, exchange_name)
        else:
            sql += " AND public.cat_exchanges.cat_ex_id = %s"
            params = (symbol, cat_ex_id)

        try:
            with self.con.cursor() as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
            if row:
                return SymbolStruct(*row)
        except (Exception, psycopg2.DatabaseError) as error:
            error = "Error can't get_symbol, postgres says: " + str(error)
            logger.info(error)
            raise

    def get_symbol_by_id(self, symbol_id: int) -> Optional[SymbolStruct]:
        """
        Get symbol information from the database.

        Args:
            symbol (int): The symbol to search for.

        Returns:
            Optional[SymbolStruct]: Returns symbol information as a
            SymbolStruct instance or None if symbol is not found or
            both cat_ex_id and exchange_name are not provided.
        """
        sql = """
            SELECT
                 public.symbols.symbol_id,
                 public.symbols.symbol,
                 public.symbols.cat_ex_id,
                 public.symbols.updateframe,
                 public.symbols.backtest,
                 public.symbols.decimals,
                 public.symbols.base,
                 public.symbols.ex_base,
                 public.symbols.only_ticker,
                 public.cat_exchanges.name as exchange_name,
                 public.cat_exchanges.ohlcv_view
            FROM
                public.cat_exchanges
            INNER JOIN public.symbols
            ON public.cat_exchanges.cat_ex_id = public.symbols.cat_ex_id
            WHERE symbol_id = %s
        """
        try:
            with self.con.cursor() as cur:
                cur.execute(sql, (symbol_id,))
                row = cur.fetchone()
            if row:
                return SymbolStruct(*row)
        except (Exception, psycopg2.DatabaseError) as error:
            error = "Error can't get_symbol, postgres says: " + str(error)
            logger.info(error)
            raise

    def get_symbol_id(self, symbol: str, exchange_name: Optional[str] = None) -> Optional[str]:
        """
        Get symbol_id from the database.

        Args:
            symbol (str): The symbol to search for.
            exchange_name (Optional[str], optional): The exchange name. Defaults to None.

        Returns:
            str: Returns symbol_id as a string or None if symbol is not found or exchange_name is not provided.
        """
        symbol_struct = self.get_symbol(symbol, exchange_name=exchange_name)
        if symbol_struct:
            return symbol_struct.symbol_id
        else:
            return None
