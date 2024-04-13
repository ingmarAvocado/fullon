from __future__ import unicode_literals, print_function
import sys
from requests.cookies import MockRequest
from libs import log, settings, database, cache
from libs.structs.trade_struct import TradeStruct
from libs.structs.symbol_struct import SymbolStruct
from run.user_manager import UserManager
import datetime
import pytest


@pytest.mark.order(1)
def test_get_symbols(dbase):
    symbols = dbase.get_symbols()
    assert len(symbols) > 0
    assert isinstance(symbols[0].symbol, str)
    assert isinstance(symbols[0].exchange_name, str)
    assert isinstance(symbols[0].backtest, int)
    assert isinstance(symbols[0].updateframe, str)
    assert isinstance(symbols[0].decimals, int)
    assert isinstance(symbols[0].base, str)
    assert isinstance(symbols[0].ex_base, str)
    assert isinstance(symbols[0].ohlcv_view, str)


@pytest.mark.order(2)
def test_get_symbols2(dbase):
    symbols = dbase.get_symbols(exchange='kraken')
    assert len(symbols) > 0
    assert isinstance(symbols[0].symbol, str)
    assert isinstance(symbols[0].exchange_name, str)
    assert isinstance(symbols[0].backtest, int)
    assert isinstance(symbols[0].updateframe, str)
    assert isinstance(symbols[0].decimals, int)
    assert isinstance(symbols[0].base, str)
    assert isinstance(symbols[0].ex_base, str)
    assert isinstance(symbols[0].ohlcv_view, str)


@pytest.mark.order(3)
def test_get_symbol(dbase, symbol1):
    symbol = symbol1.symbol
    cat_ex_id = symbol1.cat_ex_id
    exchange = symbol1.exchange_name
    symbol_data = dbase.get_symbol(symbol=symbol,
                                   cat_ex_id=cat_ex_id)
    assert symbol_data is not None
    assert symbol_data.symbol == symbol
    assert symbol_data.cat_ex_id == cat_ex_id
    assert symbol_data.exchange_name == exchange
    assert isinstance(symbol_data.updateframe, str)
    assert isinstance(symbol_data.backtest, int)
    assert isinstance(symbol_data.decimals, int)
    assert isinstance(symbol_data.base, str)


@pytest.mark.order(4)
def test_get_symbol2(dbase, symbol2):
    symbol = symbol2.symbol
    cat_ex_id = symbol2.cat_ex_id
    exchange = symbol2.exchange_name
    symbol_data = dbase.get_symbol(symbol=symbol,
                                   cat_ex_id=cat_ex_id)
    assert symbol_data is not None
    assert symbol_data.symbol == symbol
    assert symbol_data.cat_ex_id == cat_ex_id
    assert symbol_data.exchange_name == exchange
    assert isinstance(symbol_data.updateframe, str)
    assert isinstance(symbol_data.backtest, int)
    assert isinstance(symbol_data.decimals, int)
    assert isinstance(symbol_data.base, str)


@pytest.mark.order(5)
def test_get_symbol_by_id(dbase, symbol1):
    symbol_id = symbol1.symbol_id
    symbol_data = dbase.get_symbol_by_id(symbol_id=symbol_id)
    assert symbol_data is not None
    assert isinstance(symbol_data.symbol, str)
    assert isinstance(symbol_data.updateframe, str)
    assert isinstance(symbol_data.backtest, int)
    assert isinstance(symbol_data.decimals, int)
    assert isinstance(symbol_data.base, str)
