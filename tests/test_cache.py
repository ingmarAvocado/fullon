from __future__ import unicode_literals, print_function
from run.user_manager import UserManager
import pytest
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
        params = dbase.get_exchange(exchange_name='kraken')[0]

    print(params)

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


@pytest.mark.order(5)
def test_get_symbols(store, user_ex):
    symbols = store.get_symbols(exchange='kraken')
    assert len(symbols) > 0
    assert isinstance(symbols[0].symbol, str)
    assert isinstance(symbols[0].exchange_name, str)
    assert isinstance(symbols[0].backtest, int)
    assert isinstance(symbols[0].updateframe, str)
    assert isinstance(symbols[0].decimals, int)
    assert isinstance(symbols[0].base, str)
    assert isinstance(symbols[0].ohlcv_view, str)


@pytest.mark.order(6)
def test_get_symbol(store, user_ex):
    symbol = 'BTC/USD'
    cat_ex_id = user_ex.cat_ex_id
    symbol_data = store.get_symbol(symbol=symbol,
                                   cat_ex_id=cat_ex_id)
    assert symbol_data is not None
    assert symbol_data.symbol == symbol
    assert symbol_data.cat_ex_id == cat_ex_id


@pytest.mark.order(7)
def test_prepare_cache(store):
    result = store.prepare_cache()
    assert result is None
