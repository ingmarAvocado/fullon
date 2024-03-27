#!/usr/bin/python3
"""
rpcdaemon_manager
"""
from __future__ import unicode_literals, print_function
import sys
import os
import time
import json
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
from socketserver import ThreadingMixIn
import psutil
from libs.exchange import start_all  # pylint: disable=no-name-in-module
from libs import settings, log
from libs.structs.symbol_struct import SymbolStruct
from run import system_manager
from run import avail_components as comp

logger = log.fullon_logger(__name__)

handler: dict = {}
handler['tick'] = system_manager.TickManager()
handler['ohlcv'] = system_manager.OhlcvManager()
handler['account'] = system_manager.AccountManager()
handler['bot'] = system_manager.BotManager()
handler['install'] = system_manager.InstallManager()
handler['user'] = system_manager.UserManager()
handler['bot_status'] = system_manager.BotStatusManager()
handler['crawler'] = system_manager.CrawlerManager()

COMPONENTS = comp.get_components()


# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
    """ class """
    rpc_paths = ('/RPC2',)


class ThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass


def daemon_startup():
    """ description """
    if find_another_daemon():
        logger.warning("Another daemon is running, can't run until its off")
        sys.exit()
    handler['install'].install_exchanges()
    try:
        handler['install'].install_strategies()
    except (EOFError, SyntaxError) as error:
        logger.error("Can't install strategies: %s", str(error))
        return False
    handler['install'].install_crawlers()
    handler['install'].install_cache()
    logger.info("Cache component ready")
    return True


def rpc_test():
    """ description """
    return "fullon"


def stop_component(component: str) -> str:
    """ description """
    response = ""
    try:
        match component:
            case "tick":
                handler['tick'].stop_all()
                response = "Tick stopped"
            case "ohlcv":
                handler['ohlcv'].stop_all()
                response = "ohlcv stopped"
            case "account":
                handler['account'].stop_all()
                response = "account stopped"
            case "bot":
                handler['bot'].stop_all()
                del handler['bot']
                handler['bot'] = system_manager.BotManager()
                response = "bot stopped"
            case "bot_status":
                handler['bot_status'].stop()
                response = "bot status stopped"
            case 'crawler':
                handler['crawler'].stop()
                response = "CrawlerStopped"
    except KeyboardInterrupt:
        response = "keyboard interrupt"
    return response


def get_top() -> str:
    """ gets the table of processes for fullon"""
    proc = system_manager.ProcessManager()
    top = proc.get_top()
    top = json.dumps(top)
    return top


def component_on(component):
    """ description """
    match component:
        case "tick":
            if handler['tick'].started:
                return True
        case "ohlcv":
            if handler['ohlcv'].started:
                return True
        case "account":
            if handler['account'].started:
                return True
        case "bot":
            if handler['bot'].started:
                return True
        case "bot_status":
            if handler['bot_status'].started:
                return True
        case "crawler":
            if handler['crawler'].started:
                return True
    return False


def start_ohlcv():
    """ description """
    if not component_on('ohlcv'):
        # This will launch the update OHLCV tables process
        if not component_on('ohlcv'):
            handler['ohlcv'].run_loop()
            return "OHLCV started"
    return "OHLCV already running"


def start_accounts():
    """ description """
    if not component_on('account'):
        if not component_on('tick'):
            logger.info(tickers('start'))
        handler['account'].run_account_loop()
        return "Accounts launched"
    return "Accounts already running"


def start_tickers() -> str:
    """
    """
    if not component_on('tick'):
        handler['tick'].run_loop()
        return "Ticker Launched"
    return "Ticker already running"


def start_crawler() -> str:
    """
    """
    handler['crawler'].run_loop()
    return "Ticker already running"


def start_bot_status() -> str:
    """
    """
    if not component_on('bot_status'):
        handler['bot_status'].run_loop()
        return "Bot status launched"
    return "Bot Status already running"


def start_bots():
    """ description """
    if not component_on('bot'):
        start_services()
        handler['bot'].run_bot_loop()
        return "Bots launched"
    return "Bots already running"


def start_full():
    """ description """
    if not component_on('tick'):
        logger.info(start_tickers())
    if not component_on('account'):
        logger.info(start_accounts())
    if not component_on('ohlcv'):
        logger.info(start_ohlcv())
        time.sleep(15)
    if not component_on('bot_status'):
        logger.info(start_bot_status)
    if not component_on('bots'):
        logger.info("Starting Bots")
        logger.info(start_bots())
    if not component_on('bots'):
        logger.info("Starting Crawler")
        logger.info(start_crawler())
    return "Full services started"


