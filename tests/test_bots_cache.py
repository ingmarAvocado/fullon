from __future__ import unicode_literals, print_function
import sys
from requests.cookies import MockRequest
from fullon.libs import log, settings
from fullon.libs.settings_config import fullon_settings_loader
from fullon.libs.structs.exchange_struct import ExchangeStruct
from run import system_manager
from run.user_manager import UserManager
import json
import pytest
import arrow
from libs import cache, database
from unittest.mock import MagicMock


# Test data
tipe_tick = "tick"
tipe_ohlcv = "ohlcv"
key_kraken = "kraken"
pid_1000 = "1000"
pid_1001 = "1001"
params = "test param"
message_new = "new"
message_update = "update"

@pytest.fixture(scope="module")
def store():
    return cache.Cache(reset=True)

@pytest.fixture(scope="module")
def mock_store(store):
    # Make a copy of the original store object
    mock_store = cache.Cache(reset=True)
    # Mock the conn object and its methods
    mock_store.conn = MagicMock()
    mock_store.get_exchange = MagicMock()
    yield mock_store
    del mock_store


def test_update_bot_1(store):
    bot = {"bot_id": '00000-0000-00001',
           "ex_id": '00000-0000-00001',
           "bot_name": "test name",
           "symbol": "BTC/USD",
           "exchange": "kraken",
           "tick": 19200,
           "roi": 200,
           "funds": 10000,
           "totfunds": 8000,
           "pos": 1,
           "pos_price": 100,
           "roi_pct": 2,
           "orders": "",
           "message": "updated",
           "live": "No",
           "strategy": "hot",
           "base": 'BTC',
           "params": {},
           "variables": 'var1, var2'}
    _bot = {}
    _bot[0] = bot
    result = store.del_bot(bot_id=bot['bot_id'])
    assert (result is True) is False
    result = store.update_bot(bot_id=bot['bot_id'], bot=_bot)
    assert (result is True) is True


def test_update_bot_2(store):
    bot = {"bot_id": '00000-0000-00001',
           "ex_id": '00000-0000-00001',
           "bot_name": "test name",
           "symbol": "BTC/USD",
           "exchange": "kraken",
           "tick": 19200,
           "roi": 200,
           "funds": 10000,
           "totfunds": 8000,
           "pos": 1,
           "pos_price": 100,
           "roi_pct": 2,
           "orders": "",
           "message": "updated",
           "live": "No",
           "base": 'BTC',
           "params": {},
           "variables": 'var1, var2'}
    _bot = {}
    _bot[0] = bot
    result = store.update_bot(bot_id=bot['bot_id'], bot=_bot)
    assert (result is False) is True


def test_get_bots(store):
    results = store.get_bots()
    assert isinstance(results, dict) is True
    assert (len(results) > 0) is True
    result = store.del_bot(bot_id='00000-0000-00001')
    assert (result is True) is True


def test_block_exchange(store):
    ex_id = 1
    symbol = 'BTC/USD'
    bot_id = '1.1'
    res = store.block_exchange(ex_id=ex_id, symbol=symbol, bot_id=bot_id)
    assert res is True


def test_is_blocked_1(store):
    ex_id = 1
    symbol = 'BTC/USD'
    bot_id = '1.2'
    bot = store.is_blocked(ex_id=ex_id, symbol=symbol)
    assert bot != bot_id


def test_is_blocked_2(store):
    ex_id = 1
    symbol = 'BTC/USD'
    bot_id = '1.1'
    bot = store.is_blocked(ex_id=ex_id, symbol=symbol)
    assert bot == bot_id


def test_get_blocks(store):
    blocked = store.get_blocks()
    ex_id = '1'
    symbol = 'BTC/USD'
    bot_id = '1.1'
    found = False
    for block in blocked:
        if block['ex_id'] == ex_id and block['symbol'] == symbol and block['bot'] == bot_id:
            found = True
    assert found is True


def test_unblock_exchange(store):
    ex_id = 1
    symbol = 'BTC/USD'
    res = store.unblock_exchange(ex_id=ex_id, symbol=symbol)
    assert res is True
