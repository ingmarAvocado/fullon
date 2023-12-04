"""
Comments
"""

from tabulate import tabulate
from libs import log
from libs.ctl.ctl_strategies_lib import CTL
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from clint.textui import colored
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import arrow
import time
from prettytable import PrettyTable
from typing import Union


logger = log.fullon_logger(__name__)


class CTL(CTL):

    def launch_bot(self, bots: List[Dict[str, str]], bot_id: Optional[int] = None) -> None:
        """
        Launches a selected bot.

        Args:
            bots: A list of bot information represented as dictionaries. Each bot dictionary is
                  expected to have at least a 'bot_id' field which is used for bot identification.

        Returns:
            None
        """
        # Start the session with prompt_toolkit
        session = PromptSession()

        # Prepare bot dictionary with bot_id as keys
        bot_dict = {str(bot['bot_id']): bot for bot in bots}
        if not bot_id:
            while True:
                try:
                    # Prompt user to select a bot to launch
                    bot_id = session.prompt("(Bots Shell) Enter bot ID to launch > ")

                    if bot_id not in bot_dict:
                        print(colored.red("\nInvalid bot ID."))
                        return
                    break
                except (EOFError, KeyboardInterrupt):  # Catch Ctrl+D and Ctrl+C and exit
                    return
                except ValueError as error:
                    print(colored.red("\nInvalid input, please enter a valid bot ID."))

        # Get the bot details using the bot_id
        bot = bot_dict[str(bot_id)]
        # Assuming the 'bot_id' field is unique and is used to start the bot
        print(colored.magenta(self.RPC.bots('start', {'bot_id': bot['bot_id']})))
        time.sleep(1)

    def stop_bot(self, bots: List[Dict[str, str]], bot_id: Optional[int] = None) -> None:
        """
        Stops a specified bot from a list of active bots by prompting the user for input.

        This method displays a command-line prompt to the user, asking for the number of the bot to stop.
        It then sends a 'stop' command to the specified bot and prints a confirmation message.
        The method handles various input errors, including non-integer input and out-of-range bot numbers,
        and allows the user to exit with Ctrl+D or Ctrl+C.

        Parameters:
        - bots (List[Dict[str, str]]): List of dictionaries containing information about the active bots.
            Each dictionary must include the 'bot_id' key, representing the unique identifier for a bot.

        Attributes:
        - self.RPC (object): Remote Procedure Call object used to communicate with the bots.

        Exceptions:
        - EOFError: Caught when the user presses Ctrl+D to exit the prompt.
        - KeyboardInterrupt: Caught when the user presses Ctrl+C to exit the prompt.
        - ValueError: Caught when the input is not a valid integer.

        Returns:
        - None
        """
        session = PromptSession()
        while True:
            try:
                bot_ids = [bot['bot_id'] for bot in bots]
                if not bot_id:
                    bot_id = session.prompt("(Bots Shell) Enter bot number to stop > ")
                bot_id = int(bot_id)
                if bot_id not in bot_ids:
                    print(colored.red("\nInvalid bot number."))
                    continue
                bot_id = bots[bot_ids.index(bot_id)]['bot_id']
                break
            except (EOFError, KeyboardInterrupt):  # Catch Ctrl+D and Ctrl+C and exit
                return
            except ValueError:
                print("Not a valid number.")

        print(f"Attempting to stop bot: {bot_id}")
        resp = self.RPC.bots('stop', {'bot_id': bot_id})
        if resp:
            print("Bot stopped")
            return
        else:
            print(f"\nCould not stop bot {bot_id}, is it running?")
            return

    def _bot_header(self, details: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Creates a formatted string header for display, encompassing editable fields,
        extended parameters, and feed details of a bot. It also combines these details
        into a single dictionary.

        The function excludes certain keys ('uid', 'str_id', 'bot_id', 'name') from
        the editable fields, tfreating them as non-editable.

        Args:
            details (Dict[str, Any]): The details of a bot.

        Returns:
            Tuple[str, Dict[str, Any]]: A tuple containing two elements:
                - A formatted string that combines the details of editable fields,
                  extended parameters, and feeds.
                - A dictionary that combines the editable fields, extended parameters,
                  and feeds details.
        """
        # Generate tables for editable fields, extended params, and feeds
        non_editable_keys = ['uid', 'str_id', 'bot_id', 'name', 'feeds', 'extended']
        editable_fields = {k: v for k, v in details.items() if k not in non_editable_keys}
        start_index = 0
        header = self._table(title="Current details", fields=editable_fields, index=start_index)

        start_index += len(editable_fields)
        header += self._table(title="Extended params", fields=details.get('extended', {}), index=start_index)

        start_index += len(details.get('extended', {}))
        header += self._table_feeds(title="Feeds", feeds=details.get('feeds', {}), index=start_index)

        # Combine all fields
        fields = {**editable_fields, **details.get('extended', {}), **details.get('feeds', {})}

        return header, fields

    def _table(self, title: str, fields: Dict[str, Any], index: int) -> str:
        """
        Prints a table with each row represented by a tuple consisting of 
        the index, field name, and value. The index starts from the provided
        start_index and increments for each field.

        Args:
            fields (Dict[str, Any]): A dictionary where each key-value pair
                represents a field name and its value.
            index (int): The starting index for the table rows.

        Returns:
            str: The table as a string with borders.
        """
        rows = [(i + index, field, str(value))  # Convert value to string
                for i, (field, value) in enumerate(fields.items())]

        table = PrettyTable()
        table.field_names = ['No.', 'Field', 'Value']
        for row in rows:
            table.add_row(row)

        # Add any other formatting or border styles you need
        resp = f"\n{title}:\n" + table.get_string()
        return resp

    def _table_feeds(self, title: str, feeds: Dict[str, Any], index: int) -> str:
        """
        Prints a table with each row represented by a tuple consisting of
        the index, feed name, field name, and value. The index starts from
        the provided start_index and increments for each field.

        Args:
            title (str): Title of the table to be printed.
            feeds (Dict[str, Any]): A dictionary where each key-value pair
                represents a feed name and its value.
            index (int): The starting index for the table rows.

        Returns:
            None
        """
        # what i need is to retun a dictionary
        # like feed[0] = "symbol: BTC
        rows = []

        for feed_name, feed_values in feeds.items():
            fields = ''
            for field_name, field_value in feed_values.items():
                if 'feed_id' not in field_name:
                    fields += f"{field_name}:{field_value}, "
            rows.append((index, feed_name, fields.rstrip(", ")))
            index += 1
        resp = (f'\n{title}:\n')
        resp += (tabulate(rows, headers=['No.', 'Feed', 'Value'], tablefmt='psql'))
        return resp

    def add_bot(self) -> bool:
        """
        Add a new bot to the system using user-selected strategy, feeds, and exchange.

        This method interacts with the user through the command-line interface using the PromptSession from
        the prompt_toolkit library. It guides the user through the process of creating a new bot by prompting
        for the strategy, feeds, exchange, and bot name. After collecting the necessary information, it constructs
        a bot dictionary with the selected options and sends the bot information to the RPC server to add it to
        the system.

        Returns:
            bool: True if the bot was successfully added to the system; False if the user canceled the operation
            (e.g., by pressing Ctrl+D or Ctrl+C) or if any error occurred during the process.

        Raises:
            None

        Example:
            Suppose we have a CTL object initialized as ctl = CTL(). To add a new bot to the system, we can call
            the method as follows:

            >>> bot_added = ctl.add_bot()
            (Edit Bot Shell) Name your bot > MyBot
            >>> print(bot_added)
            True

            In this example, the user selected the strategy, feeds, exchange, and provided the bot name "MyBot."
            The method returned True, indicating that the bot was successfully added to the system. If the user
            cancels the operation or any error occurs during the process, the method would return False.
        """
        uid = self.select_user()
        if not uid:
            print("No user selected to create a bot")
            return False

        #first we register the bot
        session = PromptSession()

        while True:
            try:
                bot_name = session.prompt("(Edit Bot Shell) Name your bot > ")
                break
            except (EOFError, KeyboardInterrupt):  # Catch Ctrl+D and Ctrl+C and exit
                print("Canceling operation")
                return False
            except ValueError:
                print(colored.red("\nInvalid input, please enter a valid bot name."))
        bot = {'user': uid,
               'name': bot_name,
               'dry_run': True,
               'active': True}

        _bot_id: str = self.RPC.bots('add', {'bot': bot})
        try:
            if _bot_id and 'Error' not in _bot_id:
                print(colored.green("Bot registered"))
            else:
                print(colored.red("Failure adding bot"))
                return False
        except TypeError:
            pass
        bot_id: int = int(_bot_id)

        #then we assing an exchange
        exchange = self.select_user_exchange(uid=uid)
        exchange = {"exchange_id": exchange}
        if self.RPC.bots('add_exchange', {'bot_id': bot_id, 'exchange': exchange}):
            print(colored.green("Exchange added to bot"))
        else:
            print(colored.red("Failed adding exchange to bot"))
            return False
        #then we assign a strategy
        print(colored.blue("Set the strategy"))
        feeds_num = self.set_new_strategy(bot_id=bot_id)
        if not feeds_num:
            print(colored.red("Failed adding strategy to bot"))
            return False
        #then we do the feeds
        feeds = self.build_feeds(feeds=feeds_num)
        _feeds = {}
        for num, feed in feeds.items():
            _feeds[str(num)] = feed
        if self.RPC.bots('add_feeds', {'bot_id': bot_id, 'feeds': _feeds}):
            print(colored.green("Feeds added"))
        else:
            print(colored.red("Failed adding feeds to bot"))
            return False
        print(colored.green("Bot fully added"))
        return False

    def delete_bot(self, bots: List[Dict[str, str]]) -> None:
        """
        Deletes a  bot identified by its ID.

        This method interacts with the user through the command-line interface using the PromptSession from
        the prompt_toolkit library. It allows the user to select a bot from the provided list of bots by entering
        its ID. Once a valid bot ID is entered, the method fetches the details of the selected bot from the RPC server
        and prompts the user to delete specific fields of the bot.

        The method prompts the user to save the changes after prepring delete.
        Parameters:
            bots (List[Dict[str, str]]): A list of dictionaries, where each dictionary contains details of a bot,
            including the bot ID (bot['bot_id']) as a string.

        Returns:
            None: The method does not return anything. Instead, it directly updates the bot's configuration on the
            RPC server based on the user's edits, if any.

        Raises:
            None
        """
        session = PromptSession()
        bot_dict = {str(bot['bot_id']): bot for bot in bots}

        while True:
            try:
                print("\n" + tabulate(bots, headers="keys", tablefmt="pretty"))                
                bot_id = session.prompt("(Delete Bot Shell) Enter bot ID to delete or 'quit' to exit > ")

                if bot_id.lower() == 'quit':
                    return

                if bot_id not in bot_dict:
                    print(colored.red("\nInvalid bot ID."))
                    continue
                yes = session.prompt(f"\n(Delete Bot Shell) Are you sure to delete bot {bot_id}? (yes/no) > ")  
                if yes:
                    if self.RPC.bots('delete', {'bot_id': bot_id}):
                        print(colored.green(f"\nDeleted bot {bot_id}"))
                        return
                else:
                    print(colored.green(f"\nCould not delete bot: {bot_id}"))
            except (EOFError, KeyboardInterrupt):  # Catch Ctrl+D and Ctrl+C and exit
                return
            except ValueError:
                print(colored.red("\nInvalid input, please enter a valid bot ID to delete"))

    def edit_bot(self, bots: List[Dict[str, str]], bot_id: Optional[int] = None) -> None:
        """
        Edit the details of a bot identified by its ID.

        This method interacts with the user through the command-line interface using the PromptSession from
        the prompt_toolkit library. It allows the user to select a bot from the provided list of bots by entering
        its ID. Once a valid bot ID is entered, the method fetches the details of the selected bot from the RPC server
        and prompts the user to edit specific fields of the bot.

        The method prompts the user to save the changes after making edits. If the user chooses to save the changes,
        the updated bot details are sent back to the RPC server to update the bot's configuration. If the user chooses
        not to save the changes, the bot's details remain unchanged.

        Parameters:
            bots (List[Dict[str, str]]): A list of dictionaries, where each dictionary contains details of a bot,
            including the bot ID (bot['bot_id']) as a string.

        Returns:
            None: The method does not return anything. Instead, it directly updates the bot's configuration on the
            RPC server based on the user's edits, if any.

        Raises:
            None
        """
        session = PromptSession()
        bot_dict = {str(bot['bot_id']): bot for bot in bots}

        while True:
            try:
                bot_id = session.prompt("(Edit Bot Shell) Enter bot ID to edit or 'quit' to exit > ")

                if bot_id.lower() == 'quit':
                    return

                if bot_id not in bot_dict:
                    print(colored.red("\nInvalid bot ID."))
                    continue

                details = self.RPC.bots('details', {'bot_id': bot_id})
                self.edit_fields(details=details)
                save_changes = session.prompt("\n(Edit Bot Shell) Save changes? (yes/no) > ")
                if save_changes.lower() in ['y', 'yes']:
                    self.RPC.bots('edit', {'bot': details})
                    print(colored.green(f"\nUpdated bot {bot_id}"))
                #print("\n" + tabulate(bots, headers="keys", tablefmt="pretty"))
                return
            except (EOFError, KeyboardInterrupt):  # Catch Ctrl+D and Ctrl+C and exit
                return
            except ValueError as error:
                print(colored.red("\nInvalid input, please enter a valid bot ID to edit"))           

    def edit_fields(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prompts the user to select and edit fields from a provided set of bot details.
        The function iteratively presents the user with a list of fields to edit, and accepts
        input for new values. The process continues until the user enters 'done'.

        It returns a dictionary of changes, where keys represent field names and values represent
        new values provided by the user.

        Args:
            details (Dict[str, Any]): The details of a bot.

        Returns:
            Dict[str, Any]: A dictionary representing changes made by the user.
        """
        session = PromptSession()
        changes = {}
        extended = {}
        feeds = {}

        while True:
            header, fields = self._bot_header(details)
            print(header)
            field_num = session.prompt("(Edit Bot Shell) Enter number of field to edit, press enter to refresh, or 'write' when finished > ")

            if field_num.lower() == 'write':
                return changes

            if field_num == '':
                continue

            try:
                field_num = int(field_num)
            except ValueError:
                print(colored.red("\nInvalid number, please enter a valid number."))
                continue

            if field_num < 0 or field_num >= len(fields):
                print(colored.red("\nInvalid number, please enter a valid number."))
                continue

            field = list(fields.keys())[field_num]

            if 'feeds' in details and field in details['feeds']:
                feed = self._change_bot_feed(feed=details['feeds'][field])
                if feed:
                    details['feeds'][field].update(feed)
            else:
                new_value = session.prompt(f"(Bot Shell) Enter new value for '{field}' > ")
                # if it's an extended field
                if 'extended' in details and field in details['extended']:
                    extended[field] = new_value
                else:
                    changes[field] = new_value
                details.update(changes)
                details['extended'].update(extended)

    def _change_bot_feed(self, feed: Dict) -> Dict:
        """
        Change the feed associated with a bot. This method prompts the user to select
        the exchange, symbol, and optionally the period and compression for the bot's feed.
        :param feed: The current feed configuration of the bot.
        :type feed: Dict
        :return: The updated feed configuration.
        :rtype: Dict
        """
        # Instantiate a PromptSession object
        session = PromptSession()

        # Get symbols from RPC
        exchange, symbol, _ = self.select_symbol()
        if not symbol:
            return feed

        # Default period and compression values
        period = 'Ticks'
        compression = 1

        # If the current feed period is not 'ticks', prompt the user for period and compression
        if 'ticks' not in feed['period'].lower():
            while True:
                periods = ['Minutes', 'Hours', 'Days', 'Weeks', 'Months']
                completer = WordCompleter(periods, ignore_case=True)
                period = session.prompt(f"(Bots Shell Feed) Pick feed period > ", completer=completer)
                if period in periods:
                    break
                print("Please pick a valid period.")

            while True:
                try:
                    compression = int(session.prompt(f"(Bots Shell Feed) Pick feed compression > "))
                    break
                except ValueError:
                    print("Please enter a valid integer for compression.")

        # Update the feed configuration
        feed['exchange'] = exchange
        feed['symbol'] = symbol
        feed['period'] = period
        feed['compression'] = compression

        # Return the updated feed configuration
        return feed

    def get_bot_list(self, page=1) -> list:
        """
        Retrieves a list of bots and their statuses from the RPC server. The bots are requested page by page,
        where each page contains a maximum of 10 bots. Each bot status dictionary is modified by:  
        - Removing the 'timestamp' field.
        - Trimming the 'bot_id' to its last 8 characters.
        - Representing the 'position' and 'live' fields in green color if they are True.

        Returns:
            list: A list of dictionaries, each containing a bot's status information.
        """
        page_size = 20
        bots: list = self.RPC.bots("list", {'page': page, 'page_size': page_size})
        for num, bot in enumerate(bots, start=(page-1)*page_size+1):
            # Drop the 'timestamp' field
            bot.pop('timestamp', None)
            # Trim 'bot_id' to its last 8 characters
            #bot['bot_id'] = bot['bot_id'][-8:]
            # If 'position' is True, represent it in green color
            if bot.get('position', False):
                bot['position'] = '\033[92m{}\033[0m'.format(bot['position'])
            # If 'live' is True, represent it in green color
            if bot.get('live', False):
                bot['live'] = '\033[92m{}\033[0m'.format(bot['live'])
        return bots

    def show_live_bots(self):
        """
        Retrieve and display the status of all live trading bots.
        """
        # Retrieve bots list
        _bots = self.RPC.bots("live_list")

        if _bots:
            self.display_bots(_bots)
        else:
            print("\nNo live bots to display.")

    def _prep_bots(self, bots: list) -> list:
        """
        Prepare bot data for displaying.
        """
        _bots = []

        if bots:
            for bot in bots.values():
                for key, feed in bot.items():
                    _meta = {'bot_id': feed['bot_id'],
                             'bot_name': feed['bot_name'],
                             'strategy': feed['strategy']}
                    feed['timestamp'] = arrow.get(feed['timestamp']).format('YYYY-MM-DD HH:mm:ss')
                    feed['position'] = round(feed['position'], 4)
                    feed['feed'] = key

                    # Reorder the bot dictionary as per desired format
                    ordered = ['bot_id',
                               'feed',
                               'exchange',
                               'symbol',
                               'cash',
                               'tick',
                               'open price',
                               'position',
                               'open value',
                               'value',
                               'roi',
                               'roi pct',
                               'base',
                               'timestamp']
                    feed = {k: feed[k] for k in ordered}
                _bots.append(feed)
        return _bots

    def _display_bot(self, bot):
        """
        Display detailed information about a bot.

        Args:
            bot: A dictionary containing bot details.

        Returns:
            None
        """
        # Print the full details of the bot without removing any keys.
        # Create table with 2 columns per feed
        feeds = []
        for feed_id, feed in bot.items():
            list_format = [[key, value] for key, value in feed.items()]
            print("\n" + tabulate(list_format, headers=['Key', 'Value'], tablefmt="pretty"))
            continue

    def display_bots(self, bots: Dict[str, List[Dict[str, Union[str, float]]]]) -> None:
        """
        Display bot information and allow the user to view detailed info.

        Args:
            bots (Dict[str, List[Dict[str, Union[str, float]]]]): A dictionary of bots and their information.

        Returns:
            None
        """
        session = PromptSession()

        while True:
            bots = self._prep_bots(bots)
            self.print_bots_table(bots)

            commands = ['view', 'back', 'stop']
            completer = WordCompleter(commands, ignore_case=True)

            try:
                resp = session.prompt("\nLive bots (view/back/stop) > ", completer=completer)

                if resp == 'back':
                    return
                elif resp == 'stop':
                    self.stop_bot(bots=bots)
                elif resp == 'view':
                    bot_number = input("Enter bot number: ")
                    if bot_number in bots:
                        self._display_bot(bots[bot_number])
                    else:
                        print(colored.cyan('Invalid bot number'))

                bots = self.RPC.bots("live_list")
            except (EOFError, KeyboardInterrupt):
                return
            except ValueError:
                print(colored.red("\nInvalid input, please enter a valid command or bot number."))

    def print_bots_table(self, bots: List[Dict[str, Union[str, float]]]) -> None:
        """
        Print the table of bot information.

        Args:
            bots (List[Dict[str, Union[str, float]]]): A list of dictionaries containing bot information.

        Returns:
            None
        """
        df = pd.DataFrame(bots)
        df_sorted = df.sort_values(by=['bot_id', 'feed'])

        df_sorted['roi'] = df_sorted['roi'].apply(self.color_roi)
        df_sorted['roi pct'] = df_sorted['roi pct'].apply(self.color_roi)

        headers = df_sorted.columns
        table = df_sorted.values.tolist()
        print(tabulate(table, headers, tablefmt="pretty"))

    def color_roi(self, val: float) -> str:
        """
        Colorize the ROI value based on its sign.

        Args:
            val (float): The ROI value.

        Returns:
            str: The colorized ROI value.
        """
        if val < 0:
            return f"\033[91m{val}\033[0m"  # Red color for negative 'roi'
        elif val == 0:
            return str(val)
        else:
            return f"\033[92m{val}\033[0m"  # Green color for non-negative 'roi'