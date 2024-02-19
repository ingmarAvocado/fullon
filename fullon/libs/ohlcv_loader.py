"""
OHLCVLoader is responsible for loading Open, High, Low, Close, and Volume (OHLCV) data 
for a given exchange and symbol within a specified time range. It fetches this data from 
a database, formats it, and returns it as a pandas DataFrame.
"""

#from libs.database_ohlcv import Database
from libs.models.ohlcv_model import Database
from libs import log
import arrow
import pandas
from typing import Optional

logger = log.fullon_logger(__name__)


class OHLCVLoader():
    """
    OHLCVLoader is responsible for loading Open, High, Low, Close, and Volume (OHLCV) data
    for a given exchange and symbol within a specified time range. It fetches this data from
    a database, formats it, and returns it as a pandas DataFrame.
    """

    def fetch(self, exchange: str, symbol: str,  compression: int,
              period: str, fromdate: arrow.Arrow,
              todate: arrow.Arrow = arrow.utcnow()
              ) -> Optional[pandas.DataFrame]:
        """
        Fetches OHLCV data from the database for a specified exchange, symbol, and time period.

        Parameters:
            exchange (str): The name of the exchange (e.g., 'Binance', 'Coinbase').
            symbol (str): The trading symbol (e.g., 'BTC/USD').
            compression (int): The compression size for the data (e.g., 1 for 1-minute data).
            period (str): The period type (e.g., 'minutes', 'days').
            fromdate (arrow.Arrow): The start date for the data fetch.
            todate (arrow.Arrow): The end date for the data fetch. Defaults to the current UTC time.

        Returns:
            Optional[pandas.DataFrame]: A DataFrame containing the OHLCV data if available; otherwise, None.
        """
        table = self._get_table(exchange=exchange, symbol=symbol)
        with Database(exchange=exchange, symbol=symbol) as dbase:
            rows = dbase.fetch_ohlcv(table=table,
                                     compression=compression,
                                     period=period.capitalize(),
                                     fromdate=fromdate.datetime,   # pylint: disable=E1101
                                     todate=todate.datetime)
        if rows:
            # Convert the fetched data to a pandas DataFrame
            df = pandas.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            # Set timestamp as the index and convert it to a datetime object
            df.set_index('timestamp', inplace=True)
            df.index = pandas.to_datetime(df.index)
            return df

    def _get_table(self, exchange: str, symbol: str) -> str:
        """
        Determines the correct database table name for fetching OHLCV data based on the exchange and symbol.

        Parameters:
            exchange (str): The name of the exchange.
            symbol (str): The trading symbol.

        Returns:
            str: The table name for the specified exchange and symbol.

        Raises:
            ValueError: If no appropriate table exists for the schema.
        """
        table = exchange + "_" + symbol
        table = table.replace('/', '_')
        table = table.replace('-', '_')
        with Database(exchange=exchange, symbol=symbol) as dbase:
            if dbase.table_exists(schema=table, table="trades"):
                return table + ".trades"
            if dbase.table_exists(schema=table, table="candles1m"):
                return table + ".candles1m"
            raise ValueError(f"_get_table: Error, cant continue: \
                tables for schema {table} dont exist")
