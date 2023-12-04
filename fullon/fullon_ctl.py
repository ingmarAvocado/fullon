#!/usr/bin/python3
"""
This module helps launch the fullon CLI interface.
"""
from __future__ import unicode_literals, print_function
import sys
from typing import List
from setproctitle import setproctitle
from clint.textui import colored
from termcolor import cprint
from pyfiglet import figlet_format
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter
from run import ctl_manager as ctl
from libs import log
from run import avail_components as comp
import os


logger = log.fullon_logger(__name__)
bindings = KeyBindings()


class FullonSwitch:  # pylint: disable=too-few-public-methods
    """FullonSwitch is a command dispatcher for the Fullon CLI."""

    argv: []

    def exec(self, argv: List[str]) -> None:
        """Execute the appropriate command based on the given arguments.

        Args:
            argv (List[str]): A list of command-line arguments.
        """
        self.argv = argv
        default = "Unknown option"
        name = argv[1]

        if name == "h":
            name = "help"

        # Get the method from 'ctl'
        method = getattr(ctl, name, None)

        # Check if the method exists
        if method:
            # Call the method with parameters
            return method()
        else:
            # If the method doesn't exist, print an error message
            print(default)


def print_colored_line(char: str, color: str) -> None:
    """
    Prints a colored line using the given character and color.

    Args:
        char (str): The character to be repeated to form the line.
        color (str): The color to be used for the line.

    Returns:
        NoReturn: This function does not return any value.
    """
    cprint(char * 80, color, attrs=['bold'])


def main(argv: List[str]) -> None:
    """Main function to execute the Fullon CLI command.

    Args:
        argv (List[str]): A list of command-line arguments.
    """
    ctl.validate_command(argv)
    switch = FullonSwitch()
    switch.exec(argv)


@bindings.add('c-c')
def _(event):
    """ Exit when `c-c` is pressed. """
    logger.info("Bye...\n")
    print("\n")
    event.app.exit()
    sys.exit()


@bindings.add('c-d')
def _(event):
    """ Exit when `c-d` is pressed. """
    logger.info("Bye...\n")
    print("\n")
    event.app.exit()
    sys.exit()


if __name__ == "__main__":
    setproctitle("Fullon Trading CTL")
    figlet = figlet_format('Fullon Crypto Trading Bot CTL', font='larry3d', width=120)
    print_colored_line('=', 'blue')
    cprint(figlet, 'red', attrs=['bold'])
    print_colored_line('=', 'blue')
    print(colored.yellow(" Fullon Crypto Trading Bot FERI7701027FL9 Crypto Services (C) 2023"))
    print_colored_line('-', 'magenta')
    components = comp.get_components()
    # Get the method names (keys of the dictionary)
    method_names = list(components.keys())
    method_completer = WordCompleter(method_names, ignore_case=True)

    # Pass the completer to PromptSession
    session = PromptSession(history=FileHistory("fullon_history.txt"),
                            key_bindings=bindings,
                            completer=method_completer)
    MESG = 'Running Fullon Shell....   '+colored.blue('Press CTRL-C to exit.')
    logger.info(MESG)
    logger.info('Fullon Crypto Trading Bot FERI7701027FL9 Crypto Services (C) 2023')
    ARGS = None
    try:
        if ctl.RPC.rpc_test() == "fullon":
            logger.info(colored.green("Connected to daemon!\n"))
            mesg = "----------------------------------------------------------------\n"
            mesg += "                         FULLON CTL V 1.0                      \n"
            mesg += "----------------------------------------------------------------\n"
            print(colored.cyan(mesg))
            while True:
                ctl.help()
                ctl.top()
                reply = session.prompt("(Fullon Shell)> ")
                if ctl.RPC.rpc_test() == "fullon":
                    jsonstring = reply
                    reply = ' '.join(reply.split()).split(' ')
                    ARGS = ['fullon']
                    for e in reply[0:2]:
                        jsonstring = jsonstring.replace(e,'')
                        ARGS.append(e)
                    ARGS.append(jsonstring.lstrip())
                    main(argv=ARGS)
                #os.system('clear')
    except ConnectionRefusedError:
        logger.warning(colored.red("Connection Refused: Is daemon up and running?\n"))
        sys.exit()
