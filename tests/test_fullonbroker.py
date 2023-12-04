from libs import strategy, log, settings, cache, exchange, database
from libs.bot import Bot
from libs.btrader.fullonbroker import FullonBroker
from libs.btrader.fullonstore import FullonStore
from libs.structs.order_struct import OrderStruct
from run.user_manager import UserManager
import backtrader as bt
import pytest
import random
import arrow
from collections import deque, namedtuple
from unittest.mock import PropertyMock, create_autospec, MagicMock, patch
from datetime import datetime
import pytz

@pytest.fixture
def fullon_owner():
    # Define a namedtuple type and create an instance
    Parameter = namedtuple('Parameter', 'leverage')
    p = Parameter(leverage=2)

    # Do the same for Owner
    Owner = namedtuple('Owner', 'p')
    yield Owner(p=p)


@pytest.fixture
def fullon_feed():
    user = UserManager()
    UID = user.get_user_id(mail='admin@fullon')
    with database.Database() as dbase:
        exch = dbase.get_exchange(user_id=UID)[0]

    class test_feed():
        ex_base = 'USD'
        base = 'BTC'
        ex_id = exch.ex_id
        symbol = 'MATIC/USD'
        cat_ex_id = 'blah'
        exchange_name = 'kraken',
        order_id = "1"

    yield test_feed()



@pytest.fixture
def fullon_datas(fullon_feed):
    user = UserManager()
    UID = user.get_user_id(mail='admin@fullon')
    with database.Database() as dbase:
        exch = dbase.get_exchange(user_id=UID)[0]

    class DateTimeList:
        def __init__(self, dt_list):
            self.dt_list = dt_list
            self.tz = None

        def __getitem__(self, index):
            return self.dt_list[index]

        def datetime(self, index=None):
            if index is not None:
                return self.dt_list[index]
            else:
                return self.dt_list

        def set_timezone(self, timezone):
            self.tz = pytz.timezone(timezone)
            self.dt_list = [self.tz.localize(dt.replace(tzinfo=None)) for dt in self.dt_list]

    class params:
        sessionend = arrow.utcnow()

    class datas():
        ex_id = exch.ex_id
        exchange = exch.name
        uid = UID
        ex_base = 'USD'
        base = 'BTC'
        symbol = 'MATIC/USD'
        trading = True
        bot_id = '000000000-b4b3-45b2-936b-b6894b81762d'
        futures = True
        size_pct = 10
        feed = fullon_feed
        close = ['1']
        datetime = DateTimeList([arrow.utcnow().datetime])
        p = params()
        date2num = bt.feed.date2num

    yield datas()


@pytest.fixture
def fullon_broker(fullon_feed):
    store = FullonBroker(feed=fullon_feed)
    yield store
    del store



'''
def test_buy(fullon_broker, fullon_datas, fullon_owner):
    # Prepare expected order dictionary

    expected_order_dict = {
        'order_id': "a1",
        'symbol': fullon_datas.symbol,
        'side': 'buy',
        'volume': 10  # This should be the volume of your order
    }
    expected_order_dict = OrderStruct.from_dict(expected_order_dict)
    print(expected_order_dict)

    # Mock the return value from the FullonStore.create_order method
    with patch.object(FullonStore, 'create_order', return_value=expected_order_dict) as mock_create_order:

        # Call the buy method
        result = fullon_broker.buy(
            owner=fullon_owner,
            data=fullon_datas,
            size=10,  # Define size of your order
            price=100,  # Define price of your order
            plimit=None,
            exectype=bt.Order.Market,
            valid=None,
            tradeid=0,
            oco=None,
            trailamount=None,
            trailpercent=None,
            command=None,
            side="buy"
        )

        # We're not asserting against the mock_create_order, because we want to compare the actual OrderStruct with the expected one.
        assert result == expected_order_dict


def test_sell(fullon_broker, fullon_datas, fullon_owner):
    # Prepare expected order dictionary

    expected_order_dict = {
        'order_id': "a1",
        'symbol': fullon_datas.symbol,
        'side': 'Sell',
        'volume': 10  # This should be the volume of your order
    }

    # Mock the return value from the FullonStore.create_order method
    with patch.object(FullonStore, 'create_order', return_value=expected_order_dict) as mock_create_order:

        # Call the buy method
        result = fullon_broker.sell(
            owner=fullon_owner,
            data=fullon_datas,
            size=10,  # Define size of your order
            price=100,  # Define price of your order
            plimit=None,
            exectype=bt.Order.Market,
            valid=None,
            tradeid=0,
            oco=None,
            trailamount=None,
            trailpercent=None,
            command=None,
            side="sell"
        )

        # We're not asserting against the mock_create_order, because we want to compare the actual OrderStruct with the expected one.
        assert result == expected_order_dict
'''
