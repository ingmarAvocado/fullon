#!/usr/bin/python3
"""
This is a command line tool for managing persea
"""
from __future__ import unicode_literals, print_function
import sys
from typing import List
from prompt_toolkit import PromptSession, print_formatted_text, HTML
from prompt_toolkit.key_binding import KeyBindings
from clint.textui import colored
from termcolor import cprint
from pyfiglet import figlet_format
from tabulate import tabulate
from libs import log, settings
from libs.settings_config import fullon_settings_loader  # pylint: disable=unused-import
from libs.secret import SecretManager

bindings = KeyBindings()
logger = log.fullon_logger(__name__)


def launch(argv: List[str]) -> None:
    """
    Launches commands based on the command line arguments.

    Args:
        argv (List[str]): A list of command line arguments.

    Returns:
        None
    """
    # Use Python's `match` statement to implement a simple command line interface
    match argv[1]:
        case 'view':
            try:
                if argv[2]:
                    view(key=argv[2])
                else:
                    print("- view secret_key")
            except IndexError:
                print("- view secret_key")
        case 'view_all':
            view_all()
        case 'add':
            try:
                add(key=argv[2], value=argv[3])
            except IndexError:
                print("- add secret_key secret_value")
        case 'delete':
            try:
                delete_secret(key=argv[2])
            except IndexError:
                print("- delete secret_key")
        case 'default_secrets':
            default_secrets()
        case 'help':
            print_help()
        case _:
            print_help()


def default_secrets() -> None:
    """
    Installs Persea default secrets.

    Returns:
        None
    """
    hush = SecretManager()
    hush.create_fullon_default_secrets()
    del hush


def view(key: int) -> None:
    """
    Views all of the available secret keys.

    Returns:
        str
    """
    hush = SecretManager()
    secret = hush.access_secret_version(secret_id=str(key))
    print(secret)


def view_all() -> None:
    """
    Views all of the available secret keys.

    Returns:
        None
    """
    hush = SecretManager()
    if hush.secrets:
        data = [["Name"]]
        for key in hush.secrets:
            name = "".join(key.name.split("/")[-1:])
            data.append([name])
    else:
        data = [["No secrets found."]]
    # Print the table
    del hush
    print(tabulate(data, headers="firstrow", tablefmt="fancy_grid"))


def add(key: str, value: str) -> None:
    """
    Adds a new secret to the Secret Manager.

    Args:
        key (str): The key to add.
        value (str): The value to associate with the key.

    Returns:
        None
    """
    hush = SecretManager()
    hush.add_secret_version(secret_id=key, payload=value)
    del hush


def delete_secret(key: str) -> None:
    """Delete a secret by key.

    Args:
        key (str): The key of the secret to delete.
    """
    hush = SecretManager()
    hush.delete_secret(secret_id=key)
    del hush


def print_help() -> None:
    """Print help information for the command-line tool."""
    helpstr = """
    Available commands:

    <b>view_all</b>,
    <b>view</b> secret_key,
    <b>add</b> secret_key secret_value,
    <b>delete</b> secret_key,
    <b>default_secrets</b>,
    <b>help</b>
    Version
    """
    print_formatted_text(HTML(helpstr))


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


def main() -> None:
    """Main routine for the command-line tool."""
    fig = figlet_format('Fullon Secret Manager', font='larry3d', width=120)
    print_colored_line('=', 'blue')
    cprint(fig, 'yellow', attrs=['bold'])
    print_colored_line('=', 'blue')
    print('Running Fullon Secret....   ' +
          colored.blue('Press CTRL-C to exit.'))
    argv = None
    session = PromptSession(key_bindings=bindings)
    while True:
        try:
            reply = session.prompt("(Fullon Secret)> ")
        except KeyboardInterrupt:
            logger.info("CTRL-C Pressed, exiting...")
            sys.exit()
        except EOFError:
            logger.info("CTRL-D Pressed, exiting...")
            sys.exit()
        if reply:
            jsonstring = reply
            reply = ' '.join(reply.split()).split(' ')
            argv = ['fullon']
            for entry in reply[0:2]:
                jsonstring = jsonstring.replace(entry, '')
                argv.append(entry)
            argv.append(jsonstring.lstrip())
            launch(argv=argv)
    logger.info("bye...")


if __name__ == "__main__":
    main()
