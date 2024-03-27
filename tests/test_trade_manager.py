from __future__ import unicode_literals, print_function
import sys

from requests.cookies import MockRequest
from libs import log, settings, exchange
from libs.settings_config import fullon_settings_loader
from libs.models.ohlcv_model import Database
import threading
from run import system_manager
import arrow
import pytest

SYMBOL = 'BTC/USD'


@pytest.fixture
def trade_manager():
    tm = system_manager.TradeManager()
    yield tm
    del tm

@pytest.fixture
def exchange_instance():
    exch = exchange.Exchange("kraken")
    yield exch
    del exch


@pytest.fixture
def db_ohlcv_instance(exchange_instance):
    dbase = Database(exchange='kraken', symbol=SYMBOL)
    yield dbase
    del dbase


@pytest.mark.order(1)
def test_order_startup(trade_manager):
    assert trade_manager.started is True, "Trade manager didn't properly start"


@pytest.mark.order(2)
def test_update_trades_since_1(trade_manager,
                               exchange_instance,
                               db_ohlcv_instance,
                               caplog):
    since = db_ohlcv_instance.get_latest_timestamp(table2="kraken_BTC_USD.trades")
    symbol = SYMBOL  # Replace with the symbol you want to test
    exchange = 'kraken'
    # Define a wrapper function to call `update_trades_since` with the necessary arguments
    trade_manager.update_trades_since(exchange=exchange,
                                      symbol=symbol,
                                      since=since,
                                      test=True)
    assert len(caplog.records) > 0

