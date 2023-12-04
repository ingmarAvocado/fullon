#!/usr/bin/python3
"""
Fullon CTL Manager
"""
from __future__ import unicode_literals, print_function
import json
from clint.textui import puts, colored
from run import avail_components as comp
from libs.settings_config import fullon_settings_loader
from libs import log
from libs.ctl.ctl_lib import CTL
from tabulate import tabulate
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from run import avail_components as comp
from typing import List
import arrow

logger = log.fullon_logger(__name__)

_ctl = CTL()

RPC = _ctl.RPC
COMPONENTS = comp.get_components()


def bots():
    """
    Manage bots in the application.

    This function provides a command shell that allows users to interactively
    manage bots. It provides options to navigate through pages of bots, and
    commands to start, stop, edit, add, delete and view live bots.

    Args:
        argv: The argument vector. This is not currently used in the function,
              but is included for future extensions.

    Note:
        The commands supported in the shell include:
            'next': Go to the next page of bots.
            'prev': Go to the previous page of bots.
            'live': Show live bots.
            'start': Launch a bot.
            'stop': Stop a bot.
            'edit': Edit a bot.
            'add': Add a bot.
            'delete': Delete a bot.
            'exit': Exit the shell.
    """
    session = PromptSession()
    bots_sub_commands = COMPONENTS['bots']
    bots_completer = WordCompleter(bots_sub_commands, ignore_case=True)
    page = 1

    while True:
        _bots = _ctl.get_bot_list()
        if _bots:
            print("\n" + tabulate(_bots, headers="keys", tablefmt="pretty"))
        else:
            input("\nNo bots to display. press enter to continue > ")
            return

        print("Type next/prev to change pages")

        try:
            command = session.prompt("(Bots Shell)> ", completer=bots_completer).strip().lower()
            post = None
            if ' ' in command:
                command, post = command.split(' ')
        except EOFError:  # Catch Ctrl+D and exit the loop
            break
        except KeyboardInterrupt:
            break

        match command:
            case 'next':
                page += 1
            case 'prev':
                if page > 1:
                    page -= 1
                else:
                    print("You are already on the first page.")
                    continue
            case 'live':
                livebots = _ctl.show_live_bots()
            case 'start':
                _ctl.launch_bot(_bots, post)
            case 'stop':
                _ctl.stop_bot(_bots, post)
            case 'edit':
                _ctl.edit_bot(_bots, post)
            case 'add':
                _ctl.add_bot()
            case 'delete':
                _ctl.delete_bot(_bots)
            case 'exit':
                break
            case _:
                print(colored.red("Invalid command: "), command)
                print_comp_menu("bots")


def strategies():
    """
    A command-line function that manages trading strategies.

    This function provides an interactive shell interface for trading strategy management.
    Users can view a paginated list of strategies and navigate between pages using 'next' and 'prev' commands.
    Additionally, users can add new strategies or delete existing ones.

    Parameters:
    - argv: list
        Command-line arguments passed to the function.
    Returns:
    None. This function operates interactively and does not return a value.
    Raises:
    - EOFError: When Ctrl+D is pressed to end the command input.
    - KeyboardInterrupt: When Ctrl+C is pressed to interrupt the command input.

    Notes:
    - The function relies on external `COMPONENTS`, `PromptSession`, and `_ctl` variables/objects.
    - Strategies are displayed in a table format using the 'tabulate' function.
    - Page numbering starts from 1 and users can navigate between pages.

    Examples:
    >>> strategies(['add'])
    (strategies Shell)> add
    """
    session = PromptSession()
    strat_sub_commands = COMPONENTS['strategies']
    strat_completer = WordCompleter(strat_sub_commands, ignore_case=True)
    page = 1
    while True:
        _strats = _ctl.get_strat_list(page=page, minimal=True)
        if _strats:
            print("\n" + tabulate(_strats, headers="keys", tablefmt="pretty"))
        else:
            print("\nNo strategies to display.")
            return
        print("Type next/prev to change pages")
        try:
            command = session.prompt("(Strategies Shell)> ",
                                     completer=strat_completer).strip().lower()
        except EOFError:  # Catch Ctrl+D and exit the loop
            break
        except KeyboardInterrupt:
            break
        match command:
            case 'next':
                page += 1
            case 'prev':
                if page > 1:
                    page -= 1
                else:
                    print("You are already on the first page.")
                    continue
            case 'add':
                res = _ctl.add_strategies()
            case 'delete':
                strats = []
                for s in _strats:
                    strats.append(s['name'])
                if strats:
                    _ctl.del_strategy(strats=strats)
                else:
                    print("This system has no strategies, please add one first")
            case _:
                print("No such command")


