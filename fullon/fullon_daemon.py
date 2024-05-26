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
from libs.database_ohlcv import start as startohlcv, stop as stopohlcv
from libs.database import start as startdb, stop as stopdb, WorkerError
from run.process_manager import ProcessManager
from run import rpcdaemon_manager as rpc
from setproctitle import setproctitle
import sys


logger = log.fullon_logger(__name__)
thread: Thread
threas2: Thread
stop_event = Event()
pmanager = ProcessManager()
not_stopping = True
ctrlc = 0


def ignore_signal(sig, frame):
    global ctrlc
    process_name = subprocess.check_output(["ps", "-p", str(os.getpid()), "-o", "comm="], encoding="utf-8").strip()
    if 'Daemon' in process_name:
        logger.info("SIGINT received again, but ignoring since shutdown is in progress %s try", (ctrlc))
        ctrlc += 1
        if ctrlc > 5:
            logger.info("CTRL-C pressed more than 5 times, hard kill in progress")
            kill_processes('Fullon', manual=True)
            kill_processes('fullon_daemon', manual=True)
            time.sleep(1)
            exit()


def signal_handler(sig, frame):
    """
    Cntrl-c shutdown
    """
    global not_stopping
    signal.signal(signal.SIGINT, ignore_signal)
    process_name = subprocess.check_output(["ps", "-p", str(os.getpid()), "-o", "comm="], encoding="utf-8").strip()
    if 'Daemon' in process_name:
        if not_stopping:
            not_stopping = False
            logger.warning("Stopping components")
            stops_components()
            sys.exit(0)
        else:
            kill_processes('Fullon', manual=True)
            kill_processes('fullon_daemon', manual=True)
            kill_hard()


def kill_processes(name, manual: bool = False):
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
    #import ipdb
    #ipdb.set_trace()
    for pid in pids:
        try:
            os.kill(int(pid), signal.SIGTERM)
            if manual:
                os.kill(int(pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError:
            logger.error("Permission error: can't kill pid %s", pid)


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
    """
    Hard kills fullon processes
    """
    try:
        logger.warning(colored.red("Quitting Fullon... stopping threads..."))
        stop_launcher()
        for process in ['Fullon', 'fullon_daemon.py']:
            kill_processes(process)
    except WorkerError:
        pass
    pass


def print_banners():
    """
    Prints banners
    """
    # Print the Fullon Crypto Trading Bot title using PyFiglet
    figlet = figlet_format('Fullon Crypto Trading Bot', font='larry3d', width=120)

    print_colored_line('=', 'blue')
    cprint(figlet, 'yellow', attrs=['bold'])
    print_colored_line('=', 'blue')

    print(colored.yellow(" Fullon Crypto Trading Bot FERI7701027FL9 Crypto Services (C) 2023"))
    print_colored_line('-', 'magenta')


def start_components(cli_args):
    """
    Starts fullon components
    """
    global thread, stop_event, thread2
    setproctitle("Fullon Daemon")
    startohlcv()
    startdb()
    start_launcher()
    setproctitle("Fullon Daemon")
    # Start the ProcessManager and RPC server
    thread = Thread(target=rpc.pre_rpc_server,
                    args=(cli_args.full, cli_args.services, stop_event))
    thread.start()
    logger.warning("Console detached")
    thread2 = Thread(target=pmanager.check_services, args=([stop_event]))
    thread2.start()


def stops_components():
    """
    Stops fullon services
    """
    global thread, thread2, stop_event
    stop_event.set()
    try:
        thread2.join(timeout=1)
        if thread and thread.is_alive():
            thread.join(timeout=5)
        stop_launcher()
        stopdb()
        stopohlcv()
        kill_hard()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    finally:
        logger.info("Shutdown complete.")


def while_alive():
    '''
    Checks whether rpc server thread is alive
    '''
    global thread
    while thread.is_alive():
        time.sleep(1)


def other_instances() -> bool:
    '''
    Check if an instance of the trading bot is already running and exit if it is
    '''
    for process in psutil.process_iter(['pid', 'name', 'username']):
        if "Fullon" in process.name():
            print(process.name)
            if os.getuid() == process.uids().real:
                return True
    return False


def main(cli_args: argparse.Namespace) -> None:
    """
    Main function to manage the execution of the trading bot based on the provided arguments.

    Args:
        cli_args: argparse.Namespace object containing the parsed command line arguments.
    """
    # Check if the "stop" argument is passed, and stop components accordingly

    if cli_args.stop:
        kill_processes('Fullon', manual=True)
        kill_processes('fullon_daemon', manual=True)
        return
    try:
        shutil.rmtree('tmp/')
    except FileNotFoundError:
        pass
    for folder in ['tmp', 'pickle', 'predictors', 'crawler_media']:
        try:
            os.mkdir(folder)
        except FileExistsError:
            pass
    print_banners()
    if other_instances():
        print(colored.red("A daemon is already running, use -x to stop it"))
        return
    logger.info("Press CTRL-C to quit")

    try:
        start_components(cli_args=cli_args)
        while_alive()
    except KeyboardInterrupt:
        print("ACCAAAAAAAAAAA")
        #stops_components()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    parser = argparse.ArgumentParser(description="Fullon Daemon Help Page")
    parser.add_argument("-f", "--full", action="store_true",
                        help="Starts all components")
    parser.add_argument("-s", "--services", action="store_true",
                        help="Starts all components, but not individual bots")
    parser.add_argument("-x", "--stop", action="store_true",
                        help="Stops components")

    args = parser.parse_args()
    main(args)
