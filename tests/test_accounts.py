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
ex_names = {}

@pytest.fixture(scope="module")
def account():
    am = AccountManager()
    yield am
    del am


@pytest.fixture(scope="module")
def exchange_params() -> Dict:
    user = UserManager()
    uid = user.get_user_id(mail='admin@fullon')
    details = user.user_details(uid=uid)
    ex1 = details['exchanges']['kraken']
    ex2 = details['exchanges']['bitmex']
    ex_names['kraken'] = ex1['ex_named']
    ex_names['bitmex'] = ex2['ex_named']
    return {
        'kraken': {
            'cat_ex_id': ex1['cat_ex_id'],
            'uid': f'{uid}',
            'ex_id': ex1['ex_id']
        },
        'bitmex': {
            'cat_ex_id': ex2['cat_ex_id'],
            'uid': f'{uid}',
            'ex_id': ex2['ex_id'],
        }
        # Add more exchanges here
    }




@pytest.fixture(scope="module")
def exchange_instance(request, exchange_params):
    exchange_name = request.param
    params = ExchangeStruct.from_dict(exchange_params[exchange_name])
    em = ExchangeMethods(
           exchange=exchange_name,
           params=params)
    con = em.connect_websocket()
    assert isinstance(con, bool)
    yield em
    con = em.stop_websockets()
    assert isinstance(con, bool)
    con = em.stop()
    del em


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
@pytest.mark.parametrize("exchange_instance", exchange_list, indirect=True)
def test_update_user_account(account, store, exchange_instance, exchange_params):
    """ description """
    result = account.update_user_account(ex_id=exchange_instance.ex_id)
    assert result is None
    exch_name = ex_names[exchange_instance.exchange]
    res = wait(store, exch_name)
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

