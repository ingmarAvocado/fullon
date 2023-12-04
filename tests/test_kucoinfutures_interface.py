from fullon.libs import log, settings
from libs.settings_config import fullon_settings_loader
#from fullon.exchanges.kucoinfutures.interface import Interface
import pytest
import time

'''

@pytest.fixture(scope="module")
def kucoinfutures():
    params = {'KEY': '64210332ecb900000172f782', 'SECRET': 'cffddbc9-cbe7-4d31-b430-fb81726a1139', 'FUTURES': "1"}
    return Interface('kucoinfutures', params)


def test_fetch_trades(kucoinfutures):
    trades = kucoinfutures.fetch_trades(symbol='XBTUSDTM')
    assert len(trades) > 0
    for trade in trades:
        assert 'takerOrMaker' in trade


def test_get_tickers(kucoinfutures):
    tickers = kucoinfutures.get_tickers()
    assert isinstance(tickers, dict)
    assert len(tickers) > 0
    for ticker in tickers.values():
        assert isinstance(ticker, dict)
        assert set(ticker.keys()) == {'symbol', 'datetime', 'openPrice', 'highPrice', 'lowPrice', 'closePrice', 'volume'}
        assert isinstance(ticker['symbol'], str)
        assert isinstance(ticker['datetime'], str)
        assert isinstance(ticker['openPrice'], float)
        assert isinstance(ticker['highPrice'], float)
        assert isinstance(ticker['lowPrice'], float)
        assert isinstance(ticker['closePrice'], float)
        assert isinstance(ticker['volume'], float)
"""
def test_fetch_my_trades(kucoinfutures):
    symbol = "XBTUSDTM"
    time.sleep(3)
    trades = kucoinfutures.fetch_my_trades(symbol=symbol)
    assert isinstance(trades, list)
    for trade in trades:
        assert isinstance(trade, dict)
        assert set(trade.keys()) == {'id', 'info', 'symbol', 'timestamp', 'datetime', 'order', 'type', 'side', 'takerOrMaker', 'price', 'amount', 'cost', 'fee'}
        assert isinstance(trade['id'], str)
        assert isinstance(trade['info'], dict)
        assert isinstance(trade['symbol'], str)
        assert isinstance(trade['timestamp'], int)
        assert isinstance(trade['datetime'], str)
        assert isinstance(trade['order'], str)
        assert isinstance(trade['type'], str)
        assert isinstance(trade['side'], str)
"""
'''