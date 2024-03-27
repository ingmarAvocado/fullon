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
settings.LOG_LEVEL = "logging.INFO"
from libs import exchange, log
from libs.bot_launcher import start, stop
from libs.database_ohlcv import start as startohlcv, stop as stopohlcv, Database as DatabaseOhlcv
from libs.database import start as startdb, stop as stopdb, Database
from run import rpcdaemon_manager as rpc
import pytest

logger = log.fullon_logger(__name__)


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
    yield dbase
    print("Ohlcv Database Queue Stopped")
    stopohlcv()


@pytest.fixture(scope="session", autouse=True)
def db_session():
    startdb()
    print("\nDatabase Queue Started")
    dbase = Database()
    yield dbase
    print("Database Queue Stopped")
    del dbase
    stopdb()
