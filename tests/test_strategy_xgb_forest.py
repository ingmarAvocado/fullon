"""
import backtrader as bt
import pytest
from fullon.strategies.xgb_forest.strategy import Strategy
from unittest.mock import MagicMock, patch
import arrow
from backtrader import TimeFrame


class MockStratParams:
    def __init__(self, size_pct, leverage, take_profit, stop_loss, timeout, size):
        self.size_pct = size_pct
        self.leverage = leverage
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.timeout = timeout
        self.size = size


@pytest.fixture
def strat():
    class strat_feed:
        ex_id = 1
        period = 'minutes'
        exchange_name = "kraken"

    class data:
        symbol = "BTC/USD"
        feed = strat_feed()
        _table = 'kraken_btc_usd.trades'
        compression = 240
        period = TimeFrame.Minutes

    class helper:
        uid = 1
        bot_id = 1

    cerebro = bt.Cerebro()
    broker = cerebro.getbroker()
    cerebro.addstrategy(Strategy)
    strat = cerebro.strats[0][0][0]
    strat.cash[0] = 1000
    strat.tick[0] = 10
    datas = [data(), data()]
    curtime = [arrow.utcnow().format()]
    setattr(strat, "p", MockStratParams(size_pct=10, leverage=1, take_profit=10, stop_loss=10, timeout=10, size=10))
    setattr(strat, "broker", broker)
    setattr(strat, "datas", datas)
    setattr(strat, "helper", helper())
    setattr(strat, "curtime", curtime)
    setattr(strat, "size", {0: 10})
    yield strat



'''
@pytest.fixture
def trade_updated(strat, trade):
    _trade = strat._update_trade_details(self=strat, trade=trade, datas_num=0)
    yield _trade


def test_entry(strat):
    entry = strat.entry(self=strat, datas_num=0, price=10)
    assert entry == 1.0 #entry / price 


def test_is_new_candle(strat):
    res = strat._is_new_candle(self=strat, feed=0)
    assert res is False
    setattr(strat.datas[1], "datetime", {0: '2023-07-17T00:00:00+00:00'})
    res = strat._is_new_candle(self=strat, feed=1)
    assert res is True
    setattr(strat, "last_candle_date", {1: '2023-07-17T00:00:00+00:00'})
    res = strat._is_new_candle(self=strat, feed=1)
    assert res is False
    setattr(strat.datas[1], "datetime", {0: '2023-07-17T00:01:00+00:00'})
    res = strat._is_new_candle(self=strat, feed=1)
    assert res is True
'''
"""
