"""
Comments
"""

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
                       page_size: int = 30,
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

    def reload_strategies(self) -> bool:
        """
        Adds new strategies to the system and prints a success or failure message.

        Returns:
            None
        """
        res = self.RPC.strategies('reload')
        print(colored.green("Strategies have been reloaded"))
        if res:
            return True
        return False

    def del_strategy(self, strats: List):
        """
        deletes a global strategy from the system
        """
        session = PromptSession()
        completer = WordCompleter(strats, ignore_case=True)

        while True:
            try:
                cat_str_name = session.prompt("(Strategies Shell) Select a strategy to delete> ",
                                              completer=completer).strip().lower()
            except (EOFError, KeyboardInterrupt):
                return
            except ValueError:
                print(colored.red("\nInvalid input, please enter a valid strategy to delete"))

            print(f"Lets delete: {cat_str_name}")
            # 1 check if there is a bot with that strategy, if it is ask if we want to delete
            bots = self.RPC.strategies('get_bots', {'cat_str_name': cat_str_name})
            completer = WordCompleter(['yes', 'no'], ignore_case=True)
            if bots:
                print("To delete this strategy we are going to delete associated bots:")
                _yes = False
                for bot in bots:
                    print(f"- bot_id {bot['bot_id']} owned by {bot['mail']}")
                try:
                    _yes = session.prompt("(Strategies Shell) Are you sure you want to delete bots> ",
                                          completer=completer).strip().lower()
                except (EOFError, KeyboardInterrupt):
                    return
                except ValueError:
                    print(colored.red("\nInvalid input, please enter pick a valid choice"))
                if _yes == "yes":
                    for bot in bots:
                        delete = self.RPC.bots('delete', {'bot_id': bot['bot_id']})
                        if 'Error' not in str(delete):
                            print(colored.green(f"Bot bot_id {bot['bot_id']} deleted"))
                        else:
                            print(colored.red(f"Bot bot_id {bot['bot_id']} could not be deleted"))

            if bots and _yes != 'yes':
                break
            else:
                try:
                    _yes = session.prompt("(Strategies Shell) Are you sure you want to delete> ",
                                          completer=completer).strip().lower()
                except (EOFError, KeyboardInterrupt):
                    return
                except ValueError:
                    print(colored.red("\nInvalid input, please enter a valid strategy to delete"))
                if _yes == "yes":
                    if self.RPC.strategies('del_cat_str', {'cat_str_name': cat_str_name}):
                        print(colored.green(f"Strategy {cat_str_name} deleted"))
                    else:
                        print(colored.red(f"Strategy {cat_str_name} could not be deleted"))
            return bots

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
                        return (resp, strats[selection][1])
                    else:
                        print(f"Error: cant process {resp}")
                else:
                    print("Invalid selection. Please choose a valid strategy name.")
            except EOFError:  # Catch Ctrl+D and exit the loop
                break
            except KeyboardInterrupt:
                break
        return None  # Return None if the loop is exited without a valid selection
