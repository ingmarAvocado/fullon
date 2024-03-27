from libs import strategy, log, settings, cache, exchange, database
from libs.bot import Bot
from libs.btrader.fullonstore import FullonStore
from libs.structs.order_struct import OrderStruct
from run.user_manager import UserManager
import backtrader as bt
import pytest
import random
import arrow
from collections import deque
from unittest.mock import PropertyMock, create_autospec, MagicMock, patch


@pytest.fixture
def fullon_feed():
    user = UserManager()
    UID = user.get_user_id(mail='admin@fullon')
    with database.Database() as dbase:
        exch = dbase.get_exchange(user_id=UID)[0]

    class test_feed():
        ex_base = 'USD'
        base = 'USD'
        ex_id = exch.ex_id
        symbol = 'MATIC/USD'
    yield test_feed()


@pytest.fixture
def fullon_datas(fullon_feed):
    user = UserManager()
    UID = user.get_user_id(mail='admin@fullon')
    with database.Database() as dbase:
        exch = dbase.get_exchange(user_id=UID)[0]

    class datas():
        ex_id = exch.ex_id
        exchange = exch.name
        uid = UID
        ex_base = 'USD'
        base = 'BTC'
        symbol = 'BTC/USD'
        trading = True
        bot_id = 1
        futures = True
        size_pct = 10
        leverage = 3
        feed = fullon_feed

    yield datas()


@pytest.fixture
def fullon_store(fullon_feed):
    store = FullonStore(feed=fullon_feed)
    yield store
    del store


@pytest.fixture
def fullon_order():
    user = UserManager()
    UID = user.get_user_id(mail='admin@fullon')
    with database.Database() as dbase:
        exch = dbase.get_exchange(user_id=UID)[0]
    order = {"ex_id": exch.ex_id,
             "order_id": "1",
             "cat_ex_id": exch.cat_ex_id,
             "exchange": exch.name,
             "symbol": 'BTC/USD',
             "order_type": "market",
             "volume": 0.0001,
             "price": 25600,
             "plimit": None,
             "side": "Buy",
             "reason": 'signal',
             "command": "spread",
             "subcommand": "60:minutes",
             "leverage": 3,
             "bot_id": 2}
    order = OrderStruct.from_dict(order)
    yield order


def test_get_cash(fullon_store, fullon_datas):
    ret = {"free": 1000.0}
    with patch('libs.btrader.fullonstore.Cache.get_full_account', return_value=ret) as mock_get_full_account:
        cash = fullon_store.get_cash()
        mock_get_full_account.assert_called_once_with(
            exchange=fullon_datas.ex_id, currency=fullon_datas.ex_base)
    assert isinstance(cash, float)
    assert cash > 0


def test_get_position(fullon_store, fullon_datas):
    mock_position = MagicMock()
    mock_position.volume = 10.0
    mock_position.price = 200.0
    with patch('libs.btrader.fullonstore.Cache.get_position', return_value=mock_position) as mock_get_position:

        position, price = fullon_store.get_position(data=fullon_datas)

        mock_get_position.assert_called_once_with(ex_id=fullon_datas.ex_id, symbol=fullon_datas.symbol)
    assert isinstance(price, float)
    assert price > 0
    assert isinstance(position, float)
    assert position > 0


def test_get_symbol_value(fullon_store, fullon_datas):
    mock_value = 27000.1
    symbol = 'BTC/USD'
    with patch('libs.btrader.fullonstore.Cache.get_price', return_value=mock_value) as mock_get_price:
        price = fullon_store.get_symbol_value(symbol=symbol)
        mock_get_price.assert_called_once_with(symbol=symbol)
    assert isinstance(price, float)
    assert price == 27000.1


def test_get_value(fullon_store, fullon_datas):
    position = {}
    position['total'] = 100.1
    with patch('libs.btrader.fullonstore.Cache.get_full_account', return_value=position) as get_full_account:
        position, price = fullon_store.get_position(data=fullon_datas)
        value = fullon_store.get_value()
        get_full_account.assert_called_once_with(exchange=fullon_store.feed.ex_id, currency='USD')
    assert isinstance(value, float)
    assert value > 0


def test_create_order(fullon_store, fullon_order):
    # Mock the return value from the OrderMethods.new_order method
    with patch('libs.order_methods.OrderMethods.new_order', return_value=fullon_order) as mock_new_order:
        # Call the create_order function with the mock order
        result = fullon_store.create_order(order=fullon_order)

        # Check that the new_order function was called with the correct arguments
        mock_new_order.assert_called_once_with(order=fullon_order)

    # Assert the returned result is as expected
    assert isinstance(result, OrderStruct)
    assert result == fullon_order


'''
def test_create_real_order(fullon_store, fullon_order):
    # Mock the return value from the OrderMethods.new_order method
    result = fullon_store.create_order(order=fullon_order)
'''

def test_cancel_order(fullon_store, fullon_order):
    # Mock the return value from the OrderMethods.cancel_order method
    with patch('libs.order_methods.OrderMethods.cancel_order', return_value=True) as mock_cancel_order:
        # Call the cancel_order function with the mock order
        result = fullon_store.cancel_order(order=fullon_order)

        # Check that the cancel_order function was called with the correct arguments
        mock_cancel_order.assert_called_once_with(oid=fullon_order.order_id, ex_id=fullon_order.ex_id)

    # Assert the returned result is as expected
    assert result is True


def test_fetch_open_orders(fullon_store):
    # Define a sample list of orders
    sample_orders = [
        OrderStruct(status='pending'),
        OrderStruct(status='executed'),
        OrderStruct(status='pending')
    ]

    # Mock the get_orders method of OrderCache to return the sample list of orders
    with patch('libs.btrader.fullonstore.Cache.get_orders', return_value=sample_orders) as mock_get_orders:
        # Call the method with the test exchange id
        orders = fullon_store.fetch_open_orders()

        # Assert that the mock was called correctly
        mock_get_orders.assert_called_once_with(ex_id=fullon_store.feed.ex_id)

    # Check that the result is a list and has the correct length
    assert isinstance(orders, list)
    assert len(orders) == 2

    # Check that all orders in the result have the status 'pending'
    for order in orders:
        assert order.status == 'pending'
