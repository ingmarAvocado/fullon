import sys
from pathlib import Path
from time import sleep
from threading import Thread, Event


project_dir = Path(__file__).resolve().parents[1]
libs_dir = project_dir / "fullon"
sys.path.append(str(project_dir))
sys.path.append(str(libs_dir))

from libs import settings
from libs.settings_config import fullon_settings_loader
from libs import exchange, log
from libs.cache import  Cache
from libs.bot_launcher import start, stop
from libs.database_ohlcv import start as startohlcv, stop as stopohlcv, Database as DatabaseOhlcv
from libs.database import start as startdb, stop as stopdb, Database
from run import rpcdaemon_manager as rpc
from run.user_manager import UserManager
from libs.structs.symbol_struct import SymbolStruct
from libs.structs.exchange_struct import ExchangeStruct
from fullon.run.install_manager import InstallManager
import pytest
import xmlrpc.client

logger = log.fullon_logger(__name__)

settings.LOG_LEVEL = "logging.INFO"

@pytest.fixture(scope="session", autouse=True)
def exchange_session():
    exchange.start_all()
    print("Exchange queue started")
    yield
    print("Exchange queue stopped")
    exchange.stop_all()

@pytest.fixture(scope="session")
def server():
    stop_event = Event()
    server_thread = Thread(target=rpc.rpc_server, args=[stop_event,], daemon=True)
    server_thread.start()
    sleep(1)
    print("RPC Server Started")
    yield True
    stop_event.set()


@pytest.fixture(scope="session", autouse=True)
def launcher_session():
    start()
    print("Bot Launcher Started")
    yield
    stop()


@pytest.fixture(scope="session", autouse=True)
def dbohlcv_session():
    startohlcv()
    print("Ohlcv Database Queue Started")
    dbase = DatabaseOhlcv(exchange='kraken', symbol='BTC/USD')
    yield
    print("Ohlcv Database Queue Stopped")
    stopohlcv()


@pytest.fixture(scope="session", autouse=True)
def db_session():
    startdb()
    print("\nDatabase Queue Started")
    yield
    print("Database Queue Stopped")
    stopdb()


@pytest.fixture(scope="module")
def dbase():
    with Database() as dbase:
        yield dbase


@pytest.fixture(scope="module")
def store():
    store = Cache()
    yield store
    del store

@pytest.fixture(scope="module")
def test_mail():
    yield "admin@fullon"


@pytest.fixture(scope="module")
def uid():
    """
    installs users
    """
    user_system = UserManager()
    uid = user_system.get_user_id(mail='admin@fullon')
    yield uid


@pytest.fixture(scope="module")
def bot_id():
    yield 2


@pytest.fixture(scope="module")
def cat_str_name():
    yield 'trading101'


@pytest.fixture(scope="module")
def rsi_upper():
    yield 62


@pytest.fixture(scope="module")
def cat_str_id(dbase, cat_str_name):
    _id = dbase.get_cat_str_id(name=cat_str_name)
    yield _id


@pytest.fixture(scope="module")
def str_id1(bot_id, dbase):
    str_id1 = dbase.get_base_str_params(bot_id=bot_id)
    yield str_id1[0].str_id


@pytest.fixture(scope="module")
def symbol1(dbase):
    symbol1 = dbase.get_symbol(symbol='BTC/USD', exchange_name='kraken')
    yield symbol1


@pytest.fixture(scope="module")
def symbol2(dbase):
    symbol = dbase.get_symbol(symbol='ETH/USD', exchange_name='kraken')
    yield symbol


@pytest.fixture(scope="module")
def exchange1(dbase):
    """
    """
    _exchange = dbase.get_exchange(ex_id=1)
    yield _exchange[0]


@pytest.fixture(scope="module")
def rpc_client(server):
    if server:
        yield xmlrpc.client.ServerProxy(f"http://{settings.XMLRPC_HOST}:{settings.XMLRPC_PORT}", allow_none=True)

def get_symbol_struct():
    VIEW_NAME = "kraken_agld_usd.candles1m"
    OHLCV = f"""
    CREATE MATERIALIZED VIEW kraken_agld_usd.candles1m
    WITH (timescaledb.continuous) AS
    SELECT time_bucket('1 minutes', timestamp) AS ts,
            FIRST(price, timestamp) as open,
            MAX(price) as high,
            MIN(price) as low,
            LAST(price, timestamp) as close,
            SUM(volume) as vol
    FROM kraken_agld_usd.trades
    WHERE kraken_agld_usd.trades.timestamp > '2017-01-01'
    GROUP BY ts WITH NO DATA;
    commit;
    SELECT add_continuous_aggregate_policy('kraken_agld_usd.candles1m',
        start_offset => INTERVAL '2 h',
        end_offset => INTERVAL '1 h',
        schedule_interval => INTERVAL '1 h');
    commit;
    ALTER TABLE agld_usd_USD.candles1m  RENAME COLUMN ts to timestamp;
    """

    SYMBOL = {"symbol": 'AGLD/USD',
              "exchange_name": "kraken",
              "updateframe": "1h",
              "backtest": 2,
              "decimals": 6,
              "base": "USD",
              "futures": False,
              "only_ticker": True,
              "cat_ex_id": 1,
              "ohlcv_view": OHLCV}
    symbol = SymbolStruct.from_dict(SYMBOL)
    return symbol


@pytest.fixture(scope="module")
def symbol_test():    
    symbol_struct = get_symbol_struct()
    install = InstallManager()
    install.remove_symbol_by_struct(symbol=symbol_struct)
    s_id = install.install_symbol(symbol=symbol_struct)
    symbol_struct.symbol_id = s_id
    yield symbol_struct


def pytest_sessionfinish(session, exitstatus):
    """
    This hook is called after all tests have been executed and just before
    finishing the session, making it a good place to perform cleanup activities,
    or logging the overall results of the tests.
    
    Args:
        session: The pytest session object.
        exitstatus: The exit status of the testing process.
    """
    print("All tests are done. Perform any cleanup or final logging here.")
    # For example, you can log the exit status or perform some final cleanup.
    startohlcv()
    startdb()
    symbol_struct = get_symbol_struct()
    install = InstallManager()
    install.remove_symbol_by_struct(symbol=symbol_struct)
    stopdb()
    stopohlcv()
    print(f"Test session finished. Exit status: {exitstatus}")