def symbols():
    """
    A command-line function that manages symbols.

    This function provides an interactive shell interface for symbol management.
    Users can view a list of symbols, and add or delete them. Navigation through 
    multiple pages of symbols is supported with 'next' and 'prev' commands.
    Parameters:
    - argv: list
        Command-line arguments passed to the function.
    Returns:
    None. This function operates interactively.
    Raises:
    - EOFError: When Ctrl+D is pressed.
    - KeyboardInterrupt: When Ctrl+C is pressed.

    Notes:
    - The function relies on external `COMPONENTS`, `PromptSession`, and `_ctl` variables/objects.
    - The table view of symbols is formatted using the 'tabulate' function.
    """
    session = PromptSession()
    sub_commands = COMPONENTS['symbols']
    completer = WordCompleter(sub_commands, ignore_case=True)
    page = 1
    while True:
        post = ''
        _symbols = _ctl.get_symbol_list(minimal=True)
        if _symbols:
            print("\n" + tabulate(_symbols, headers="keys", tablefmt="pretty"))
        else:
            print("\nNo symbols to display.")
            return
        print("Type next/prev to change pages")
        try:
            command = session.prompt("(Symbols Shell)> ", completer=completer).strip().lower()
            if ' ' in command:
                command, post = command.split(' ')
        except EOFError:  # Catch Ctrl+D and exit the loop
            break
        except KeyboardInterrupt:
            break
        match command:
            case 'add':
                _ctl.add_symbol()
            case 'delete':
                _ctl.delete_symbol(symbol=post)


def tickers():
    """
    Prints all the tickers
    """
    session = PromptSession()
    sub_commands = COMPONENTS['tickers']
    completer = WordCompleter(sub_commands, ignore_case=True)
    _ticks = _ctl.get_ticks_list()
    if _ticks:
        print("\n" + tabulate(_ticks, headers="keys", tablefmt="pretty"))
    else:
        print("\nNo tickers to display.")
    try:
        input("Type anything to continue > ")
    except (EOFError, KeyboardInterrupt):
        pass
    return


def users():
    """
    Prints user's account data
    """
    session = PromptSession()
    commands = COMPONENTS['users']
    completer = WordCompleter(commands, ignore_case=True)
    accounts = _ctl.get_user_list(minimal=True)
    if accounts:
        print("\n" + tabulate(accounts, headers="keys", tablefmt="pretty"))
    else:
        print("\nNo tickers to display.")
    try:
        input("Type anything to continue > ")
    except (EOFError, KeyboardInterrupt):
        pass


def top():
    """
    Print the latest records fetched from an RPC call. The output table includes timestamp, type, key, and message columns.
    For records older than 2 minutes, the output line will be colored in red.

    Args:
        argv (Optional[List[str]], optional): Unused argument, only present for compatibility with command line interfaces. Defaults to None.
    """
    # Fetch and parse the response
    response: List[Dict[str, str]] = json.loads(RPC.get_top())

    column_order: List[str] = ["timestamp", "type", "key", "message"]

    # Reorder dictionaries and check for timestamps
    response_ordered: List[Dict[str, str]] = []
    now = arrow.utcnow()
    for record in response:
        ordered_record = dict(sorted(record.items(), key=lambda x: column_order.index(x[0])))
        timestamp = arrow.get(ordered_record['timestamp'])
        if (now - timestamp).total_seconds() > 120:  # older than 2 minutes
            ordered_record = {k: colored.red(v) for k, v in ordered_record.items()}
        response_ordered.append(ordered_record)

    # Print the table
    if response_ordered:
        print(tabulate(response_ordered, headers="keys", tablefmt="pretty"))
    else:
        print("\nAll services are turned off, use command <services>\n")


def services():
    """
    A command-line function that manages fullon services

    """
    session = PromptSession()
    commands = COMPONENTS['services']
    completer = WordCompleter(commands, ignore_case=True)
    subcmds = ['start', 'stop', 'restart']
    subcompleter = WordCompleter(subcmds, ignore_case=True)
    while True:
        try:
            command = session.prompt("(Services Shell) type command press <TAB> > ",
                                     completer=completer).strip().lower()
            if ' ' in command:
                command, subcmd = command.split(' ')
            else:
                subcmd = session.prompt("(Services Shell) type subcommand press <TAB> > ",
                                        completer=subcompleter).strip().lower()
        except EOFError:  # Catch Ctrl+D and exit the loop
            break
        except KeyboardInterrupt:
            break
        if command in COMPONENTS['services']:
            if subcmd in ['start', 'stop', 'restart']:
                res = RPC.services(command, subcmd)
                print(colored.green(res))
            else:
                print("Wrong subcommand")
        else:
            print("Wrong command")


def print_comp_menu(component: str):
    """Prints the available commands for a given component in color.

    Args:
        component: The component for which to print the commands.
    """
    if len(COMPONENTS[component]) == 0:
        return None

    # Prepare the header of the menu
    header = colored.cyan(f"AVAILABLE COMMANDS FOR {component.upper()}")

    # Prepare the list of commands
    commands = colored.magenta(', '.join(COMPONENTS[component]))

    # Create a table to print
    table = [[header], [commands]]

    # Print the table
    print(tabulate(table, tablefmt="plain"))


def help():
    """ description """
    components = comp.get_components()
    string = 'Commands: '
    for compo, commands in components.items():
        string += f"{colored.magenta(compo)}, "
    puts(string.rstrip(", "))
    # logger.info(mesg)


def validate_command(argv: list):
    """ description """
    components = comp.get_components()
    if argv[1] in components:
        if len(argv) <= 2:
            return True
        if argv[2] in components[argv[1]]:
            return True
        print_comp_menu(component=argv[1])
        # logger.info(colored.cyan("Sub command (%s) for (%s) not found."
        # %(argv[2], argv[1])))#run_help()
        return False
    mesg = f"Command ({argv[1]}) not found. Type help or h to view  all available commands."
    logger.info(colored.cyan(mesg))
    return False