def stop_full():
    """ description """
    stop_component(component='bot')
    stop_component(component='bot_status')
    stop_component(component='account')
    stop_component(component='ohlcv')
    stop_component(component='tick')
    return "Full services stopped"


def check_services() -> bool:
    """ description """
    services = ['ohlcv', 'tick', 'account', 'bot_status']
    for service in services:
        if not component_on(service):
            return False
    return True


def start_services():
    """ description """
    if not component_on('tick'):
        logger.info(start_tickers())
    if not component_on('account'):
        logger.info(start_accounts())
    if not component_on('ohlcv'):
        logger.info(start_ohlcv())
    if not component_on('bot_status'):
        logger.info(start_bot_status())
    return "Services started"


def stop_services():
    """ description """
    stop_component(component='bot_status')
    stop_component(component='tick')
    stop_component(component='ohlcv')
    stop_component(component='account')
    stop_component(component='crawler')
    return "Services stopped"


def services(cmd, subcmd):
    """
    Execute accounts commands with given parameters.

    Args:
        cmd: The command to execute, can be 'list', 'btc, 'stop' or 'start'.
        params: The parameters to use for the command execution.

    Returns:
        The result of the command execution or an error message.

    Raises:
        KeyError: An error occurred accessing the command.
    """
    result = f"Error: could not execute {cmd} with subcmd {subcmd}"
    if cmd not in COMPONENTS['services']:
        return "Error: Invalid command"
    if subcmd not in ['start', 'stop', 'restart']:
        return "Error: Invalid command, only start, stop and restart are available"
    match cmd:
        case 'accounts':
            match subcmd:
                case 'start':
                    result = start_accounts()
                case 'stop':
                    result = stop_component('account')
                case 'restart':
                    stop_component('account')
                    start_accounts()
                    result = "Accounts restarted"
        case 'tickers':
            match subcmd:
                case 'start':
                    result = start_tickers()
                case 'stop':
                    result = stop_component('tick')
                case 'restart':
                    stop_component('tick')
                    start_tickers()
                    result = "Tickers restarted"
        case 'ohlcv':
            match subcmd:
                case 'start':
                    result = start_ohlcv()
                case 'stop':
                    result = stop_component('ohlcv')
                case 'restart':
                    stop_component('ohlcv')
                    start_ohlcv()
                    result = "Ohlcv restarted"
        case 'bot_status':
            match subcmd:
                case 'start':
                    result = start_bot_status()
                case 'stop':
                    result = stop_component('bot_status')
                case 'restart':
                    stop_component('bot_status')
                    start_bot_status()
                    result = "Bot status restarted"
        case 'bots':
            match subcmd:
                case 'start':
                    result = start_bots()
                case 'stop':
                    result = stop_component('bots')
                case 'restart':
                    stop_component('bots')
                    start_bots()
                    result = "Bots restarted"
        case 'services':
            match subcmd:
                case 'start':
                    result = start_services()
                case 'stop':
                    result = stop_services()
                case 'restart':
                    stop_services()
                    start_services()
                    result = "Services restarted"
        case 'full':
            match subcmd:
                case 'start':
                    result = start_all()
                case 'stop':
                    result = stop_full()
                case 'restart':
                    stop_full()
                    start_all()
                    result = "Services and bots restarted"
    return result


def tickers(cmd, params: dict = {}):
    """
    Execute tickers commands with given parameters.

    Args:
        cmd: The command to execute, can be 'list', 'btc, 'stop' or 'start'.
        params: The parameters to use for the command execution.

    Returns:
        The result of the command execution or an error message.

    Raises:
        KeyError: An error occurred accessing the command.
    """
    results = f"Error: could not execute {cmd} with params {params}"
    match cmd:
        case 'list':
            results = handler['tick'].get_tickers()
        case 'btc':
            pass
            #return handler['tick'].btc_ticker()
    return results


