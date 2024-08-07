from __future__ import unicode_literals, print_function
import sys
from libs import log, settings, exchange, database_helpers
from libs.models import ohlcv_model as database_ohlcv
from fullon.libs.settings_config import fullon_settings_loader
from run.system_manager import TickManager
from libs.cache import Cache
from libs.structs.tick_struct import TickStruct
import pytest
import time
import json


exchange_list = ['kraken']

@pytest.fixture(scope="module")
def tick_manager():
    t = TickManager()
    yield t
    t.stop_all()


@pytest.mark.order(1)
@pytest.mark.parametrize("exchange_name", exchange_list)
def test_run_loop_test(tick_manager, exchange_name, caplog):
    cat_exchanges = tick_manager.get_cat_exchanges()
    for exch in cat_exchanges:
        if exch['name'] == exchange_name:
            result = tick_manager.run_loop_one_exchange(
                exchange_name=exchange_name)
    while True:
        with Cache() as store:
            ticker = store.get_ticker_any('BTC/USD')
            if ticker > 0:
                aticker = store.get_ticker(exchange=exchange_name,
                                           symbol='BTC/USD')
                if aticker[0] > 0:
                    break
            time.sleep(2)
    with Cache() as store:
        tickers = store.get_tickers()
    assert len(tickers) > 0
    time.sleep(20)
    tick_exchange = exchange.Exchange(exchange_name)
    tick_exchange.stop_ticker_socket()
    #lets delete all the records and leave one with an other date
    for tick in tickers:
        assert isinstance(tick, TickStruct)



@pytest.mark.order(2)
def test_run_btc_ticker(tick_manager):
    store = Cache()
    ticker_data = {
                    "price": "27577.20000",
                    "volume": "0.04966290",
                    "time": "2023-04-23 01:10:43.023",
                    "side": "b",
                    "order_type": "l",
                    "misc": ""
                }
    store.conn.hset(f"tickers:kraken", 'BTC/USD', json.dumps(ticker_data))
    btc_price = tick_manager.btc_ticker()
    store.conn.delete("tickers:kraken")
    assert btc_price is not None
    assert isinstance(btc_price, float)
    assert btc_price > 0


@pytest.mark.order(3)
def test_get_cat_exchanges(tick_manager):
    cat_exchanges = tick_manager.get_cat_exchanges()
    assert isinstance(cat_exchanges, list)
    assert len(cat_exchanges) > 0
    for exch in cat_exchanges:
        assert isinstance(exch, dict)
        assert 'name' in exch and isinstance(exch['name'], str)
        assert 'id' in exch and isinstance(exch['id'], str)


@pytest.mark.order(4)
def test_get_exchange_pairs(tick_manager):
    pairs = tick_manager.get_exchange_pairs(exchange_name="kraken")
    assert isinstance(pairs, list)
    assert len(pairs) > 0
    for pair in pairs:
        assert isinstance(pair, str)


@pytest.mark.order(5)
def test_init_install_ticker(tick_manager):
    assert tick_manager.started is False


@pytest.mark.order(6)
def test_get_ticker_list(tick_manager):
    res = tick_manager.get_tickers()
    assert isinstance(res, list)
