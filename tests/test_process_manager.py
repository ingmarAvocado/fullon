from __future__ import unicode_literals, print_function
from run.tick_manager import TickManager
from run import system_manager
import pytest
import time
import arrow


@pytest.fixture
def process_manager():
    pmanager = system_manager.ProcessManager()
    yield pmanager
    del pmanager


@pytest.fixture
def tick_manager():
    tick_manager = TickManager()
    yield tick_manager
    tick_manager.stop_all()


@pytest.mark.order(1)
def test_get_top(process_manager):
    res = process_manager.get_top()
    #print(res)


@pytest.mark.order(2)
def test_check_tickers(process_manager, tick_manager):
    error = process_manager.check_tickers()
    assert isinstance(error, dict)

@pytest.mark.order(3)
def test_ohlcv_tickers(process_manager, store):
    #store.update_trade_status(key="test1")
    #store.update_trade_status(key="test2")
    error = process_manager.check_ohlcv()
    assert isinstance(error, dict)

@pytest.mark.order(4)
def test_check_user_trades(process_manager, store):
    store.update_user_trade_status(key="1-kraken")
    error = process_manager.check_user_trades()
    assert isinstance(error, dict)
    assert isinstance(error['user_trades'], list)
    assert len(error['user_trades']) == 0
    tstamp = arrow.utcnow().shift(days=-1).timestamp()
    store.update_user_trade_status(key="1-kraken", timestamp=tstamp)
    error = process_manager.check_user_trades()
    assert isinstance(error, dict)
    assert isinstance(error['user_trades'], list)
    assert len(error['user_trades']) > 0

@pytest.mark.order(5)
def test_check_accounts(process_manager, store):
    account = {
            'ASYMBOL': {
                    'cost':  1699.8,
                    'volume': 2000.0,
                    'fee': 2.039761,
                    'price': 0.8499,
                    'timestamp': 1684802146.139731
                    },
            'date': arrow.utcnow().format('YYYY-MM-DD HH:mm:ss')
        }
    store.upsert_user_account(ex_id=1, account=account)
    error = process_manager.check_accounts()
    assert isinstance(error, dict)
    assert isinstance(error['accounts'], list)
    assert len(error['accounts']) == 0
    date = arrow.utcnow().shift(days=-1).format('YYYY-MM-DD HH:mm:ss')
    store.upsert_user_account(ex_id=1, account=account, date=date)
    error = process_manager.check_accounts()
    assert isinstance(error, dict)
    assert isinstance(error['accounts'], list)
    assert len(error['accounts']) > 0
