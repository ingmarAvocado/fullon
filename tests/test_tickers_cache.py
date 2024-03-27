from __future__ import unicode_literals, print_function
import pytest
import arrow
from libs import cache

exchange_list = ['kraken']


@pytest.fixture(scope="module")
def store():
    return cache.Cache(reset=True)


@pytest.mark.order(1)
@pytest.mark.parametrize("exchange_name", exchange_list)
def test_update_tickers(store, exchange_name):
    tick1 = {
        "price": "28500.00000",
        "volume": "1.00000000",
        "time": arrow.utcnow().format('YYYY-MM-DD HH:mm:ss.SSS')
    }
    result = store.update_ticker(symbol='BTC/USD', exchange=exchange_name, data=tick1)
    assert result != 0
    tick2 = {
        "price": "3000.00000",
        "volume": "1.00000000",
        "time": arrow.utcnow().format('YYYY-MM-DD HH:mm:ss.SSS')
    }
    result = store.update_ticker(symbol='ETH/USD', exchange=exchange_name, data=tick2)
    assert result != 0
    tick3 = {
        "price": "0.07000000",
        "volume": "1000.00000000",
        "time": arrow.utcnow().format('YYYY-MM-DD HH:mm:ss.SSS')
    }
    result = store.update_ticker(symbol='XRP/USD', exchange=exchange_name, data=tick3)
    assert result != 0
    tick4 = {
        "price": "0.03000000",
        "volume": "2000.00000000",
        "time": arrow.utcnow().format('YYYY-MM-DD HH:mm:ss.SSS')
    }
    result = store.update_ticker(symbol='BTC/USD', exchange=exchange_name, data=tick4)
    assert result != 0
    tick5 = {
        "price": "0.00050000",
        "volume": "3000.00000000",
        "time": arrow.utcnow().format('YYYY-MM-DD HH:mm:ss.SSS')
    }
    result = store.update_ticker(symbol='XRP/USD', exchange=exchange_name, data=tick5)
    assert result != 0
    tick6 = {
        "price": "50000.00000",
        "volume": "0.10000000",
        "time": arrow.utcnow().format('YYYY-MM-DD HH:mm:ss.SSS')
    }
    result = store.update_ticker(symbol='XMR/USD', exchange=exchange_name, data=tick6)
    assert result != 0


@pytest.mark.order(2)
@pytest.mark.parametrize("exchange_name", exchange_list)
def test_get_price_1(store, exchange_name):
    ticker = store.get_price(exchange=exchange_name, symbol="BTC/USD")
    assert (isinstance(ticker, float) is True) is True


@pytest.mark.order(3)
def test_get_price_2(store):
    ticker = store.get_price(exchange='blah blah', symbol="BTC/USD")
    assert ticker is 0


@pytest.mark.order(4)
def test_get_price_3(store):
    ticker = store.get_price(symbol="BTC/USD")
    assert (isinstance(ticker, float) is True) is True


@pytest.mark.order(5)
@pytest.mark.parametrize("exchange_name", exchange_list)
def test_get_tickers(store, exchange_name):
    rows = store.get_tickers()
    assert (len(rows) > 0) is True
    rows = store.get_tickers(exchange=exchange_name)
    assert (len(rows) > 0) is True


@pytest.mark.order(6)
def test_get_ticker_1(store):
    ticker, stamp = store.get_ticker(exchange='blah', symbol="BTC/USD")
    assert stamp is None and ticker is 0


@pytest.mark.order(7)
@pytest.mark.parametrize("exchange_name", exchange_list)
def test_get_ticker_2(store, exchange_name):
    ticker, stamp = store.get_ticker(exchange=exchange_name, symbol="BTC/USD")
    stamp = arrow.get(stamp)
    assert isinstance(ticker, float) is True
    assert isinstance(stamp, arrow.Arrow) is True
