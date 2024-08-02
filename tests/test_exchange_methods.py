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
import logging


#exchange_list = ['kraken', 'bitmex']
exchange_list = ['kraken']


@pytest.fixture(scope="module")
def exchange_params():
    user = UserManager()
    uid = user.get_user_id(mail='admin@fullon')
    details = user.user_details(uid=uid)
    exchanges: Dict = {}
    for exchange in exchange_list:
        ex = details['exchanges'][exchange]
        exchanges[exchange] = {
            'cat_ex_id': ex['cat_ex_id'],
            'uid': f'{uid}',
            'ex_id': ex['ex_id']
            }
    yield exchanges


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
    con = em.connect_websocket()
    assert isinstance(con, bool)
    yield em
    con = em.stop_websockets()
    assert isinstance(con, bool)
    con = em.stop()
    del em


@pytest.mark.order(1)
@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_get_markets(exchange_instance):
    assert len(exchange_instance.get_markets()) > 0


@pytest.mark.order(2)
@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_no_sleep(exchange_instance):
    no_sleep_list = exchange_instance.no_sleep()
    assert isinstance(no_sleep_list, list)


@pytest.mark.order(3)
@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_has_ticker(exchange_instance):
    has_ticker = exchange_instance.has_ticker()
    assert isinstance(has_ticker, bool)


@pytest.mark.order(4)
@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_socket_connected(exchange_instance):
    con = exchange_instance.socket_connected()
    assert isinstance(con, bool)


@pytest.mark.order(5)
@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_start_ticker_socket(exchange_instance):
    tickers = ['BTC/USD', 'ETH/USD']
    res = exchange_instance.start_ticker_socket(tickers=tickers)
    assert res is True


@pytest.mark.order(6)
@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_start_trade_socket(exchange_instance):
    tickers = ['BTC/USD', 'ETH/USD']
    res = exchange_instance.start_trade_socket(tickers=tickers)
    assert res is True

@pytest.mark.order(7)
@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_start_my_trades_socket(exchange_instance, caplog):
    with caplog.at_level(logging.INFO):
        res = exchange_instance.start_my_trades_socket()
        # Check if the subscription was successful
        assert res is True, "Failed to start my trades socket"
        # Convert all captured logs to lowercase for case-insensitive matching
        logs = caplog.text.lower()
        # Check if the log contains "subscribed" and "trade"
        #assert "subscribed" in logs, "Log does not contain 'subscribed'"
        #assert "trade" in logs, "Log does not contain 'trade'"
    # Optional: Print captured logs for debugging

@pytest.mark.order(8)
@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_fetch_trades(exchange_instance):
    symbol = 'BTC/USD'
    since = int(arrow.utcnow().shift(minutes=-5).timestamp() * 1000)
    trades = exchange_instance.fetch_trades(symbol=symbol, since=since)
    assert isinstance(float(trades[0].price), float) is True
    assert isinstance(float(trades[0].volume), float) is True
    assert isinstance(float(trades[0].timestamp), float) is True
    assert isinstance(trades[0].time, datetime) is True
    assert isinstance(trades[0].side, str) is True
    assert isinstance(trades[0].order_type, str) is True


'''
@pytest.mark.order(9)
@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_get_candles(exchange_instance):
    symbol = 'BTC/USD'
    since = int(arrow.utcnow().shift(days=-3).timestamp() * 1000)
    candles = exchange_instance.get_candles(symbol=symbol,
                                            frame='1d',
                                            since=since)
    assert len(candles) > 0
'''


@pytest.mark.order(10)
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
    assert 'volume' in tick


@pytest.mark.order(11)
@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_get_candles(exchange_instance):
    since = arrow.utcnow().shift(days=-1).timestamp()
    tickers = exchange_instance.get_candles(symbol='BTC/USD', frame='1m', since=since, limit=1000)
    if tickers:
        tick = tickers[0]
        assert tick[0]
        assert tick[1]
        assert tick[2]
        assert tick[3]
        assert tick[4]
        assert tick[5]



@pytest.mark.order(39)
@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_stop_ticker_socket(exchange_instance):
    """Stops the ticker socket.
    Returns:
        Any: The result of starting the ticker socket.
    """
    res = exchange_instance.stop_ticker_socket()
    assert res is True



'''


@pytest.mark.order(3)
@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_connect_test_stop_websocket(exchange_instance):
    assert exchange_instance.connect_websocket() is None
    #assert exchange_instance.start_ticker_socket(tickers=['BTC/USD']) is True
    #assert exchange_instance.socket_connected() is True
    assert exchange_instance.stop_websockets() is None
    #assert exchange_instance.socket_connected() is False
    assert exchange_instance.wbsrv.websocket_connected is False






@pytest.mark.order(6)
@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_fetch_orders(exchange_instance):
    symbol = 'BTC/USD'
    orders = exchange_instance.fetch_orders(symbol=symbol)
    assert isinstance(orders, dict)




@pytest.mark.order(8)
@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_fetch_my_trades(exchange_instance):
    symbol = 'BTC/USD'
    limit = 2
    trades = exchange_instance.fetch_my_trades(symbol=symbol, limit=limit)
    if trades:
        trade = trades[0]
        assert trade.side
        assert trade.ex_trade_id
        assert trade.timestamp
        assert trade.time
        assert trade.volume


@pytest.mark.order(9)
@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_get_balances(exchange_instance):
    symbol = 'BTC/USD'
    limit = 2
    trades = exchange_instance.fetch_my_trades(symbol=symbol, limit=limit)
    if trades:
        trade = trades[0]
        assert trade.side
        assert trade.ex_trade_id
        assert trade.timestamp
        assert trade.time
        assert trade.volume

'''