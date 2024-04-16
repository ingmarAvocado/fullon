"""
comment
"""
from __future__ import unicode_literals, print_function
from numpy import right_shift
import pytest
from fullon.libs import log
from fullon.libs import cache
from fullon.libs.structs.symbol_struct import SymbolStruct
from fullon.run.ohlcv_manager import OhlcvManager

import threading
from time import sleep


logger = log.fullon_logger(__name__)
symbol_name = "AGLD/USD"


@pytest.fixture(scope="module")
def ohlcv():
    manager = OhlcvManager()
    yield manager
    manager.stop_all()
    del manager


@pytest.mark.order(2)
def test_run_ohlcv_loop(ohlcv, symbol_test):
    """Test installation of test symbol."""
    result = ohlcv.run_ohlcv_loop(
        symbol=symbol_name, exchange=symbol_test.exchange_name, test=True)
    assert result is None


@pytest.mark.order(3)
def test_relaunch_dead_threads(ohlcv, symbol_test):
    ohlcv.threads[f'{symbol_test.exchange_name}:{symbol_test.symbol}'] = threading.Thread()
    ohlcv.threads[f'{symbol_test.exchange_name}:{symbol_test.symbol}'].is_alive = lambda: False
    ohlcv.relaunch_dead_threads(test=True)
    sleep(4)
