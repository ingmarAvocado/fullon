#!/usr/bin/python3
"""
Fullon Installer Script

This script is responsible for setting up the necessary infrastructure for Fullon application.
It sets up databases, installs necessary SQL schemas, prepares cache and performs installations
of strategies, exchanges and optionally, a demo.

Usage:
    python install_fullon.py [--demo]

Optional flags:
    -d, --demo: Install a demo
    -f, --full: Full install
    -r, --reinstalls: Only reinstalls strategies and exchanges
"""

import argparse
from libs import log, settings
from libs.settings_config import fullon_settings_loader  # pylint: disable=unused-import
from libs.database import start as start_database, stop as stop_database
from libs.database_ohlcv import start as start_ohlcv, stop as stop_ohlcv
from libs.models.install_model import Database as Database_Install
from libs.models.ohlcv_model import Database as Database_ohlcv
from libs.cache import Cache
from run.install_manager import InstallManager
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from tabulate import tabulate

settings.LOG_LEVEL = "logging.INFO"
logger = log.fullon_logger(__name__)


def list_backups():
    """
    lists backups
    """
    backup = InstallManager()
    results = backup.list_backups()
    sorted_results = sorted(results, key=lambda x: x['num'], reverse=False)[:20]

    # Define the headers for the table
    headers = ["Number", "Backup Name", "Size"]

    # Extract required fields for tabulation
    table_data = [(item['num'], item['name'], item['size']) for item in sorted_results]

    # Use tabulate to print the table
    print(tabulate(table_data, headers=headers, tablefmt="grid"))


def make_backups():
    """
    makes backups
    """
    logger.info("Starting Backup")
    backup = InstallManager()
    backup.make_backup(full=True)
    logger.info("Backup complete")


def restore():
    """
    Recover backup.
    """
    dbase = Database_Install()
    dbase.clean_base()
    dbase.create_database()

    backup = InstallManager()
    results = backup.list_backups()

    # Sort results by 'num' and take the most recent 20
    sorted_results = sorted(results, key=lambda x: x['num'], reverse=True)[:20]

    # Get the names of the backups for the WordCompleter
    backup_names = [item['name'] for item in sorted_results]
    session = PromptSession()
    completer = WordCompleter(backup_names, ignore_case=True)
    name = None
    while True:
        try:
            name = session.prompt("Pick backup press <tab> > ", completer=completer).strip().lower()
            if name in backup_names:
                break
            else:
                print("Invalid choice. Please select a valid backup.")
        except EOFError:  # Catch Ctrl+D and exit the loop
            return
        except KeyboardInterrupt:  # Catch Ctrl+C and exit the loop
            return
    backup.recover_backup(name=name)


def install_fullon(cli_args: argparse.Namespace) -> None:
    """
    Handles Fullon installation process

    Parameters:
    cli_args (argparse.Namespace): Command line arguments

    Returns:
    None
    """

    # Initialize the InstallManager and run necessary pre-install checks and installation tasks
    if cli_args.full:
        dbase = Database_Install()
        dbase.clean_base()  # Clean base tables
        dbase.install_base_sql()  # Install base SQL
        dbase.install_ohlcv()  # Install OHLCV
        logger.info("Databases and tables have been installed")

        # Setup database for OHLCV
        with Database_ohlcv(exchange='exchange', symbol='symbol') as dbase:
            dbase.install_timescale()  # Install timescale
            dbase.install_timescale_tools()  # Install timescale tools
    # Initialize Install Manager
    install = InstallManager()

    if cli_args.full or cli_args.reinstalls:
        # Install strategies and exchanges
        logger.info("Installing the basic SQL schema")
        stop_database()
        start_database()
        install.install_strategies()
        logger.info("Strategies Installed")
        install.install_exchanges()
        logger.info("Exchanges Installed")
        install.install_crawlers()
        logger.info("Crawlers Installed")

        # Prepare the cache
        logger.info("Preparing cache")
        install.install_cache()  # Install cache
        with Cache() as store:
            store.prepare_cache()
        logger.info("Installation complete")

    # If the demo flag was set, install the demo
    if cli_args.demo:
        logger.info("Installing demo")
        install.install_demo()


def switch(cli_args: argparse.Namespace):
    if cli_args.full or cli_args.demo or cli_args.reinstalls:
        install_fullon(cli_args=cli_args)
    if cli_args.backup:
        make_backups()
    if cli_args.list:
        list_backups()
    if cli_args.restore:
        restore()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fullon Installer Help Page")
    parser.add_argument("-d", "--demo", action='store_true', help="Install demo data")
    parser.add_argument("-f", "--full", action='store_true', help="Full Install")
    parser.add_argument("-r", "--reinstalls", action='store_true', help="Only reinstalls strategies and exchanges")
    parser.add_argument("-b", "--backup", action='store_true', help="backs database up")
    parser.add_argument("-R", "--restore", action='store_true', help="restores database")
    parser.add_argument("-l", "--list", action='store_true', help="lists databases available for restore")
    args = parser.parse_args()
    start_database()
    start_ohlcv()
    switch(args)
    stop_database()
    stop_ohlcv()
