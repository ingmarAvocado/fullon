import pytest
from libs import exchange, database
from typing import Dict
from fullon.run.user_manager import UserManager


@pytest.fixture(scope="module")
def exchanges():
    user = UserManager()
    uid = user.get_user_id(mail='admin@fullon')
    with database.Database() as dbase:
        exch = dbase.get_exchange(user_id=uid)
    yield exch


def test_exchange_operations(exchanges):
    for exch in exchanges:
        exch1 = exchange.Exchange(exchange=exch.cat_name, params=exch)
        assert exch1.dry_run is False
        assert len(exch1.get_markets()) > 0
        del exch1

        exch2 = exchange.Exchange(exchange=exch.cat_name, params=exch)
        assert exch2.dry_run is False
        assert len(exch2.get_markets()) > 0
        del exch2

        exch3 = exchange.Exchange(exchange=exch.cat_name, params={})
        assert exch3.dry_run is False
        assert len(exch3.get_markets()) > 0
        del exch3
