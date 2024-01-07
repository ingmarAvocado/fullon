"""
Comments
"""

from tabulate import tabulate
from libs import log
from libs.ctl.ctl_users_lib import CTL
from clint.textui import colored
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from typing import Optional, Tuple

logger = log.fullon_logger(__name__)


class CTL(CTL):
    """
    The CTL class is responsible for managing symbol-related functionalities,
    such as listing symbols.
    """

    def get_symbol_list(self, page: int = 1, page_size: int = 30, all=False, minimal=False) -> list:
        """
        Retrieves a paginated list of strategies.

        Parameters:
            page (int): The current page number. Defaults to 1.
            page_size (int): The number of records to return per page. Defaults to 10.

        Returns:
            list: A list of strategies for the current page.
        """
        args = {'page': page, 'page_size': page_size, 'all': all}
        symbols: list = self.RPC.symbols('list', args)
        if minimal:
            symbols = [{k: v for k, v in item.items() if k != 'cat_ex_id'} for item in symbols]
        return symbols

    def delete_symbol(self, symbol: Optional[int] = None) -> bool:
        session = PromptSession()
        symbols = self.get_symbol_list(all=True)
        symbols = [int(s['symbol_id']) for s in symbols]
        if not symbol:
            symbol = session.prompt(f"(Symbols Shell Feed) Enter symbol id to delete > ")
            symbol = int(symbol)
        if symbol in symbols:
            completer = WordCompleter(['yes/no'], ignore_case=True)
            yes = session.prompt(f"(Symbols Shell Feed) are you sure you want delete type 'yes' > ", completer=completer)
            if yes == 'yes':
                res = self.RPC.symbols('delete', {'symbol_id': symbol})
                print(colored.green("Symbol deleted"))
                return res
            else:
                print(colored.magenta(f"Deleting of symbol canceled ({yes})"))
        else:
            print(colored.red("symbol id is not registered, pick a valid one"))
        return False

    def add_symbol(self):
        """
        Interactively add a symbol to the database.

        This function performs the following steps:
        1. Presents the user with a list of exchanges from cat_exchange to choose from.
        2. After selecting an exchange, it fetches and presents the symbols available in that exchange.
        3. Once a symbol is chosen, the user is prompted to select backload data in terms of days.
        4. Constructs a SYMBOL dictionary with the chosen parameters and other defaults.
        5. Calls an RPC method to add the constructed symbol.

        Note:
            It utilizes the PromptSession from the `prompt_toolkit` to facilitate interactive prompts.

        Raises:
            ValueError: If the provided number of backload days is not an integer.
        """
        session = PromptSession()
        exchanges = self.RPC.exchanges('list')
        _exchanges = {}
        for exch in exchanges:
            _exchanges[exch[1]] = exch[0]
        # Prompt user to pick an exchange
        while True:
            completer = WordCompleter(_exchanges.keys(), ignore_case=True)
            exchange = session.prompt(f"(Symbols Shell Feed) Pick Exchange - press [tab] > ", completer=completer)
            if exchange in _exchanges:
                break
            print("Please pick a valid exchange.")
        # then query symbols from exchange to add in compeleter
        print("Downloading symbols from exchange...")
        symbols = self.RPC.symbols('list_exchange', {'exchange': exchange})
        symbols = dict(symbols)
        while True:
            completer = WordCompleter(symbols.keys(), ignore_case=True)
            symbol = session.prompt(f"(Symbols Shell Feed) Pick Symbol - press [tab] > ", completer=completer)
            if symbol in symbols:
                break
            print("Please pick a valid exchange.")
        session = PromptSession()
        while True:
            back = session.prompt(f"(Symbols Shell Feed) Pick Symbol - Backload data from (days) > ")
            try:
                back = int(back)
                break
            except ValueError:
                print("Please pick number of days, must be an integer")
        SYMBOL = {
            "symbol": symbol,
            "exchange_name": exchange,
            "updateframe": "1h",
            "backtest": back,
            "decimals": symbols[symbol]['pair_decimals'],
            "base": symbols[symbol]['base'],
            "ex_base": "",
            "futures": "t"
            }
        return self.RPC.symbols('add', {'symbol': SYMBOL})

    def select_symbol(self) -> Tuple[Optional[str], Optional[str], Optional[int]]:
        """
        Prompts the user to select an exchange and a symbol using an auto-completing interface.
        Returns the selected exchange, symbol, and symbol_id.

        Returns:
            Tuple[Optional[str], Optional[str], Optional[int]]: A tuple containing the selected exchange, symbol, and symbol_id.
        """
        session = PromptSession()

        # Get symbols from RPC
        symbols = self.get_symbol_list()
        if not symbols:
            return (None, None, None)

        # Initialize lists and dictionaries
        _exchanges = []
        _symbols = {}
        _symbol_ids = {} # Dictionary to store symbol_ids

        # Create exchange and symbol lists
        for symbol in symbols:
            # Add exchange to _exchanges list
            if symbol['exchange_name'] not in _exchanges:
                _exchanges.append(symbol['exchange_name'])

            # Add symbol to _symbols dictionary under the respective exchange
            if symbol['exchange_name'] not in _symbols:
                _symbols[symbol['exchange_name']] = []
            _symbols[symbol['exchange_name']].append(symbol['symbol'])
            # Store symbol_id
            _symbol_ids[symbol['symbol']] = symbol['symbol_id']

        # Prompt user to pick an exchange
        while True:
            completer = WordCompleter(_exchanges, ignore_case=True)
            exchange = session.prompt(f"(Symbols Shell Feed) Pick Feed Exchange - press [tab] > ", completer=completer)
            if exchange in _exchanges:
                break
            print("Please pick a valid exchange.")

        # Prompt user to pick a symbol
        while True:
            completer = WordCompleter(_symbols[exchange], ignore_case=True)
            symbol = session.prompt(f"(Symbols Shell Feed) Pick Symbol > ", completer=completer)
            if symbol in _symbols[exchange]:
                break
            print("Please pick a valid symbol.")
        # Retrieve symbol_id from the selected symbol
        symbol_id = _symbol_ids[symbol]

        return (exchange, symbol, symbol_id)

    def build_feeds(self, feeds: int) -> dict:
        """
        Create the feed associated with a bot. This method prompts the user to select
        the exchange, symbol, and optionally the period and compression for the bot's feed.
        :param feeds: The number of feeds to build
        :return: The updated feed configuration.
        :rtype: Dict
        """
        # Instantiate a PromptSession object

        _, symbol, symbol_id = self.select_symbol()

        session = PromptSession()

        _feeds = {}

        for feed in range(0, feeds):
            while True:
                periods = ['Minutes', 'Days', 'Weeks', 'Months']
                if feed == 0:
                    periods = ['Ticks']
                completer = WordCompleter(periods, ignore_case=True)
                period = session.prompt(f"(Symbols Shell Feed) Pick feed {feed} period > ", completer=completer)
                if period in periods:
                    _feeds[feed] = {'period': period} # Fixed assignment with colon
                    break
                print("Please pick a valid period.")

            if feed == 0:
                _feeds[feed]['compression'] = 1
            else:
                while True:
                    try:
                        compression = int(session.prompt(f"(Symbols Shell Feed) Pick feed {feed} compression > "))
                        _feeds[feed]['compression'] = compression
                        break # Added break to exit the loop once a valid compression is entered
                    except ValueError:
                        print("Please enter a valid integer for compression.")
            _feeds[feed]['order'] = feed+1
            _feeds[feed]['symbol_id'] = symbol_id
        return _feeds
