"""
Test file for account module
"""
from __future__ import unicode_literals, print_function
from libs import log, database, cache
from run.system_manager import AccountManager
import unittest.mock
import pytest
import time

logger = log.fullon_logger(__name__)

EX_IDS_FALSE = ["00000000-0000-0000-0000-000000000001"]
EX_IDS_TRUE = ["00000000-0000-0000-0000-000000000002"]


@pytest.fixture(scope="module")
def account():
    am = AccountManager()
    yield am
    del am

@pytest.fixture(scope="module")
def dbase():
    dbase = database.Database()
    yield dbase
    del dbase

@pytest.fixture(scope="module")
def store():
    store = cache.Cache()
    yield store
    del store


def wait(store, name):
    res = False
    for attempts in range(0, 40):
        proc = store.get_process(tipe='account', key=name)
        if 'Updated' in proc['message']:
            res = True
            break
        time.sleep(0.5)
    return res


def test_update_user_account(account, store):
    """ description """
    exch = store.get_exchanges()[0]
    result = account.update_user_account(ex_id=exch.ex_id)
    res = wait(store, exch.name)
    account.stop_all()
    assert res is True


def test_run_account_loop(account, store):
    # Run the account loop
    account.run_account_loop()
    exch = store.get_exchanges()[0]
    res = wait(store, exch.name)
    account.stop_all()
    assert res is True

'''
def test_update_user_account_false(account):
    """Test updating user accounts with incorrect ex_ids."""
    for value in EX_IDS_FALSE:
        if value:
            result = account.update_user_account(ex_id=value, test=True)
            assert result is None
'''

