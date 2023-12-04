from libs import strategy
from libs.strategy import drylive_strategy as strategy
from libs.structs.trade_struct import TradeStruct
from libs.database import Database
import arrow
import backtrader as bt
import pytest
from unittest.mock import MagicMock, patch

setattr(Database, 'save_dry_trade', MagicMock)


class MockStratParams:
    def __init__(self, size_pct, leverage, take_profit, stop_loss, timeout, size):
        self.size_pct = size_pct
        self.leverage = leverage
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.timeout = timeout
        self.size = 10

@pytest.fixture
def order():
    order = bt.Order
    yield order
'''
@pytest.fixture
def feed():
    bot1 = Bot('00000000-0000-0000-0000-000000000001')
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
    trade.cost = 1000  # trade value
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
    trade.cost = 0  # trade value
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
    trade.cost = -1000  # trade value
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
        ex_id = '00000000-0000-0000-0000-000000000001'

    class data:
        symbol = "BTC/USD"
        feed = strat_feed()

    class helper:
        uid = '00000000-0000-0000-0000-000000000001'
        bot_id = '00000000-0000-0000-0000-000000000002'

    cerebro = bt.Cerebro()
    broker = cerebro.getbroker()
    cerebro.addstrategy(strategy.Strategy)
    strat = cerebro.strats[0][0][0]
    strat.cash[0] = 1000
    strat.tick[0] = 10
    datas = [data()]
    curtime = [arrow.utcnow().format()]
    setattr(strat, "p", MockStratParams(size_pct=10, leverage=1, take_profit=10, stop_loss=10, timeout=10, size=10))
    setattr(strat, "broker", broker)
    setattr(strat, "datas", datas)
    setattr(strat, "helper", helper())
    setattr(strat, "curtime", curtime)
    size = {0: 100}
    setattr(strat, "size", size)
    yield strat

@pytest.fixture
def trade_updated(strat, trade):
    _trade = strat._update_trade_details(self=strat, trade=trade, datas_num=0)
    yield _trade


def test_entry(strat):
    entry = strat.entry(self=strat, datas_num=0, price=10)
    assert entry == 10.0

'''
def test__save_status(strat):
    with patch.object(strat, '_get_simul_status', return_value=True) as mock_method:
        assert strat._save_status(self=strat) is True
    mock_method.assert_called_once_with(datas_num=0)
'''


def test_kill_orders(strat):

    class MockOrder:
        pass

    mock_order = MockOrder()

    with patch.object(strat.broker, 'get_orders_open', return_value=[mock_order]) as mock_get_orders_open, \
         patch.object(strat.broker, 'cancel', return_value=None) as mock_cancel:

        strat.kill_orders(self=strat)

        mock_get_orders_open.assert_called_once_with(strat.datas[0])
        mock_cancel.assert_called_once_with(mock_order)


def test_notify_order(strat, order, caplog):
    order.status = 7
    strat.notify_order(self=strat, order=order)
    assert "Trying to buy more than can be afforded, check your entry" in caplog.text

'''
def test_bt_trade_to_struct_buy(strat, open_trade_buy, close_trade_buy):
    # Test for opening trade
    trade = strat._bt_trade_to_struct(self=strat, trade=open_trade_buy)
    assert isinstance(trade, TradeStruct)
    assert trade.cost > 1
    assert trade.price > 1
    assert trade.side is "Buy"
    strat.open_trade = [trade]
    trade = strat._bt_trade_to_struct(self=strat, trade=close_trade_buy)
    assert isinstance(trade, TradeStruct)
    assert trade.cost > 1
    assert trade.price > 1
    assert trade.volume > 1
    assert trade.roi > 1


def test_bt_trade_to_struct_sell(strat, open_trade_sell, close_trade_sell):
    # Test for opening trade
    trade = strat._bt_trade_to_struct(self=strat, trade=open_trade_sell)
    assert isinstance(trade, TradeStruct)
    assert trade.cost > 1
    assert trade.price > 1
    assert trade.side is "Sell"
    strat.open_trade = [trade]
    trade = strat._bt_trade_to_struct(self=strat, trade=close_trade_sell)
    assert isinstance(trade, TradeStruct)
    assert trade.cost > 1
    assert trade.price > 1
    assert trade.volume > 1
    assert trade.roi > 1
'''

@patch('libs.strategy.drylive_strategy.Strategy._bt_trade_to_struct')
@patch.object(Database, 'save_dry_trade')
def test_notify_trade(mock_save_dry_trade, mock_bt_trade_to_struct, strat, open_trade_buy):
    # Setting the necessary parameters for the Strategy instance.
    strat.p = MockStratParams(size_pct=10, leverage=1, take_profit=10, stop_loss=10, timeout=10, size=1)
    strat.datas = [MagicMock()]
    strat.datas[0]._name = '0'
    strat.helper.id = '00000000-0000-0000-0000-000000000002'
    strat.take_profit = [10]
    strat.stop_loss = [10]
    strat.timeout = [10]

    # Create a sample trade structure.
    trade_struct = {
        'uid': '00000000-0000-0000-0000-000000000001',
        'ex_id': '00000000-0000-0000-0000-000000000001',
        'symbol': 'BTC/USD',
        'side': 'Buy',
        'volume': 10,
        'price': 100,
        'cost': 1000,
        'fee': 10,
        'roi': 0,
        'roi_pct': 0
    }
    trade_struct = TradeStruct.from_dict(trade_struct)

    # Mock the return value of the _bt_trade_to_struct method.
    mock_bt_trade_to_struct.return_value = trade_struct

    # Call the notify_trade method.
    strat.notify_trade(self=strat, trade=open_trade_buy)

    # Assert that the _bt_trade_to_struct method was called with the correct arguments.
    mock_bt_trade_to_struct.assert_called_once_with(open_trade_buy)

    # Assert that the save_dry_trade method was called with the correct arguments.
    mock_save_dry_trade.assert_called_once_with(
        bot_id='00000000-0000-0000-0000-000000000002',
        trade=trade_struct,
        reason='strategy'
    )

    # Assert the changes in strategy instance attributes.
    assert strat.p.take_profit == 10
    assert strat.p.stop_loss == 10
    assert strat.p.timeout == 10
    assert strat.datas[0].pos == open_trade_buy.size