def strategies(cmd, params: dict = {}):
    """
    Execute strategy commands with given parameters.

    Args:
        cmd: The command to execute, can be 'list', 'user_list' or 'add'.
        params: The parameters to use for the command execution.

    Returns:
        The result of the command execution or an error message.

    Raises:
        KeyError: An error occurred accessing the command.
    """
    results = f"Error: could not execute {cmd} with params {params}"
    match cmd:
        case 'list':
            page = params.get('page')
            page_size = params.get('page_size')
            if page is None or page_size is None:
                results = "Error: Missing 'page' or 'page_size' parameter for 'list' command."
            else:
                results = handler['install'].list_cat_strategies(
                    page=page, page_size=page_size)
        case 'user_list':
            uid = params.get('uid')
            if uid is None:
                results = "Error: Missing 'uid' parameter"
            else:
                results = handler['install'].list_user_strategies(uid=uid)
        case 'reload':
            results = handler['install'].install_strategies()
        case 'add_user':
            strat = params.get('strat')
            if isinstance(strat, dict):
                results = handler['user'].add_bot_strategy(strategy=strat)
            else:
                return "Error: Parameter strat is missing"
        case 'get_bots':
            if params.get('cat_str_name') is None:
                results = f"Error: Missing 'cat_str_name' parameter for '{cmd}' command."
            else:
                results = handler['install'].list_strategy_bots(
                    cat_str_name=params['cat_str_name'])
        case 'del_cat_str':
            if params.get('cat_str_name') is None:
                results = f"Error: Missing 'cat_str_name' parameter for '{cmd}' command."
            else:
                results = handler['install'].del_cat_str(
                    cat_str_name=params['cat_str_name'])
    return results


def symbols(cmd, params: dict = {}):
    """
    Execute symbols commands with given parameters.

    Args:
        cmd: The command to execute, can be 'list' or 'add'.
        params: The parameters to use for the command execution.

    Returns:
        The result of the command execution or an error message.

    Raises:
        KeyError: An error occurred accessing the command.
    """
    results = f"Error: could not execute {cmd} with params {params}"
    match cmd:
        case 'list':
            page = params.get('page')
            page_size = params.get('page_size')
            if page is None or page_size is None:
                results = "Error: Missing 'page' or 'page_size' parameter for 'list' command."
            else:
                results = handler['install'].list_symbols(
                    page=page, page_size=page_size)
        case 'add':
            symbol = params.get('symbol')
            if symbol:
                results = handler['install'].install_symbol(symbol=SymbolStruct.from_dict(symbol))
            else:
                results = 'Parameter symbol is missing'
        case 'delete':
            try:
                symbol_id = int(params.get('symbol_id'))
                if symbol_id:
                    results = handler['install'].remove_symbol(symbol_id=symbol_id)
                else:
                    results = 'Parameter symbol_id is missing'
            except TypeError:
                results = "Parmeter symbol_id must be an int"
        case 'list_exchange':
            exchange = params.get('exchange')
            if exchange:
                results = handler['install'].list_symbols_exchange(exchange=exchange)
            else:
                results = 'Parameter exchange is missing'
    return results


def exchanges(cmd, params: dict = {}):
    """
    Execute exchanges commands with given parameters.

    Args:
        cmd: The command to execute, currently only 'list' is supported.
        params: The parameters to use for the command execution.

    Returns:
        The result of the command execution or an error message.

    Raises:
        KeyError: An error occurred accessing the command.
    """
    results = f"Error: could not execute {cmd} with params {params}"
    match cmd:
        case 'list':
            results = handler['install'].list_cat_exchanges()
    return results


def users(cmd, params: dict = {}):
    """
    Execute user commands with given parameters.

    Args:
        cmd: The command to execute, can be 'list' or 'exchange'.
        params: The parameters to use for the command execution.

    Returns:
        The result of the command execution or an error message.

    Raises:
        KeyError: An error occurred accessing the command.
    """
    results = f"Error: could not execute {cmd} with params {params}"
    match cmd:
        case 'list':
            page = params.get('page')
            page_size = params.get('page_size')
            if page is None or page_size is None:
                results = "Error: Missing 'page' or 'page_size' parameter for 'list' command."
            else:
                results = handler['user'].list_users(
                    page=page, page_size=page_size)
        case 'exchange':
            results = handler['user'].get_user_exchanges(uid=params.get('uid'))
        case 'account_list':
            pass
    return results


