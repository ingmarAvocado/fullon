from libs import strategy
from libs.strategy import drylive_strategy as strategy
from libs.structs.trade_struct import TradeStruct
from libs.database import Database
import arrow
import backtrader as bt
import pytest
from unittest.mock import MagicMock, patch


class MockStratParams:
    def __init__(self, size_pct, leverage, take_profit, stop_loss, timeout, size):
        self.size_pct = size_pct
        self.leverage = leverage
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.timeout = timeout
        self.size = size


@pytest.fixture
def order():
    order = bt.Order
    yield order
'''
@pytest.fixture
def feed():
    bot1 = Bot(1)
    feed = bot1.str_feeds[0]
    yield feed
'''


@pytest.fixture
def open_trade_buy():
    class data:
        _name = '0'
    trade = MagicMock(spec=bt.Trade)
    setattr(trade, "data", data)
    trade.price = 100  # trade price
    trade.size = 10  # trade size
    trade.value = 1000  # trade value
    trade.commission = 10  # trade commission
    trade.justopened = True

    yield trade


@pytest.fixture
def close_trade_buy():
    class data:
        _name = '0'
    trade = MagicMock(spec=bt.Trade)
    setattr(trade, "data", data)
    trade.price = 110  # trade price
    trade.size = 0  # trade size
    trade.value = 0  # trade value
    trade.pnl = 100
    trade.commission = 3  # trade commission
    trade.pnlcomm = 97  # profit/loss including commission
    trade.justopened = False
    yield trade


@pytest.fixture
def open_trade_sell():
    class data:
        _name = '0'
    trade = MagicMock(spec=bt.Trade)
    setattr(trade, "data", data)
    trade.price = 100  # trade price
    trade.size = -10  # trade size
    trade.value = -1000  # trade value
    trade.commission = 10  # trade commission
    trade.justopened = True

    yield trade


@pytest.fixture
def close_trade_sell():
    class data:
        _name = '0'
    trade = MagicMock(spec=bt.Trade)
    setattr(trade, "data", data)
    trade.price = 90  # trade price
    trade.size = 0  # trade size
    trade.value = 0  # trade value
    trade.pnl = 100
    trade.commission = 3  # trade commission
    trade.pnlcomm = 97  # profit/loss including commission
    trade.justopened = False
    yield trade


@pytest.fixture
def strat():
    class strat_feed:
        ex_id = 1

    class data:
        symbol = "BTC/USD"
        feed = strat_feed()
        _name = 0

    class helper:
        uid = 1
        bot_id = 2

    cerebro = bt.Cerebro()
    broker = cerebro.getbroker()
    cerebro.addstrategy(strategy.Strategy)
    strat = cerebro.strats[0][0][0]
    datas = [data(), data()]
    curtime = [arrow.utcnow().format()]
    setattr(strat, "p", MockStratParams(size_pct=10, leverage=1, take_profit=10, stop_loss=10, timeout=10, size=10))
    setattr(strat, "broker", broker)
    setattr(strat, "datas", datas)
    setattr(strat, "helper", helper())
    setattr(strat, "curtime", curtime)
    setattr(strat, "size", {0: 10})
    setattr(strat, "str_feed", datas)
    setattr(strat, "last_bar_date", {0: arrow.get('2023-07-17T00:00:00+00:00')})
    yield strat


@pytest.fixture
def trade_updated(strat, trade):
    _trade = strat._update_trade_details(self=strat, trade=trade, datas_num=0)
    yield _trade


@pytest.mark.order(1)
def test_entry(strat):
    entry = strat.entry(self=strat, datas_num=0, price=10)
    assert entry == 1.0 #entry / price


@pytest.mark.order(2)
def test_is_new_bar(strat):
    res = strat._is_new_bar(self=strat, feed=0)
    assert res is False
    setattr(strat.datas[1], "datetime", {0: '2023-07-17T00:00:00+00:00'})
    res = strat._is_new_bar(self=strat, feed=1)
    assert res is True
    setattr(strat, "last_candle_date", {1: '2023-07-17T00:00:00+00:00'})
    res = strat._is_new_bar(self=strat, feed=1)
    assert res is False
    setattr(strat.datas[1], "datetime", {0: '2023-07-17T00:01:00+00:00'})
    res = strat._is_new_bar(self=strat, feed=1)
    assert res is True
