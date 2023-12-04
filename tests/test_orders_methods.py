from __future__ import unicode_literals, print_function
from fullon.libs import log, settings
from libs.settings_config import fullon_settings_loader
from libs import cache, database
from libs.order_methods import OrderMethods
from libs.structs.order_struct import OrderStruct
from run.user_manager import UserManager
import arrow
from unittest.mock import patch, MagicMock
import pytest

@pytest.fixture(scope="module")
def order_struct(db_session):
    user = UserManager()
    UID = user.get_user_id(mail='admin@fullon')
    exch = db_session.get_exchange(user_id=UID)[0]
    orderBuy = {
            "ex_id": exch.ex_id,
            "cat_ex_id": exch.cat_ex_id,
            "exchange": exch.name,
            "symbol": 'BTC/USD',
            "order_type": "limit",
            "volume": 0.0001,
            "price": 25600,
            "plimit": None,
            "side": "Buy",
            "reason": 'signal',
            "command": "spread",
            "subcommand": "60:minutes",
            "leverage": 3,
            "bot_id": "00000000-0000-0000-0000-000000000002"}
    orderBuy = OrderStruct.from_dict(orderBuy)
    yield orderBuy


@pytest.fixture(scope="module")
def test_order_startup():
    order = OrderMethods()
    yield order
    del order


def test_get_price_spread(test_order_startup, order_struct):
    """
    Test for the case when the order's command is 'spread'.
    """
    with patch('libs.caches.orders_cache.Cache.get_ticker', return_value=[26000, 25500]) as mock_get_ticker:
        assert test_order_startup._get_price(order_struct) == 25998.7
        mock_get_ticker.assert_called_once_with(
            exchange=order_struct.exchange, symbol=order_struct.symbol)


def test_set_price_twap(test_order_startup, order_struct):
    """
    Test for the case when the order's command is 'twap'.
    """
    order_struct.command = "twap"
    with patch('libs.database_ohlcv.Database._run_default', return_value=[(arrow.utcnow(), 27000)]) as mock_twap:
        assert test_order_startup._get_price(order_struct) == 27000
        mock_twap.assert_called_once()


def test_set_price_vwap(test_order_startup, order_struct):
    """
    Test for the case when the order's command is 'vwap'.
    """
    order_struct.command = "vwap"
    with patch('libs.database_ohlcv.Database._run_default', return_value=[(arrow.utcnow(), 28000)]) as mock_vwap:
        assert test_order_startup._get_price(order_struct) == 28000
        mock_vwap.assert_called_once()


def test_can_place_order(test_order_startup, order_struct):
    """
    Test for the case when the order can be placed.
    """
    mock_exchange = MagicMock()
    mock_exchange.quote_symbol.return_value = 'USD'
    mock_exchange.minimum_order_cost.return_value = 0.1
    mock_exchange.uid = '3223423423'
    with patch('libs.order_methods.OrderMethods._get_exchange_cur', return_value=mock_exchange) as mock__get_exchange_cur, \
        patch('libs.caches.orders_cache.Cache.get_full_accounts', return_value={'USD': {"free": 8000.0}}) as mock_get_full_accounts, \
        patch('libs.caches.orders_cache.Cache.get_ticker', return_value=[26000, 25500]) as mock_get_ticker:
        assert test_order_startup._can_place_order(order_struct) is False
        mock__get_exchange_cur.assert_called_once()
        mock_get_full_accounts.assert_called_once()
        mock_get_ticker.assert_called_once_with(exchange=order_struct.exchange, symbol=order_struct.symbol)


def test_process_now_market(test_order_startup, order_struct):
    """
    Test for the case when the order's type is 'market'.
    """
    order_struct.order_type = "market"
    new_order = OrderStruct()
    new_order.status = 'closed'
    #new_order = new_order.to_dict()
    new_order.order_id = "myid"

    with patch('libs.order_methods.OrderMethods._place_order', return_value=new_order) as mock_place_order, \
         patch('libs.caches.orders_cache.Cache.get_order_status', return_value=new_order.to_dict()) as mock_get_order_status:
        res = test_order_startup._process_now_market(order_struct)
        assert res.order_id == "myid"


def test_await_order_closure(test_order_startup, order_struct):
    """
    Test for the _await_order_closure method.
    """
    # Setup
    mock_cache = MagicMock()
    order_struct.status = 'closed'
    order_struct.order_id = 'order1'

    # Mocking the sleep method to avoid actual wait time in the test
    with patch('time.sleep', return_value=None) as mock_sleep, \
         patch('libs.caches.orders_cache.Cache.get_order_status', return_value=order_struct) as mock_get_order_status, \
         patch('libs.order_methods.OrderMethods._cancel_and_replace_order', return_value=order_struct) as mock_cancel_replace:
        # Test
        result = test_order_startup._await_order_closure(order_struct)

        # Assert that the order id is returned
        assert result == order_struct

        # Assert that get_order_status was called with the correct arguments
        mock_get_order_status.assert_called_with(ex_id=order_struct.ex_id,
                                                 oid=order_struct.order_id)

        # Assert that time.sleep was not called
        #assert mock_sleep.call_count == 0

        # Assert that _cancel_and_replace_order was not called because the order was closed
        assert mock_cancel_replace.assert_not_called() is None


def test_cancel_order(test_order_startup, order_struct):
    """
    Test for the cancel_order method.
    """
    # Setup
    order_struct.status = "canceled"
    order_struct.order_id = "order1"

    mock_exchange = MagicMock()
    test_order_startup._get_exchange_cur = MagicMock(return_value=mock_exchange)

    # Mocking the return value of get_order_status
    with patch('libs.caches.orders_cache.Cache.get_order_status', return_value=order_struct) as mock_get_order_status, \
         patch('libs.caches.orders_cache.Cache.save_order_data', return_value=True), \
         patch('libs.order_methods.OrderMethods._get_exchange_cur', return_value=mock_exchange), \
         patch('time.sleep', return_value=None):

        # Test
        result = test_order_startup.cancel_order(oid=order_struct.order_id, ex_id=order_struct.ex_id)

        # Assert that the result is True
        assert result is True

        # Assert that cancel_order was called with the correct arguments
        mock_exchange.cancel_order.assert_called_with(oid=order_struct.order_id)

        # Assert that get_order_status was called with the correct arguments
        mock_get_order_status.assert_called_with(
            ex_id=order_struct.ex_id, oid=order_struct.order_id)


def test_get_minimum_order(test_order_startup, order_struct):
    """
    Test for the get_minimum_order method.
    """
    # Setup
    mock_value = 0.001  # Example value - you can use any other number as well
    mock_exchange = MagicMock()
    mock_exchange.minimum_order_cost = MagicMock(return_value=mock_value)
    test_order_startup._get_exchange_cur = MagicMock(return_value=mock_exchange)

    with patch('libs.order_methods.OrderMethods._get_exchange_cur', return_value=mock_exchange):
        # Test
        result = test_order_startup.get_minimum_order(ex_id=order_struct.ex_id, symbol=order_struct.symbol)
        # Assert
        assert result == mock_value
        mock_exchange.minimum_order_cost.assert_called_with(symbol=order_struct.symbol)
