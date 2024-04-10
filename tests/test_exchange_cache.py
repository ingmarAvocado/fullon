from __future__ import unicode_literals, print_function
import pytest
from unittest.mock import MagicMock
from run.user_manager import UserManager
from libs import cache, database


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
    return cache.Cache(reset=True)

@pytest.fixture(scope="module")
def mock_store(store):
    # Make a copy of the original store object
    mock_store = cache.Cache(reset=True)
    # Mock the conn object and its methods
    mock_store.conn = MagicMock()
    mock_store.get_exchange = MagicMock()
    yield mock_store
    del mock_store


@pytest.fixture(scope="module")
def user_ex():
    user = UserManager()
    uid = user.get_user_id(mail='admin@fullon')
    details = user.user_details(uid=uid)
    ex_id = details['exchanges']['kraken']['ex_id']
    ex_name = details['exchanges']['kraken']['ex_named']
    with database.Database() as dbase:
        params = dbase.get_exchange(user_id=uid)[0]

    class userStruct():
        uid: str
        ex_id: str
        cat_ex_id: str

        def __init__(self, uid, ex_id, cat_ex_id):
            self.uid = uid
            self.ex_id = ex_id
            self.cat_ex_id = cat_ex_id
            self.name = ex_name

    return userStruct(uid=uid,
                      ex_id=ex_id,
                      cat_ex_id=params.cat_ex_id)

@pytest.mark.order(1)
def test_get_cat_exchanges(store):
    store.conn.delete('cat_exchanges')
    result = store.get_cat_exchanges()
    assert len(result) > 0


@pytest.mark.order(2)
def test_get_exchange_symbols(store):
    result = store.get_exchange_symbols("2")
    assert len(result) == 0


@pytest.mark.order(3)
def test_get_exchange1(store, user_ex):
    result = store.get_exchange(ex_id=user_ex.ex_id)
    #assert isinstance(result.name, str)


@pytest.mark.order(4)
def test_get_exchange2(store, user_ex):
    result = store.get_exchange(ex_id='29')
    assert result.name is ''
    #assert isinstance(result, ExchangeStruct)

