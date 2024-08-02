"""
Test file for account module
"""
from __future__ import unicode_literals, print_function
from libs import log, database, cache
from libs.exchange_methods import ExchangeMethods
from run.system_manager import AccountManager
from run.user_manager import UserManager
from libs.structs.exchange_struct import ExchangeStruct
import unittest.mock
import pytest
import time
from typing import Dict

logger = log.fullon_logger(__name__)



#exchange_list = ['kraken', 'bitmex']
exchange_list = ['kraken']


@pytest.fixture(scope="module")
def account():
    am = AccountManager()
    yield am
    del am


@pytest.fixture(scope="module")
def exchange_params():
    user = UserManager()
    uid = user.get_user_id(mail='admin@fullon')
    details = user.user_details(uid=uid)
    exchanges = {}
    for exchange in exchange_list:
        ex = details['exchanges'][exchange]
        exchanges[exchange] = {
            'cat_ex_id': ex['cat_ex_id'],
            'uid': f'{uid}',
            'ex_id': ex['ex_id'],
            'name': ex['ex_named']
        }
    yield exchanges




@pytest.fixture(scope="module")
def exchange_instance(request, exchange_params):
    exchange_name = request.param
    params = ExchangeStruct.from_dict(exchange_params[exchange_name])
    em = ExchangeMethods(
           exchange=exchange_name,
           params=params)
    yield em
    em.stop()
    del em


def wait(name, store):
    res = False
    for _ in range(0, 40):
        proc = store.get_process(tipe='account', key=name)
        if 'Updated' in proc['message']:
            res = True
            break
        time.sleep(0.5)
    return res

@pytest.mark.order(1)
@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_update_user_account(account, exchange_instance, store):
    """ description """
    result = account.update_user_account(ex_id=exchange_instance.ex_id)
    assert result is None
    res = wait(name=exchange_instance.ex_key, store=store)
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

