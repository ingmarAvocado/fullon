import pytest
from typing import Dict, List
import time
import arrow
from datetime import datetime
from run.tick_manager import TickManager
from libs.exchange_methods import ExchangeMethods
from libs.structs.exchange_struct import ExchangeStruct
from run.user_manager import UserManager
from run.tick_manager import TickManager


exchange_list = ['kraken']

@pytest.fixture(scope="module")
def exchange_params() -> Dict:
    user = UserManager()
    uid = user.get_user_id(mail='admin@fullon')
    details = user.user_details(uid=uid)
    ex1 = details['exchanges']['kraken']
    return {
        'kraken': {
            'cat_ex_id': ex1['cat_ex_id'],
            'uid': f'{uid}',
            'ex_id': ex1['ex_id']
        },
        'kucoin': {
            'cat_ex_id': 'different_cat_ex_id',
            'uid': f'{uid}',
            'ex_id': 'different_ex_id'
        }
        # Add more exchanges here
    }

@pytest.fixture(scope="module")
def tick_manager():
    tick = TickManager()
    yield tick
    del tick

@pytest.fixture(scope="module")
def exchange_instance(request, exchange_params):
    exchange_name = request.param
    params = ExchangeStruct.from_dict(exchange_params[exchange_name])
    em = ExchangeMethods(
           exchange=exchange_name,
           params=params)
    yield em
    del em

@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_get_markets(exchange_instance):
    assert len(exchange_instance.get_markets()) > 0


@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_has_ticker(exchange_instance):
    assert exchange_instance.has_ticker() is True

@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_connect_test_stop_websocket(exchange_instance):
    assert exchange_instance.connect_websocket() is None
    #assert exchange_instance.start_ticker_socket(tickers=['BTC/USD']) is True
    #assert exchange_instance.socket_connected() is True
    assert exchange_instance.stop_websockets() is None
    #assert exchange_instance.socket_connected() is False
    assert exchange_instance.wbsrv.websocket_connected is False


@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_fetch_trades(exchange_instance):
    symbol = 'BTC/USD'
    since = arrow.utcnow().shift(minutes=-3).timestamp()
    trades = exchange_instance.fetch_trades(symbol=symbol, since=since)
    assert isinstance(float(trades[0].price), float) is True
    assert isinstance(float(trades[0].volume), float) is True
    assert isinstance(float(trades[0].timestamp), float) is True
    assert isinstance(trades[0].time, datetime) is True
    assert isinstance(trades[0].side, str) is True
    assert isinstance(trades[0].order_type, str) is True


@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_get_candles(exchange_instance):
    symbol = 'BTC/USD'
    since = arrow.utcnow().shift(days=-1).timestamp()
    candles = exchange_instance.get_candles(symbol=symbol,
                                            frame='1h',
                                            since=since)
    assert len(candles) > 0


@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_fetch_orders(exchange_instance):
    symbol = 'BTC/USD'
    orders = exchange_instance.fetch_orders(symbol=symbol)
    assert isinstance(orders, dict)

@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_get_tickers(exchange_instance):
    tickers = exchange_instance.get_tickers()
    tick = tickers[next(iter(tickers))]
    assert tick['symbol']
    assert tick['datetime']
    assert tick['openPrice']
    assert tick['highPrice']
    assert tick['lowPrice']
    assert tick['close']
    assert tick['volume']

@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_fetch_my_trades(exchange_instance):
    symbol = 'BTC/USD'
    limit = 2
    trades = exchange_instance.fetch_my_trades(symbol=symbol, limit=limit)
    trade = trades[0]
    assert trade.side
    assert trade.ex_trade_id
    assert trade.timestamp
    assert trade.time
    assert trade.volume
