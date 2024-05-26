from fullon.exchanges.kraken.interface import Interface
from fullon.libs.database import Database
from fullon.run.user_manager import UserManager
from fullon.libs import settings
import arrow
import pytest
import time


exchange_list = ['kraken']


@pytest.fixture(scope="module", params=exchange_list)
def exchange_struct(request, dbase):
    exchange_name = request.param
    user = UserManager()
    uid = user.get_user_id(mail='admin@fullon')
    exch = dbase.get_exchange(user_id=uid)[0]
    iface = Interface(exchange_name, params=exch)
    yield iface
    iface.stop()
    del iface


@pytest.mark.order(1)
def test_stop(exchange_struct):
    return


@pytest.mark.order(2)
def test_get_user_key(exchange_struct):
    return


@pytest.mark.order(3)
def test_set_leverage(exchange_struct):
    return


@pytest.mark.order(4)
def test_get_market(exchange_struct):
    return


@pytest.mark.order(5)
def test_get_markets(exchange_struct):
    markets = exchange_struct.get_markets()
    assert isinstance(markets, dict)
    assert len(markets) > 0
    for symbol, market in markets.items():
        assert isinstance(market, dict)
        assert set(market.keys()) == {'symbol', 'wsname', 'base', 'cost_decimals', 'pair_decimals'}
        assert isinstance(symbol, str)
        assert isinstance(market['symbol'], str)
        assert isinstance(market['wsname'], str)
        assert isinstance(market['base'], str)
        assert isinstance(market['cost_decimals'], str)
        assert isinstance(market['pair_decimals'], str)


@pytest.mark.order(6)
def test_execute_ws(exchange_struct):
    return


@pytest.mark.order(7)
def test_get_cash(exchange_struct):
    return


@pytest.mark.order(8)
def test_fetch_orders(exchange_struct):
    return


@pytest.mark.order(9)
def test_cancel_all_orders(exchange_struct):
    return


@pytest.mark.order(10)
def test_create_order(exchange_struct):
    return

@pytest.mark.order(11)
def test_cancel_order(exchange_struct):
    return

@pytest.mark.order(12)
def test_get_candles(exchange_struct):
    return

@pytest.mark.order(13)
def test_get_tickers(exchange_struct):
    settings.LOG_LEVEL = "logging.INFO"
    tickers = exchange_struct.get_tickers()
    assert isinstance(tickers, dict)
    assert len(tickers) > 0
    for symbol, ticker in tickers.items():
        assert isinstance(ticker, dict)
        assert set(ticker.keys()) == {'symbol', 'datetime', 'openPrice', 'highPrice', 'lowPrice', 'close', 'volume'}
        assert isinstance(symbol, str)
        assert isinstance(ticker['symbol'], str)
        assert isinstance(ticker['datetime'], str)
        assert isinstance(ticker['openPrice'], float)
        assert isinstance(ticker['highPrice'], float)
        assert isinstance(ticker['lowPrice'], float)
        assert isinstance(ticker['close'], float)
        assert isinstance(ticker['volume'], float)


@pytest.mark.order(14)
def test_get_balances(exchange_struct):
    balances = exchange_struct.get_balances()

    # There must be at least one balance returned
    assert len(balances) > 0

    # For each currency, verify 'free', 'used', 'total' exist and are float
    for currency, balance_info in balances.items():
        assert isinstance(currency, str), f'Currency {currency} is not a string'
        assert all(key in balance_info for key in ('free', 'used', 'total')), f'Missing key in balance for {currency}'

        # Check that 'free', 'used' and 'total' are float
        for key in ('free', 'used', 'total'):
            assert isinstance(balance_info[key], float), f'{key} for {currency} is not a float'


@pytest.mark.order(15)
def test_get_positions(exchange_struct):
    pos = exchange_struct.get_positions()
    assert isinstance(pos, dict)


@pytest.mark.order(16)
def test_connect_websocket(exchange_struct):
    return


@pytest.mark.order(17)
def test_fetch_trades(exchange_struct):
    since = arrow.utcnow().shift(minutes=-5).format()
    trades = exchange_struct.fetch_trades(symbol='BTC/USD', since=since)
    assert len(trades) > 0
    for trade in trades:
        assert trade.price
        assert trade.volume
        assert trade.time
        assert trade.side
        assert trade.order_type


@pytest.mark.order(18)
def test_fetch_my_trades(exchange_struct):
    return


@pytest.mark.order(19)
def test_rearrange_tickers(exchange_struct):
    return


@pytest.mark.order(20)
def test_decimal_rules(exchange_struct):
    return


@pytest.mark.order(21)
def test_minimum_order_cost(exchange_struct):
    minord = exchange_struct.minimum_order_cost(symbol='BTC/USD')
    assert minord == 0.0001
    minord = exchange_struct.minimum_order_cost(symbol='XMR/BTC')
    assert minord == 0.035


@pytest.mark.order(22)
def test_quote_symbol(exchange_struct):
    pass


@pytest.mark.order(23)
def test_get_decimals(exchange_struct):
    return


@pytest.mark.order(24)
def test_stop_websockets(exchange_struct):
    return


@pytest.mark.order(25)
def test_start_ticker_socket(exchange_struct, caplog):
    exchange_struct.start_ticker_socket(tickers=['BTC/USD', 'ETH/USD'])
    time.sleep(3)
    assert "Subscribe" in caplog.text
    exchange_struct.stop_ticker_socket()
    time.sleep(3)
    assert "Unsubscribed" in caplog.text
    exchange_struct.start_ticker_socket(tickers=['BTC/USD', 'ETH/USD', 'MATIC/USD'])
    time.sleep(3)
    assert "Subscribe" in caplog.text
    exchange_struct.stop_ticker_socket()
    time.sleep(3)
    assert "Unsubscribed" in caplog.text


@pytest.mark.order(26)
def test_socket_connected(exchange_struct):
    return


@pytest.mark.order(27)
def test_get_asset_pairs(exchange_struct):
    return


@pytest.mark.order(28)
def test_start_my_trades_socket(exchange_struct):
    return


@pytest.mark.order(29)
def test_start_trade_socket(exchange_struct):
    return


@pytest.mark.order(30)
def test_my_open_orders_socket(exchange_struct):
    return
