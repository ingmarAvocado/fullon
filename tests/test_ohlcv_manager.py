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


@pytest.mark.order(1)
def test_run_ohlcv_loop(ohlcv, symbol_test):
    """Test installation of test symbol."""
    result = ohlcv.run_ohlcv_loop(
        symbol=symbol_name, exchange=symbol_test.exchange_name, test=True)
    assert result is None

@pytest.mark.order(2)
def test__get_since(ohlcv, symbol1):
    res = ohlcv._get_since(symbol=symbol1)
    assert isinstance(res, float)
