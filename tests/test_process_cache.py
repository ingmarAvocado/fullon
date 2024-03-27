from __future__ import unicode_literals, print_function
from run.user_manager import UserManager
import pytest
import arrow
from libs import cache, database
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
def setup_new_process(store):
    store.new_process(tipe=tipe_tick,
                      key=key_kraken,
                      pid=pid_1000,
                      params=params,
                      message=message_new)
    store.new_process(tipe=tipe_ohlcv,
                      key=key_kraken,
                      pid=pid_1001,
                      params=params,
                      message=message_new)
    yield
    # Teardown steps can be added here if necessary

@pytest.fixture(scope="module")
def user_ex(store):
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
def test_new_process(store):
    # Test new_process for tick type
    result_tick = store.new_process(tipe=tipe_tick,
                                    key=key_kraken,
                                    pid=pid_1000,
                                    params=params,
                                    message=message_new)
    #assert result_tick == 1

    # Test new_process for ohlcv type
    result_ohlcv = store.new_process(tipe=tipe_ohlcv,
                                     key=key_kraken,
                                     pid=pid_1001,
                                     params=params,
                                     message=message_new)
    #assert result_ohlcv == 1


@pytest.mark.order(2)
def test_get_process(store, setup_new_process):
    result = store.get_process(tipe=tipe_tick, key=key_kraken)
    date = arrow.get(result['timestamp'])
    assert isinstance(date, arrow.Arrow)


@pytest.mark.order(3)
def test_update_process_1(store, setup_new_process):
    # Test update_process for tick type
    result_tick = store.update_process(tipe=tipe_tick,
                                       key=key_kraken,
                                       message=message_update)
    assert result_tick is True

    # Test update_process for ohlcv type
    result_ohlcv = store.update_process(tipe=tipe_ohlcv,
                                        key=key_kraken,
                                        message=message_update)
    assert result_ohlcv is True


@pytest.mark.order(4)
def test_update_process_2(store, setup_new_process):
    """ Assuming the store and setup_new_process fixtures create t
    he necessary processes"""
    result = store.update_process(tipe=tipe_tick,
                                  key=key_kraken,
                                  message=message_update)
    assert result is True
    tipe_ohlcv = "ohlcv"
    result = store.update_process(tipe=tipe_ohlcv,
                                  key=key_kraken,
                                  message=message_update)
    assert result is True


@pytest.mark.order(5)
def test_get_top_1(store, setup_new_process):
    result = store.get_top()
    assert len(result) > 0
    fields = ['type', 'key', 'params', 'message', 'timestamp']
    for res in result:
        for field in fields:
            assert field in res


@pytest.mark.order(6)
def test_get_top_2(store, setup_new_process):
    comp_ohlcv = "ohlcv"
    result = store.get_top(deltatime=0.0001, comp=comp_ohlcv)
    assert len(result) > 0

    for res in result:
        assert res['type'] == comp_ohlcv

    comp_ohlcvv = "ohlcvv"
    result = store.get_top(deltatime=0.0001, comp=comp_ohlcvv)
    assert len(result) == 0


@pytest.mark.order(7)
def test_get_top_3(store, setup_new_process):
    comp_ohlcv = "ohlcv"
    result = store.get_top(deltatime=None, comp=comp_ohlcv)
    assert len(result) > 0

    for res in result:
        assert res['type'] == comp_ohlcv

    comp_ohlcvv = "ohlcvv"
    result = store.get_top(deltatime=None, comp=comp_ohlcvv)
    assert len(result) == 0


@pytest.mark.order(8)
def test_get_top_4(store, setup_new_process):
    comp = None
    result = store.get_top(deltatime=0.0001, comp=comp)
    assert len(result) > 0

    fields = ['type', 'key', 'params', 'message', 'timestamp']
    for res in result:
        for field in fields:
            assert field in res

