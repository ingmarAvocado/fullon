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
from libs.cache import  Cache
from libs.bot_launcher import start, stop
from libs.database_ohlcv import start as startohlcv, stop as stopohlcv, Database as DatabaseOhlcv
from libs.database import start as startdb, stop as stopdb, Database
from run import rpcdaemon_manager as rpc
from run.user_manager import UserManager
from libs.structs.symbol_struct import SymbolStruct
from libs.structs.exchange_struct import ExchangeStruct
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
    with Database() as dbase:
        yield dbase
    print("Database Queue Stopped")
    stopdb()


@pytest.fixture(scope="session", autouse=True)
def dbase(db_session):
    yield db_session


@pytest.fixture(scope="module")
def store():
    store = Cache()
    yield store
    del store

@pytest.fixture(scope="session", autouse=True)
def test_mail():
    yield "pytest@fullon"


@pytest.fixture(scope="session", autouse=True)
def uid(dbase, test_mail):
    """
    installs users
    """
    user_system = UserManager()
    # now lets add a user
    USER = {
        "mail": test_mail,
        "password": "password",
        "f2a": '---',
        "role": "admin",
        "name": "pytest",
        "lastname": "plant",
        "phone": '54321083',
        "id_num": "231231"}
    user_system.add_user(USER)
    uid = user_system.get_user_id(mail='pytest@fullon')
    yield uid
    assert user_system.remove_user(user_id=uid) is True


@pytest.fixture(scope="session", autouse=True)
def bot_id(uid):
    user = UserManager()
    BOT = {
        'user': uid,
        'name': 'pytest bot',
        'dry_run': 'True',
        'active': 'False'
    }
    bot_id = user.add_bot(bot=BOT)
    yield bot_id
    user.remove_bot(bot_id=bot_id)


@pytest.fixture(scope="session", autouse=True)
def cat_str_name():
    yield 'trading101'


@pytest.fixture(scope="session", autouse=True)
def rsi_upper():
    yield 62

@pytest.fixture(scope="session", autouse=True)
def cat_str_id(dbase, cat_str_name):
    _id = dbase.get_cat_str_id(name=cat_str_name)
    yield _id

@pytest.fixture(scope="session", autouse=True)
def str_id1(bot_id, dbase, cat_str_id):
    STRAT = {
        "cat_str_id": cat_str_id,
        "bot_id": bot_id,
        "size_pct": 10,
        "size_currency": 'USD',
        "leverage": 2}
    str_id1 = dbase.add_bot_strategy(strategy=STRAT)
    yield str_id1

@pytest.fixture(scope="session", autouse=True)
def str_id2(bot_id, dbase, cat_str_id):
    STRAT = {
        "cat_str_id": cat_str_id,
        "bot_id": bot_id,
        "size_pct": 10,
        "size_currency": 'BTC',
        "leverage": 5}
    str_id2 = dbase.add_bot_strategy(strategy=STRAT)
    yield str_id2


@pytest.fixture(scope="session", autouse=True)
def symbol1(dbase):
    # First lets install some symbols
    SYMBOL = {
        "symbol": "ALGD/USD",
        "exchange_name": "kraken",
        "updateframe": "1h",
        "backtest": "2700",
        "decimals": 6,
        "base": "USD",
        "ex_base": "",
        "futures": "t"}
    s_id = dbase.install_symbol(symbol=SymbolStruct.from_dict(SYMBOL))
    symbol = dbase.get_symbol_by_id(symbol_id=s_id)
    dbohlcv = DatabaseOhlcv(exchange=SYMBOL['exchange_name'], symbol=SYMBOL['symbol'])
    dbohlcv.install_schema()
    yield symbol
    dbase.remove_symbol(symbol=symbol)

@pytest.fixture(scope="session", autouse=True)
def symbol2(dbase):
    SYMBOL = {
        "symbol": "ALGD/BTC",
        "exchange_name": "kraken",
        "updateframe": "1h",
        "backtest": "2700",
        "decimals": 6,
        "base": "BTC",
        "ex_base": "",
        "futures": "t"}
    s_id = dbase.install_symbol(symbol=SymbolStruct.from_dict(SYMBOL))
    symbol = dbase.get_symbol_by_id(symbol_id=s_id)
    dbohlcv = DatabaseOhlcv(exchange=SYMBOL['exchange_name'], symbol=SYMBOL['symbol'])
    dbohlcv.install_schema()
    yield symbol
    dbase.remove_symbol(symbol=symbol)


@pytest.fixture(scope="session", autouse=True)
def feed1(str_id1, symbol1, dbase):
    feed = {
        "symbol_id": symbol1.symbol_id,
        "str_id": str_id1,
        "period": 'Ticks',
        "compression": 1,
        "order": 1}
    feed = dbase.add_feed_to_bot(feed=feed)
    yield feed


@pytest.fixture(scope="session", autouse=True)
def feed2(str_id2, symbol2, dbase):
    feed = {
        "symbol_id": symbol2.symbol_id,
        "str_id": str_id2,
        "period": 'Ticks',
        "compression": 1,
        "order": 1}
    feed = dbase.add_feed_to_bot(feed=feed)
    yield feed


@pytest.fixture(scope="session", autouse=True)
def feed3(str_id1, symbol1, dbase):
    feed = {
        "symbol_id": symbol1.symbol_id,
        "str_id": str_id1,
        "period": 'Minutes',
        "compression": 480,
        "order": 2}
    feed = dbase.add_feed_to_bot(feed=feed)
    yield feed


@pytest.fixture(scope="session", autouse=True)
def feed4(str_id2, symbol2, dbase):
    feed = {
        "symbol_id": symbol2.symbol_id,
        "str_id": str_id2,
        "period": 'Minutes',
        "compression": 480,
        "order": 60}
    feed = dbase.add_feed_to_bot(feed=feed)
    yield feed

@pytest.fixture(scope="session", autouse=True)
def exchange1(uid: int):
    """
    """
    with Database() as dbase:
        cat_ex_id = dbase.get_cat_exchanges(exchange='kraken')[0][0]
    exchange = {
        "uid": uid,
        "cat_ex_id": cat_ex_id,
        "name": "kraken1",
        "test": "False",
        "active": "True"}
    ex_id = dbase.add_user_exchange(exchange=ExchangeStruct.from_dict(exchange))
    _exchange = dbase.get_exchange(ex_id=ex_id)
    yield _exchange[0]
    dbase.remove_user_exchange(ex_id=ex_id)
