#!/usr/bin/python3
"""
This is a command line tool for managing persea
"""
from __future__ import unicode_literals, print_function
import sys
from typing import List
from prompt_toolkit import PromptSession, print_formatted_text, HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.shortcuts import clear
from clint.textui import colored
from termcolor import cprint
from pyfiglet import figlet_format
from libs import log, settings
from libs.settings_config import fullon_settings_loader  # pylint: disable=unused-import
from libs.simulator_prompts import Prompts
from libs.database import start as start_database, stop as stop_database
from libs.database_ohlcv import start as start_ohlcv, stop as stop_ohlcv
from libs.simul_launcher import simulator


bindings = KeyBindings()
logger = log.fullon_logger(__name__)

'''
BOT = {"bot_id": "00000000-0000-0000-0000-000000000006",
       "periods": 8200,
       "warm_up": 50,
       "xls": 0,
       "verbose": "0",
       "visual": False,
       "params": params2}
'''

start_database()
start_ohlcv()
simulator.start()
PROMPTS = Prompts()


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
        case 'users':
            PROMPTS.set_user()
        case 'bots':
            PROMPTS.set_bot()
            clear()
            print("\nBot loaded")
        case 'strat':
            PROMPTS.set_str_params()
        case 'feeds':
            PROMPTS.set_feeds()
        case 'params':
            PROMPTS.set_simul_params()
        case 'run':
            PROMPTS.run_simul()
        case 'save':
            PROMPTS.save_simul()
        case 'load':
            PROMPTS.load_simul()
            clear()
            print("\nSimulation loaded successfully.")
        case 'help':
            print_help()
        case _:
            print_help()


def print_help() -> None:
    """Print help information for the command-line tool."""
    helpstr = """
    Available commands:

    <b>users</b> Pick the user,
    <b>bots</b> Pick the bot,
    <b>strat</b> Modify strategy params,
    <b>feeds</b> Modify feeds,
    <b>params</b> Modify simul params,
    <b>run</b> Run simulation,
    <b>save</b> Save simulation,
    <b>load</b> Load Simulation,
    <b>help</b>
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


def sim_exit():
    global sim
    logger.info("bye...")
    stop_database()
    stop_ohlcv()
    simulator.stop()
    exit()


def main() -> None:
    """Main routine for the command-line tool."""
    commands = ['users', 'bots', 'strat', 'feeds', 'params', 'run', 'save', 'load', 'help']
    completer = WordCompleter(commands, ignore_case=True)
    fig = figlet_format('Fullon Simulator', font='larry3d', width=120)
    print_colored_line('=', 'blue')
    cprint(fig, 'yellow', attrs=['bold'])
    print_colored_line('=', 'blue')
    print('Running Fullon Simulator....   ' +
          colored.blue('Press CTRL-C to exit. Type "help" for help'))

    argv = None
    session = PromptSession(
        key_bindings=bindings,
        completer=completer,
        complete_style=CompleteStyle.MULTI_COLUMN,
        history=FileHistory('tmp/simulator_history.txt')
    )
    while True:
        if PROMPTS.STR_PARAMS:
            print(colored.magenta('\nStrategy params:'))
            print(', '.join([
                f"{colored.blue(key)}: {value}"
                for key, value in PROMPTS.STR_PARAMS.items()
                if value is not None
            ]))
        if PROMPTS.SIMUL_PARAMS:
            print(colored.magenta('Simulation params:'))
            result = ', '.join([
                f"{colored.blue(key)}: {value}"
                for key, inner_dict in PROMPTS.SIMUL_PARAMS.items()
                for inner_key, value in inner_dict.items()
                if value not in {False, None}
            ])
            print(result)
        print(f"\nAvailable commands: {commands}")
        try:
            if 'No bot set' in {PROMPTS.BOT[1]}:
                pre_prompt = f"({PROMPTS.USER}: <ansired>{PROMPTS.BOT[1]}</ansired>)"
            else:
                pre_prompt = f"({PROMPTS.USER}: <ansigreen>{PROMPTS.BOT[1]}</ansigreen>)"           
            pre_prompt = HTML(f'<ansibrightmagenta>Fullon Simulator {pre_prompt}> </ansibrightmagenta>')
            toolbar_text = HTML('<b>Press [Ctrl-C] to quit | [TAB] for autocompletion | "help" for help</b>')
            reply = session.prompt(pre_prompt, bottom_toolbar=toolbar_text)
        except KeyboardInterrupt:
            logger.info("CTRL-C Pressed, exiting...")
            sim_exit()
        except EOFError:
            logger.info("CTRL-D Pressed, exiting...")
            sim_exit()
        if reply:
            jsonstring = reply
            reply = ' '.join(reply.split()).split(' ')
            argv = ['fullon']
            for entry in reply[0:2]:
                jsonstring = jsonstring.replace(entry, '')
                argv.append(entry)
            argv.append(jsonstring.lstrip())
            launch(argv=argv)


if __name__ == "__main__":
    main()