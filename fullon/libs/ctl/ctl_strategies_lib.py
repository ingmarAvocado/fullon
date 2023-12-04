"""
Comments
"""

from tabulate import tabulate
from libs import log
from libs.ctl.ctl_ticks_lib import CTL
from clint.textui import colored
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from typing import Optional, List

logger = log.fullon_logger(__name__)


class CTL(CTL):
    """
    The CTL class is responsible for managing strategy-related functionalities,
    such as listing strategies, adding new strategies, and deleting strategies.
    """

    def get_strat_list(self, page: int = 1,
                       page_size: int = 10,
                       all=False,
                       minimal=False) -> list:
        """
        Retrieves a paginated list of strategies.

        Parameters:
            page (int): The current page number. Defaults to 1.
            page_size (int): The number of records to return per page. Defaults to 10.

        Returns:
            list: A list of strategies for the current page.
        """
        args = {'page': page, 'page_size': page_size, 'all': all}
        strats: list = self.RPC.strategies('list', args)
        if minimal:
            strats = [{k: v for k, v in item.items() if 'id' not in k} for item in strats]
        return strats

    def get_user_strat_list(self, uid: str) -> list:
        """
        Retrieves a paginated list of strategies.

        Parameters:
            page (int): The current page number. Defaults to 1.
            page_size (int): The number of records to return per page. Defaults to 10.

        Returns:
            list: A list of strategies for the current page.
        """
        args = {'uid': uid}
        _strats: list = self.RPC.strategies('user_list', args)
        return _strats

    def add_strategies(self) -> bool:
        """
        Adds new strategies to the system and prints a success or failure message.

        Returns:
            None
        """
        res: bool = self.RPC.strategies('add')
        if res:
            print(colored.green("Strategies have been added"))
            return True
        else:
            print(colored.red("No new strategies to add"))
            return False

    def del_strategy(self, strats: List):
        """
        deletes a global strategy from the system
        """
        bots = self.RPC.strategies('get_bots', {'cat_str_name': cat_str_name})

        session = PromptSession()
        completer = WordCompleter(strats, ignore_case=True)

        while True:
            try:
                print("Pick strategy to delete")
                cat_str_name = session.prompt("(Strategies Shell)> ",
                                              completer=completer).strip().lower()
            except (EOFError, KeyboardInterrupt):  # Catch Ctrl+D and Ctrl+C and exit
                return
            except ValueError:
                print(colored.red("\nInvalid input, please enter a valid strategy to delete"))

            print(f"i will delete {cat_str_name}")
            # 1 check if there is a bot with that strategy, if it is ask if we want to delete
            bots = self.RPC.strategies('get_bots', {'cat_str_name': cat_str_name})

        #bots = self.RPC.strategies('get_bots', {'cat_str_id': cat_str_id})

    def del_user_strategy(self, str_id) -> bool:
        """
        Deletes a strategy from the system. Currently, not implemented.

        Returns:
            bool
        """
        return self.RPC.strategies('del_user', {'str_id': str_id})

    def set_new_strategy(self, bot_id: int) -> Optional[int]:
        """
        Prompts the user to select a strategy by name using an auto-completing interface.
        Returns the selected strategy's ID and the associated 'feeds' value.

        Returns:
            Optional[int]: 'feeds' value, or None if the selection is cancelled.
        """
        strats = self.get_strat_list()
        strats = {s['name']: (s['cat_str_id'], s['feeds']) for s in strats}
        session = PromptSession()
        completer = WordCompleter(list(strats.keys()), ignore_case=True)
        while True:
            try:
                selection = session.prompt("(Strategies Shell) Select a strategy from catalog: ", completer=completer)
                if selection in strats:
                    cat_str_id = strats[selection][0]
                    STRAT = {
                        "cat_str_id": cat_str_id,
                        "bot_id": bot_id}
                    resp = str(self.RPC.strategies('add_user', {'strat': STRAT}))
                    if 'Error' not in resp:
                        return strats[selection][1]
                    else:
                        print(f"Error: cant process {resp}")
                else:
                    print("Invalid selection. Please choose a valid strategy name.")
            except EOFError:  # Catch Ctrl+D and exit the loop
                break
            except KeyboardInterrupt:
                break
        return None  # Return None if the loop is exited without a valid selection
