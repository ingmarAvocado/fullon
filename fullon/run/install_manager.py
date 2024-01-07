import os
from pathlib import Path
import arrow
import sys
from typing import List, Optional
import importlib
from libs.structs.symbol_struct import SymbolStruct
from libs import settings, cache, log
from libs.database import Database
from libs.database_ohlcv import Database as Database_ohlcv
from libs.exchange import Exchange, WorkerError
from run import install_demo

logger = log.fullon_logger(__name__)


class InstallManager:
    """A class that provides methods to install and manage Fullon Trading System"""

    def __init__(self):
        """
        Initializes InstallManager
        """
        pass

    def __enter__(self) -> 'InstallManager':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        return self

    def make_backup(self, name: Optional[str] = None, full: bool = False) -> str:
        """
        Create a backup of the PostgreSQL database using pg_dump and gzip.

        Args:
            name (str, optional): The name of the backup file. If not provided, a default name will be used.
            full (bool, optional): Whether to create a full backup of the database (including all schemas).

        Raises:
            ValueError: If neither full nor mini is True.
        """
        logger.info("Making backup...")
        backup_name = (
            f"{arrow.utcnow().format('YYYY-MM-DD_HH:mm:ss')}.sql.gz"
            if not name
            else f"{name}.sql.gz"
        )
        backup_path = os.path.join(settings.BACKUPS, "fullon_back_" + backup_name)
        schema = ""  # Add a specific schema here if needed

        prefix = (
            f"PGHOST={settings.DBHOST} PGPORT={settings.DBPORT} PGDATABASE={settings.DBNAME} "
            f"PGUSER={settings.DBUSER} PGPASSWORD={settings.DBPASSWD} {settings.PG_DUMP} -w"
        )
        cmd = f"{prefix} {schema}  | {settings.GZIP}  >  {backup_path}"
        logger.info(cmd)
        os.system(cmd)
        logger.info("Backup completed")
        return backup_path

    def recover_backup(self, name: str) -> bool:
        """
        Recovers a backup with the given name.

        Args:
            name (str): The name of the backup to recover.

        Returns:
            bool: True if the backup was recovered successfully, False otherwise.
        """
        dbase = Database()
        msg = f"Recovering backup {name}"
        logger.info(msg)
        name = settings.BACKUPS + name
        cmd = (f"{settings.GUNZIP} -c {name} | "
               f"PGHOST={settings.DBHOST} "
               f"PGPORT={settings.DBPORT} "
               f"PGDATABASE={settings.DBNAME} "
               f"PGUSER={settings.DBUSER} "
               f"PGPASSWORD={settings.DBPASSWD} "
               f"{settings.PSQL} -w")
        logger.info(cmd)
        result = os.system(cmd)
        del dbase
        if result == 0:
            logger.info("Backup recovered")
            return True
        else:
            logger.error("Failed to recover backup")
            return False

    def list_backups(self) -> List[str]:
        """
        Lists all backups.

        Returns:
            List[str]: A list of strings representing the names and sizes of each backup.
        """
        logger.info("Listing backups...")
        flist = []
        count = 1
        try:
            for this_path in Path(settings.BACKUPS).iterdir():
                if this_path.is_file():
                    name = this_path.name
                    if 'sql.gz' in name:
                        filesize = int(os.path.getsize(this_path))
                        size = round(filesize/1024/1024, 2)
                        flist.append({"num": count, "name": name, "size": f"{size}M"})
                        count = count + 1
        except FileNotFoundError as error:
            if "No such file or directory" in str(error):
                os.mkdir(settings.BACKUPS)
        return flist

    def install_strategies(self, prefix='') -> bool:
        """
        Installs all available strategies by scanning the 'strategies/' directory and installing each strategy.
        """
        base_params_list = ['take_profit', 'stop_loss', 'trailing_stop', 'timeout',
                            'size_pct', 'size_currency', 'leverage', 'pre_load_bars', 'feeds']
        pathworks = False
        strats = []
        with Database() as dbase:  # Replace 'Database' with your actual database class
            for (_, dirnames, _) in os.walk(f'{prefix}strategies/'):
                for dirname in dirnames:
                    pathworks = True
                    if dirname != "__pycache__":
                        strats.append(dirname)
                        module_name = f'strategies.{dirname}.strategy'
                        if module_name in sys.modules:
                            # If module is already imported, reload it
                            module = importlib.reload(sys.modules[module_name])
                        else:
                            # Import the module for the first time
                            module = importlib.import_module(module_name, package='Strategy')
                        params = {}
                        base_params = {}
                        for key, value in vars(module.Strategy.params).items():
                            if not key.startswith("_") and key not in base_params_list:
                                params[key] = value
                            elif key in base_params_list:
                                base_params[key] = value
                        dbase.install_strategy(
                            name=dirname, base_params=base_params, params=params)
            _strats = dbase.get_cat_strategies()
        for s in _strats:
            if s.name not in strats:
                return False
        if not pathworks and prefix == '':
            return self.install_strategies(prefix='fullon/')
        return True

    def install_exchanges(self) -> None:
        """
        Installs all available exchanges by scanning the 'exchanges/' directory and installing each exchange.
        """
        with Database() as dbase:
            # Try the first path
            path = 'exchanges/'
            if not os.path.exists(path):
                # If the first path is not found, try the second path
                path = 'fullon/exchanges'
            for (dirpath, dirnames, filenames) in os.walk(path):
                for dirname in dirnames:
                    if dirname not in ["simulator", "ccxt", "__pycache__"]:
                        dbase.install_exchange(name=dirname)

    def install_symbol(self, symbol: SymbolStruct) -> int:
        """
        Installs a specific symbol in the database.

        Args:
            symbol (str): The symbol to be installed in the database.
        """
        res = 0
        with Database() as dbase:
            res = dbase.install_symbol(symbol=symbol)
        return res

    def remove_symbol(self, symbol_id: int) -> bool:
        """
        Removes a specific symbol in the database.

        Args:
            symbol (str): The symbol to be installed in the database.
        """
        symbol = None
        if isinstance(symbol_id, int):
            with Database() as dbase:
                symbol = dbase.get_symbol_by_id(symbol_id=symbol_id)
                if symbol:
                    dbase.remove_symbol(symbol=symbol)
            if symbol:
                with cache.Cache() as store:
                    store.delete_symbol(symbol=symbol.symbol,
                                        exchange_name=symbol.exchange_name)
                with Database_ohlcv(exchange=symbol.exchange_name,
                                    symbol=symbol.symbol) as dbase:
                    dbase.delete_schema()
                    return True
            return False
        else:
            logger.error("Symbol id %s is not an integer", symbol_id)
        return False

    def remove_symbol_by_struct(self, symbol: SymbolStruct) -> bool:
        """
        Removes a specific symbol in the database.

        Args:
            symbol (str): The symbol to be installed in the database.
        """
        with cache.Cache() as store:
            store.delete_symbol(symbol=symbol.symbol,
                                exchange_name=symbol.exchange_name)
        with Database() as dbase:
            if symbol:
                dbase.remove_symbol(symbol=symbol)
        with Database_ohlcv(exchange=symbol.exchange_name,
                            symbol=symbol.symbol) as dbase:
            dbase.delete_schema()
            return True
        return False

    def add_user(self, user: dict) -> None:
        """
        Adds a new user to the database.

        Args:
            user (dict): The user dict
        """
        with Database() as dbase:
            dbase.add_user(user=user)

    def remove_user(self, user_id: Optional[str] = None, email: Optional[str] = None) -> None:
        """
        Adds a new user to the database.

        Args:
            username (str): The username for the new user.
            password (str): The password for the new user.
            email (str): The email address for the new user.
        """
        with Database() as dbase:
            dbase.remove_user(user_id=user_id, email=email)

    def list_symbols(self,
                     page: int = 1,
                     page_size: int = 10,
                     all: bool = False) -> List[SymbolStruct]:
        """
        Lists all available symbols in the database.

        Returns:
            List[Tuple[str, str]]: A list of tuples with the symbol names and exchange names.
        """
        with Database() as dbase:
            symbols = dbase.get_symbols(page=page, page_size=page_size, all=all)
        return symbols

    def list_symbols_exchange(self, exchange) -> List:
        """
        Lists all available symbols from an exchange.

        Returns:
            List[Tuple[str, str]]: A list of tuples with the symbols
        """
        exchange_conn = Exchange(exchange=exchange)
        try:
            markets = exchange_conn.get_markets()
        except WorkerError:
            markets = ['Error: exchange not registered in fullon']
        return markets

    def list_cat_exchanges(self, page=1, page_size=10, all=False) -> List:
        """
        Lists installed exchanges.

        Returns:
            str: A string containing the list of installed exchanges.
        """
        exchanges = []
        with Database() as dbase:
            exchanges = dbase.get_cat_exchanges(page=page, page_size=page_size, all=all)
        return exchanges

    def list_cat_strategies(self, page=1, page_size=10, all=False) -> list:
        """
        Lists installed strategies.

        Returns:
            str: A string containing the list of installed strategies.
        """
        strategies = []
        with Database() as dbase:
            strategies = dbase.get_cat_strategies(page=page, page_size=page_size, all=all)
        return strategies

    def list_user_strategies(self, uid: int) -> Optional[list]:
        """
        Lists user-installed strategies.

        Args:
            uid (int): User ID for which to list installed strategies.

        Returns:
            List: A list of string containing the list of user-installed strategies.
        """
        with Database() as dbase:
            strategies = dbase.get_user_strategies(uid=uid)
        return strategies

    def list_strategy_bots(self, cat_str_name: str) -> Optional[list]:
        """
        Lists bots that use a strategy

        Args:
            cat_str_name (str): the name of the strategy

        Returns:
            List: A  list of dicts containing the bots
        """
        with Database() as dbase:
            bots = dbase.get_strategies_bots(cat_str_name=cat_str_name)
        return bots

    def del_cat_str(self, cat_str_name: str) -> bool:
        """
        Delete cat_strategy

        Args:
            cat_str_name (str): the name of the strategy

        Returns:
            bool: True if success
        """
        with Database() as dbase:
            result = dbase.del_cat_strategy(cat_str_name=cat_str_name)
        return result

    def install_cache(self) -> bool:
        """
        Initializes the cache.

        Returns:
            bool: True if the cache is initialized successfully, False otherwise.
        """
        with cache.Cache() as store:
            store.prepare_cache()
        logger.info("Cache Started...")
        return True

    def clean_top(self, component: Optional[str] = None, pid: Optional[int] = None) -> bool:
        """
        Delete a component or process from the top services list.

        Args:
            component: The component to be deleted, if provided.
            pid: The process ID to be deleted, if provided.

        Returns:
            bool: True if deleted
        """
        store = cache.Cache()
        res = store.delete_from_top(component=component, pid=pid)
        del store
        if res > 0:
            return True
        return False

    def test_pre_install(self) -> bool:
        """
        Test if the pre-installation conditions are met.

        Returns:
            True if the conditions are met, otherwise False.
        """
        ret = True
        with Database() as dbase:
            if 'Error' in dbase.get_user_list():
                ret = False
        return ret

    def install_demo(self) -> None:
        """
        Install the demo data.
        """
        install_demo.install()
