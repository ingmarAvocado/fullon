"""
Comments
"""
from libs import log
from libs.ctl.ctl_users_lib import CTL
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from tabulate import tabulate
from typing import Any

logger = log.fullon_logger(__name__)


class CTL(CTL):
    """
    The CTL class is responsible for managing symbol-related functionalities,
    such as listing symbols.
    """

    def print_crawler_menu(self, page: int = 1):
        """
        blah
        """
        session = PromptSession()
        sub_commands = ['add', 'del', 'next', 'prev']
        completer = WordCompleter(sub_commands, ignore_case=True)
        page_size = 30
        _profiles = []
        while True:
            post = ''
            _profiles = self.RPC.crawler('profiles', {'page': page,
                                                     'page_size': page_size})
            if _profiles:
                print("\n" + tabulate(_profiles, headers="keys", tablefmt="pretty"))
            else:
                print("\nNo profiles to display.")
            print("Type next/prev to change pages")
            try:
                command = session.prompt("(Crawler Shell)> ", completer=completer).strip().lower()
                if ' ' in command:
                    command, post = command.split(' ')
            except EOFError:  # Catch Ctrl+D and exit the loop
                break
            except KeyboardInterrupt:
                break
            match command:
                case 'add':
                    self._add_profile()
                case 'del':
                    self._del_profile(profiles=_profiles)
                case 'next':
                    page += 1
                case 'prev':
                    if page > 1:
                        page -= 1
                    else:
                        print("You are already on the first page.")

    def _add_profile(self):
        """
        blah
        """
        try:
            session = PromptSession()
            uid = self.select_user()
            sites = self.RPC.crawler('list', {})
            completer = WordCompleter(sites, ignore_case=True)
            site = session.prompt("(Crawler Shell/Add Profile) Pick site > ",
                                  completer=completer)
            completer = WordCompleter([], ignore_case=True)
            account = session.prompt("(Crawler Shell/Add Profile) account name > ",
                                     completer=completer)
            number_strings = [str(i) for i in range(1, 10 + 1)]
            completer = WordCompleter(number_strings, ignore_case=True)
            ranking = session.prompt("(Crawler Shell/Add Profile) ranking > ",
                                     completer=completer)
            completer = WordCompleter(['True', 'False'], ignore_case=True)
            contra = session.prompt("(Crawler Shell/Add Profile) is a contra > ",
                                    completer=completer)
            contra = True if contra == 'True' else False
            profile = {"uid": uid,
                       "site": site,
                       "account": account,
                       "ranking": int(ranking),
                       "contra": contra}
            if self.RPC.crawler('add', profile):
                print("Account added")
            else:
                print("Error, could not add account")
            return
        except (EOFError, KeyboardInterrupt):  # Catch Ctrl+D and exit the loop
            print("Operation canceled")
            return

    def _del_profile(self, profiles: Any):
        """
        Delete a profile based on user input.
        """
        _profiles = {}
        for profile in profiles:
            # Use fid as the key and a string representation as the value
            _profiles[str(profile['fid'])] = f"{profile['uid']}/{profile['site']}/{profile['account']}"

        # Create a WordCompleter with fids as the completion options
        fid_completer = WordCompleter(list(_profiles.keys()), ignore_case=True)
        session = PromptSession()
        # Present the prompt
        try:
            fid = session.prompt("(Crawler Shell/Del Profile) Pick account by fid> ",
                                 completer=fid_completer)
            if fid in _profiles:
                if self.RPC.crawler('del', {'fid': int(fid)}):  # Assuming 'del' expects an integer fid
                    print("Account deleted successfully.")
                else:
                    print("Error, could not delete account.")
            else:
                print("Invalid fid.")
        except (EOFError, KeyboardInterrupt):  # Catch Ctrl+D and Ctrl+C to exit the loop
            print("Operation cancelled.")
            return