def crawler(cmd, params: dict = {}):
    """
    Execute user commands with given parameters.

    Args:
        cmd: The command to execute, can be 'list' or 'exchange'.
        params: The parameters to use for the command execution.

    Returns:
        The result of the command execution or an error message.

    Raises:
        KeyError: An error occurred accessing the command.
    """
    results = f"Error: could not execute {cmd} with params {params}"
    debug = f"lets execute {cmd} with params {params}"
    logger.info(debug)
    match cmd:
        case 'profiles':
            page = params.get('page')
            page_size = params.get('page_size')
            sieve = params.get('sieve')
            if page is None or page_size is None:
                results = "Error: Missing 'page' or 'page_size' parameter for 'list' command."
            else:
                results = handler['crawler'].get_profiles(site=sieve,
                                                          page=page,
                                                          page_size=page_size)
        case 'list':
            results = handler['crawler'].get_sites()
        case 'add':
            results = handler['crawler'].upsert_profile(profile=params)
        case 'del':
            results = handler['crawler'].del_profile(fid=params.get('fid'))
        case 'edit':
            results = handler['crawler'].upsert_profile(profile=params.get('profile'))
    return results


def bots(cmd, params: dict = {}):
    """
    Executes a command related to bot operations.

    This function is a command dispatcher: it receives a command (cmd) as a string and a set of parameters
    (params) inside a dictionary. The parameters needed depend on the command to be executed.

    Args:
        cmd (str): The command to be executed. Valid commands include 'list', 'live_list', 'edit', 'start',
                   'stop', 'details', and 'test'.
        params (Dict[str, Any]): A dictionary containing the parameters needed for the command. The required
                                 parameters depend on the command:
                                   - 'list': {'page': <int>, 'page_size': <int>}
                                   - 'live_list': No parameters required.
                                   - 'edit': {'bot': <bot instance>}
                                   - 'start' and 'stop': {'bot_id': <int>}
                                   - 'details': {'bot_id': <int>}
                                   - 'test': {'bot_id': <int>}

    Returns:
        str: A string containing the results of the executed command or an error message if the command
             could not be executed.

    Raises:
        ValueError: If the cmd argument is not one of the recognized commands, a ValueError is raised.
    """
    results = f"Error: could not execute {cmd} with params {params}"
    match cmd:
        case 'list':
            page = params.get('page')
            page_size = params.get('page_size')
            if page is None or page_size is None:
                results = "Error: Missing 'page' or 'page_size' parameter for 'list' command."
            else:
                results = handler['bot'].bots_list(page=page, page_size=page_size)
        case 'live_list':
            results = handler['bot'].bots_live_list()
        case 'edit':
            bot = params.get('bot')
            if bot is None:
                results = "Error: Missing 'bot' parameter for 'edit' command."
            else:
                results = handler['bot'].edit(bot=bot)
        case 'start':
            if params.get('bot_id') is None:
                results = f"Error: Missing 'bot_id' parameter for '{cmd}' command."
            else:
                if check_services():
                    handler['bot'].start_bot(bot_id=params['bot_id'])
                    results = f"Bot {params['bot_id']} launched"
                else:
                    results = f"Can't launch bots, services not started"
        case 'stop':
            if params.get('bot_id') is None:
                results = f"Error: Missing 'bot_id' parameter for '{cmd}' command."
            else:
                results = handler['bot'].stop_bot(bot_id=params['bot_id'])
        case 'delete':
            if params.get('bot_id') is None:
                result = f"Error: Missing 'bot_id' parameter for '{cmd}' command."
            else:
                results = handler['bot'].delete(bot_id=params['bot_id'])
        case 'all_feeds':
            results = handler['bot'].get_bot_feeds()
        case 'details':
            if params.get('bot_id') is None:
                results = f"Error: Missing 'bot_id' parameter for '{cmd}' command."
            else:
                results = handler['bot'].bot_details(bot_id=int(params['bot_id']))
        case 'test':
            if params.get('bot_id') is None:
                results = f"Error: Missing 'bot_id' parameter for '{cmd}' command."
            else:
                if component_on('bot'):
                    handler['bot'].start_bot(bot_id=params['bot_id'], test=True)
                    results = f"Bot test {params['bot_id']} launched"
                else:
                    results = f"Error: Can't launch test bot, services not started"
        case 'add':
            if params.get('bot') is None:
                results = "Error: Missing one or more parameters"
            else:
                results = handler['bot'].add(bot=params['bot'])
        case 'add_exchange':
            bot_id = params.get('bot_id', None)
            exchange = params.get('exchange', None)
            if bot_id is None or exchange is None:
                results = f"Error: Missing 'bot_id' or exchange parameter for '{cmd}' command."
            results = handler['bot'].add_exchange(bot_id=bot_id, exchange=exchange)
        case 'add_feeds':
            bot_id = params.get('bot_id', None)
            feeds = params.get('feeds', None)
            if bot_id is None or feeds is None:
                results = f"Error: Missing 'bot_id' or exchange parameter for '{cmd}' command."
            results = handler['bot'].add_feeds(bot_id=bot_id, feeds=feeds)
        case 'dry_reset':
            if params.get('bot_id') is None:
                results = f"Error: Missing 'bot_id' parameter for '{cmd}' command."
            else:
                results = dry_reset(bot_id=params['bot_id'])
    return results


