#!/usr/bin/python3
"""
Runs fullon_daemon
"""
from __future__ import unicode_literals, print_function
#from signal import signal, SIGINT
import shutil
import os
import signal
import subprocess
import time
from threading import Thread, Event
import argparse
import psutil
from termcolor import cprint
from pyfiglet import figlet_format
from clint.textui import colored
from libs import log, settings
from libs.settings_config import fullon_settings_loader  # pylint: disable=unused-import
from libs.bot_launcher import start as start_launcher, stop as stop_launcher
from libs.exchange import start_all, stop_all
from libs.database_ohlcv import start as startohlcv, stop as stopohlcv
from libs.database import start as startdb, stop as stopdb, WorkerError
from run import rpcdaemon_manager as rpc
from setproctitle import setproctitle

logger = log.fullon_logger(__name__)
thread: Thread

'''
def handler(signal_received: int, frame) -> None:
    """ Handle any cleanup here """
    del signal_received
    del frame
    try:
        thread.join()
        stop()
    except AssertionError:
        pass
    logger.info('SIGINT or CTRL-C detected. Exiting gracefully')
    sys.exit()
'''


def kill_processes(name):
    # Get list of all running processes
    try:
        pids = subprocess.check_output(["pgrep", "-f", name])
    except subprocess.CalledProcessError:
        return
    if not pids:
        return

    pids = pids.splitlines()
    _pids = [int(x.decode('utf-8')) for x in pids]
    pids = sorted(_pids, reverse=True)
    # Send SIGTERM signal to each process
    my_pid = os.getpid()
    try:
        pids.remove(my_pid)
    except ValueError:
        pass
    for pid in pids:
        try:
            os.kill(int(pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
        except PermissionError:
            logger.error("Permission error: can't kill pid %s", pid)
    '''
    time.sleep(1)
    for pid in pids:
        try:
            os.kill(int(pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
    '''


def start_pmanager() -> None:
    """
    Start the process manager.
    This function initializes the ProcessManager from the system_manager module,
    logs a message indicating that the ProcessManager is running, and then starts
    the process monitor.
    Returns:
        None
    """
    pass


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


def kill_hard():
    try:
        logger.warning(colored.red("Quitting Fullon... stopping threads..."))
        stop_launcher()
        stop_all()
        for process in ['Fullon', 'fullon_daemon.py']:
            kill_processes(process)
    except WorkerError:
        pass
    # pid = os.getpid()
    # os.kill(pid, signal.SIGTERM)
    # time.sleep(1)
    # if os.path.exists(f"/proc/{pid}"):
    #    os.kill(pid, signal.SIGKILL)
    pass


def kill_soft():
    logger.warning(colored.red("Quitting Fullon... stopping threads..."))
    rpc.stop_full()
    thread.join()
    stop_all()
    kill_processes('Fullon')


def main(cli_args: argparse.Namespace) -> None:
    """
    Main function to manage the execution of the trading bot based on the provided arguments.

    Args:
        cli_args: argparse.Namespace object containing the parsed command line arguments.
    """
    # Check if the "stop" argument is passed, and stop components accordingly
    global thread

    if cli_args.stop:
        kill_processes('Fullon')
        kill_processes('fullon_daemon')
        return
    # Set up signal handling for graceful shutdown on SIGINT or CTRL-C
    #signal(SIGINT, handler)

    # Remove the 'tmp' directory if it exists and create a new one
    try:
        shutil.rmtree('tmp/')
    except FileNotFoundError:
        pass
    os.mkdir('tmp')

    # Print the Fullon Crypto Trading Bot title using PyFiglet
    figlet = figlet_format('Fullon Crypto Trading Bot', font='larry3d', width=120)

    print_colored_line('=', 'blue')
    cprint(figlet, 'yellow', attrs=['bold'])
    print_colored_line('=', 'blue')

    print(colored.yellow(" Fullon Crypto Trading Bot FERI7701027FL9 Crypto Services (C) 2023"))
    print_colored_line('-', 'magenta')

    # Check if an instance of the trading bot is already running and exit if it is
    for process in psutil.process_iter(['pid', 'name', 'username']):
        if "Fullon" in process.name():
            if os.getuid() == process.uids().real:
                print(colored.red("A daemon is already running, use -x to stop it"))
                return
    logger.info("Press CTRL-C to quit")
    try:
        setproctitle("Fullon Daemon")
        startohlcv()
        startdb()
        start_all()
        start_launcher()
        stop_event = Event()
        setproctitle("Fullon Daemon")
        # Start the ProcessManager and RPC server
        thread = Thread(target=rpc.pre_rpc_server,
                        args=(cli_args.full, cli_args.services, stop_event))
        thread.start()
        logger.warning("Console detached")
        while thread.is_alive():
            time.sleep(2)
    except KeyboardInterrupt:
        try:
            stop_event.set()
            stop_launcher()
            stop_all()
            stopdb()
            stopohlcv()
            time.sleep(1)
            kill_hard()
        except (EOFError, KeyboardInterrupt):
            kill_hard()
        print("bye...")
        exit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fullon Daemon Help Page")
    parser.add_argument("-f", "--full", action="store_true",
                        help="Starts all components")
    parser.add_argument("-s", "--services", action="store_true",
                        help="Starts all components, but not individual bots")
    parser.add_argument("-x", "--stop", action="store_true",
                        help="Stops components")

    args = parser.parse_args()
    main(args)
