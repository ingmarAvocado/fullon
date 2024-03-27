from __future__ import unicode_literals, print_function
import sys
from libs.models.bot_model import Database
import pytest

@pytest.fixture(scope="module")
def dbase():
    with Database() as dbase:
        yield dbase


@pytest.mark.order(1)
def test_users_list(dbase):
    users = dbase.get_user_list(page=1, page_size=2, all=False)
    assert isinstance(users, list)
    assert len(users) > 0
    users = dbase.get_user_list(page=1, page_size=2, all=True)
    assert isinstance(users, list)
    assert len(users) > 0
