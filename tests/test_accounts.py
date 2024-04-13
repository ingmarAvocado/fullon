"""
Test file for account module
"""
from __future__ import unicode_literals, print_function
from libs import log, database, cache
from run.system_manager import AccountManager
from run.user_manager import UserManager
import unittest.mock
import pytest
import time

logger = log.fullon_logger(__name__)


@pytest.fixture(scope="module")
def account():
    am = AccountManager()
    yield am
    del am

@pytest.fixture(scope="module")
def exch(dbase, store):
    user = UserManager()
    UID = user.get_user_id(mail='admin@fullon')
    exch = dbase.get_exchange(user_id=UID)[0]
    exch = store.get_exchange(ex_id=exch.ex_id)
    yield exch


def wait(store, name):
    res = False
    for attempts in range(0, 40):
        proc = store.get_process(tipe='account', key=name)
        if 'Updated' in proc['message']:
            res = True
            break
        time.sleep(0.5)
    return res


@pytest.mark.order(1)
def test_update_user_account(account, store, exch):
    """ description """
    result = account.update_user_account(ex_id=exch.ex_id)
    assert result is None
    res = wait(store, exch.name)
    account.stop_all()
    assert res is True

'''

@pytest.mark.order(1)
def test_run_account_loop(account, store, exch):
    # Run the account loop
    account.run_account_loop()
    res = wait(store, exch.name)
    account.stop_all()
    assert res is True


def test_update_user_account_false(account):
    """Test updating user accounts with incorrect ex_ids."""
    for value in EX_IDS_FALSE:
        if value:
            result = account.update_user_account(ex_id=value, test=True)
            assert result is None
'''

