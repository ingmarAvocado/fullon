from __future__ import unicode_literals, print_function
import sys
from libs.models.exchange_model import Database
from run.user_manager import UserManager
import pytest


'''
@pytest.fixture(scope="module")
def install_exchanges(uid: int):
    """
    """
    user = UserManager()
    with Database() as dbase:
        cat_ex_id = dbase.get_cat_exchanges(exchange='kraken')[0][0]
    exchange = {
        "uid": uid,
        "cat_ex_id": cat_ex_id,
        "name": "pytest",
        "test": "False",
        "active": "True"}
    ex_id = user.add_exchange(exch=ExchangeStruct.from_dict(exchange))
    yield (ex_id, cat_ex_id)
    assert user.remove_user_exchange(ex_id=ex_id) is True
'''


@pytest.fixture(scope="module")
def dbase():
    with Database() as dbase:
        yield dbase

@pytest.fixture(scope="module")
def uid():
    user = UserManager()
    uid = user.get_user_id(mail='admin@fullon')
    yield uid


def test_get_cat_exchange(dbase):
    exchanges = dbase.get_cat_exchanges(page=1, page_size=10)
    assert isinstance(exchanges, list)
    exchanges = dbase.get_cat_exchanges(all=True)
    assert isinstance(exchanges, list)
