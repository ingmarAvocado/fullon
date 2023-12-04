from __future__ import unicode_literals, print_function
import sys
from requests.cookies import MockRequest
from fullon.libs import log, settings
from fullon.libs.settings_config import fullon_settings_loader
from fullon.libs.structs.exchange_struct import ExchangeStruct
from run import system_manager
from run.user_manager import UserManager
import json
import pytest
import arrow
from libs.caches import orders_cache
from libs import database
from unittest.mock import MagicMock


# Test data
tipe_tick = "tick"
tipe_ohlcv = "ohlcv"
key_kraken = "kraken"
pid_1000 = "1000"
pid_1001 = "1001"
params = "test param"
message_new = "new"
message_update = "update"

@pytest.fixture(scope="module")
def store():
    return orders_cache.Cache()


@pytest.fixture
def user():
    user = UserManager()
    UID = user.get_user_id(mail='admin@fullon')
    with database.Database() as dbase:
        exch = dbase.get_exchange(user_id=UID)[0]

    class test_user():
        ex_id = exch.ex_id

    yield test_user()


def test_get_orders(store, user):
    # Test new_process for tick type
    res = store.get_orders(ex_id=user.ex_id)
    assert isinstance(res, list)
