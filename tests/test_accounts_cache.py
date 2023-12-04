from __future__ import unicode_literals, print_function
from requests.cookies import MockRequest
from fullon.libs.structs.exchange_struct import ExchangeStruct
from run import system_manager
from run.user_manager import UserManager
import json
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


def test_get_full_account_1(mock_store, user_ex):
    expected_datas = {'BTC': 0.001}
    expected_datas = json.dumps(expected_datas)
    mock_store.conn.hget.return_value = expected_datas
    result = mock_store.get_full_account(exchange=user_ex.ex_id,
                                         currency='BTC')
    assert result is not None
    assert float(result) >= 0.0000


def test_get_full_account_2(store, user_ex):
    result = store.get_full_account(exchange=user_ex.ex_id,
                                    currency='BTD')
    assert result == {}


def test_get_position_1(mock_store, user_ex):
    expected_datas = {'ETHUSDT': {
                                    'cost':  1699.8,
                                    'volume': 2000.0,
                                    'fee': 2.039761,
                                    'price': 0.8499},
                      'timestamp': 1684802146.139731}
    expected_datas = json.dumps(expected_datas)
    mock_store.conn.hget.return_value = expected_datas
    mock_store.get_exchange.return_value = user_ex
    result = mock_store.get_position(symbol='ETHUSDT',
                                     ex_id=user_ex.ex_id)

    # The mock should have been called once with the specified arguments
    #mock_store.conn.hget.assert_called_once_with("account_positions", f"{user_ex.uid}:{user_ex.ex_id}")

    assert result.symbol == 'ETHUSDT'
    assert result.timestamp > 1604202926.668054
    assert result.cost >= 0


def test_get_position_2(store, user_ex):
    result = store.get_position(symbol='XRPING',
                                ex_id=user_ex.ex_id)
    assert result.symbol == 'XRPING'
    assert result.cost >= 0
    assert result.volume >= 0
    assert result.price >= 0


def test_all_positions_1(mock_store):
    # Mock data setup, assuming each key represents a different account or exchange ID
    expected_datas = {
        'someexchangeid': json.dumps({
            'ASYMBOL': {
                    'cost':  1699.8,
                    'volume': 2000.0,
                    'fee': 2.039761,
                    'price': 0.8499,
                    'timestamp': 1684802146.139731
                    }
                }
            )
        }
    # Mock the Redis hgetall to return the expected data
    mock_store.conn.hgetall.return_value = {k.encode('utf-8'): v.encode('utf-8') for k, v in expected_datas.items()}
    # Execute the function
    result = mock_store.get_all_positions()
    # Assertions
    assert len(result) > 0  # Ensure there are positions
    for position in result:
        assert position.ex_id == 'someexchangeid'
        assert position.symbol == 'ASYMBOL'
        assert position.timestamp > 1604202926.668054
        assert position.cost >= 0
        # Add more assertions as needed for volume, fee, price, etc.


def test_all_positions_2(mock_store):
    # Mock data setup, assuming each key represents a different account or exchange ID
    expected_datas = {}
    # Mock the Redis hgetall to return the expected data
    mock_store.conn.hgetall.return_value = {k.encode('utf-8'): v.encode('utf-8') for k, v in expected_datas.items()}
    # Execute the function
    result = mock_store.get_all_positions()
    # Assertions
    assert len(result) == 0  # Ensure there are positions