def dry_reset(bot_id):
    """ description """
    handler['bot'].dry_delete(bot_id=bot_id)
    return "Dry reset done"


def bytes_to_gb(bytes: int):
    """
    Convert bytes to gigabytes.

    Args:
    - bytes (int): Bytes to be converted.

    Returns:
    - float: The bytes converted to gigabytes.
    """
    return bytes / (1024 ** 3)


def get_system_status():
    """
    Retrieve system status metrics.

    This function captures several system resource metrics including:
    - CPU usage percentage
    - RAM (Total, Used, Available, Usage percentage)
    - Swap memory (Total, Used, Free, Usage percentage)
    - Disk usage (Total, Used, Free, Usage percentage for the root directory)

    Returns:
    - list: A list of dictionaries. Each dictionary contains a key-value 
            pair representing a system metric and its value.
    """

    resources = {}

    # CPU
    resources["cpu_percent"] = psutil.cpu_percent(interval=1)

    # RAM
    virtual_memory = psutil.virtual_memory()
    resources["total_ram_gb"] = round(bytes_to_gb(virtual_memory.total), 2)
    resources["used_ram_gb"] = round(bytes_to_gb(virtual_memory.used), 2)
    resources["available_ram_gb"] = round(bytes_to_gb(virtual_memory.available), 2)
    resources["ram_percent_used"] = virtual_memory.percent
    resources["ram_percent_free"] = 100 - virtual_memory.percent  # Calculating free RAM as percentage

    # Swap
    swap = psutil.swap_memory()
    resources["total_swap_gb"] = round(bytes_to_gb(swap.total), 2)
    resources["used_swap_gb"] = round(bytes_to_gb(swap.used), 2)
    resources["free_swap_gb"] = round(bytes_to_gb(swap.free), 2)
    resources["swap_percent"] = swap.percent

    # Disk
    disk = psutil.disk_usage('/')
    resources["total_disk_gb"] = round(bytes_to_gb(disk.total), 2)
    resources["used_disk_gb"] = round(bytes_to_gb(disk.used), 2)
    resources["free_disk_gb"] = round(bytes_to_gb(disk.free), 2)
    resources["disk_percent"] = disk.percent

    return resources


def find_another_daemon():
    """ description """
    for proc in psutil.process_iter(['pid', 'name', 'username']):
        if 'Fullon Trading Daemon' in proc.name():
            if os.getuid() == proc.uids().real:
                return True
    return False


def shutdown(message: str = "") -> None:
    """Shut down the daemon and log a message if provided."""
    logger.info("Daemon has been shut down")
    if message:
        logger.info(message)
    sys.exit()


def pre_rpc_server(full, services, stop_event):
    """ description """
    daemon_startup()
    which_startup(full, services)
    rpc_server(logs=False, stop_event=stop_event)
    stop_full()


def which_startup(full, services):
    """ description """
    if full:
        logger.warning("Full components startup initiated")
        start_full()
        logger.warning("Full components startup completed")
        return None
    if services:
        logger.warning("Services component startup initiated")
        start_services()
        logger.warning("Services component startup completed")
        return None
    return None


def rpc_server(stop_event, logs=True):
    """ description """
    with ThreadedXMLRPCServer((settings.XMLRPC_HOST, settings.XMLRPC_PORT),
                              logRequests=logs,
                              requestHandler=RequestHandler,
                              allow_none=True) as server:
        server.register_introspection_functions()
        server.register_function(users)
        server.register_function(strategies)
        server.register_function(symbols)
        server.register_function(exchanges)
        server.register_function(services)
        server.register_function(tickers)
        server.register_function(rpc_test)
        server.register_function(get_system_status)
        server.register_function(get_top)
        server.register_function(bots)
        server.register_function(crawler)
        logger.warning("Fullon Daemon Started")
        server.timeout = 0.5
        while not stop_event.is_set():
            server.handle_request()
