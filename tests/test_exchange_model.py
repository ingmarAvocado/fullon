from __future__ import unicode_literals, print_function
import sys
from libs.models.exchange_model import Database
from run.user_manager import UserManager
import pytest

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
