"""
Comments
"""

from tabulate import tabulate
from libs import log
from libs.ctl.ctl_base_lib import CTL
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

    def get_user_list(self, page: int = 1, page_size: int = 10, all=False, minimal=False) -> list:
        """
        Retrieves a paginated list of strategies.

        Parameters:
            page (int): The current page number. Defaults to 1.
            page_size (int): The number of records to return per page. Defaults to 10.

        Returns:
            list: A list of strategies for the current page.
        """
        args = {'page': page, 'page_size': page_size, 'all': all}
        users: list = self.RPC.users('list', args)
        if minimal:
            _users = []
            for user in users:
                _users.append({'uid': user['uid'],
                               'mail': user['mail'],
                               'name': user['name'],
                               'lastname': user['lastname'],
                               'active': user['active']})
            users = _users
        return users

    def select_user(self) -> Optional[str]:
        """
        Prompts the user to select a user from a list, utilizing an auto-completing interface.
        This method retrieves the list of users from the database and presents it to the user.
        The user can then pick a user, and the method will return the UID of the selected user.

        Returns:
            Optional[str]: The UID of the selected user, or None if no users are found.
        """
        session = PromptSession()

        # Get symbols from RPC
        users = self.get_user_list(all=True)
        if not users:
            return None

        # Initialize lists and dictionaries
        _users = {}

        # Create exchange and symbol lists
        for user in users:
            _users[user['mail']] = user['uid']

        # Prompt user to pick a user
        while True:
            try:
                completer = WordCompleter(list(_users.keys()), ignore_case=True)
                user_mail = session.prompt(f"(User Feed) Pick user - press [tab] > ", completer=completer)
                if user_mail in _users:
                    break
                print("Please pick a valid user.")
            except EOFError:
                return
            except KeyboardInterrupt:
                return
        user_id = _users[user_mail]  # Retrieve user ID by email
        return user_id

    def select_user_exchange(self, uid: str) -> str:
        """
        Prompt the user to pick an exchange and return the selected exchange ID.

        This method interacts with the user through the command-line interface using the PromptSession from
        the prompt_toolkit library. It retrieves a list of exchanges associated with the given user ID (uid)
        from the RPC server and displays them to the user as options. The user is prompted to pick an exchange
        from the available options by typing the name of the exchange, with auto-completion support provided
        through the WordCompleter.

        Parameters:
            uid (str): A string representing the user ID for whom to select an exchange.

        Returns:
            str: The ID of the selected exchange as a string. If no exchanges are available for the user,
            the method returns the message "No exchanges for this user."

        Raises:
            None

        Example:
            Suppose we have a CTL object initialized as ctl = CTL() and a valid user ID stored in the uid
            variable. To prompt the user to pick an exchange, we can call the method as follows:

            >>> selected_exchange_id = ctl.select_user_exchange(uid)
            (User Feed) Pick exchange - press [tab] > Kraken
            >>> print(selected_exchange_id)
            'kraken1'

            In this example, the user typed "Kraken" and pressed [tab], and the method returned the exchange ID
            'kraken1' associated with the selected exchange "Kraken."
        """
        session = PromptSession()
        exchanges = self.RPC.users('exchange', {'uid': uid})
        if not exchanges:
            return "No exchanges for this user"

        _exchanges: dict = {}
        for exchange in exchanges:
            _exchanges[exchange['ex_named']] = exchange['ex_id']

        # Prompt user to pick an exchange
        while True:
            completer = WordCompleter(list(_exchanges.keys()), ignore_case=True)
            _exchange = session.prompt(f"(User Feed) Pick exchange - press [tab] > ", completer=completer)
            if _exchange in _exchanges:
                break
            print("Please pick a valid exchange.")

        ex_id = _exchanges[_exchange]  # Retrieve user ID by email
        return ex_id
