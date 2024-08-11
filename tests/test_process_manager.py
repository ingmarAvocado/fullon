from __future__ import unicode_literals, print_function
from run.tick_manager import TickManager
from run import system_manager
import pytest
import time


@pytest.fixture
def process_manager():
    pmanager = system_manager.ProcessManager()
    yield pmanager
    del pmanager


@pytest.fixture
def tick_manager():
    tick_manager = TickManager()
    yield tick_manager
    tick_manager.stop_all()


@pytest.mark.order(1)
def test_get_top(process_manager):
    res = process_manager.get_top()
    #print(res)


@pytest.mark.order(2)
def test_check_tickers(process_manager, tick_manager):
    error = process_manager.check_tickers()
    assert isinstance(error, dict)

@pytest.mark.order(3)
def test_ohlcv_tickers(process_manager, store):
    #store.update_trade_status(key="test1")
    #store.update_trade_status(key="test2")
    error = process_manager.check_ohlcv()
    assert isinstance(error, dict)
