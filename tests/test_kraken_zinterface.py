from fullon.exchanges.kraken.interface import Interface
from fullon.run.user_manager import UserManager
import pytest



@pytest.fixture(scope="module")
def exchange_struct(db_session):
    user = UserManager()
    uid = user.get_user_id(mail='admin@fullon')
    exch = db_session.get_exchange(user_id=uid)[0]
    iface = Interface('kraken', params=exch)
    yield iface
    iface.stop()
    del iface


@pytest.mark.order(1)
def test__reconnect_ws_subscriptions(exchange_struct):
    return


@pytest.mark.order(2)
def test_generate_auth_token(exchange_struct):
    return


@pytest.mark.order(3)
def test_replace_symbol(exchange_struct):
    symbol = exchange_struct.replace_symbol('BTC/USD')
    assert symbol == 'XXBTZUSD'
    symbol = exchange_struct.replace_symbol('AGLD/USD')
    assert symbol == 'AGLDUSD'
    symbol = exchange_struct.replace_symbol('AGLD/MYCOIN')
    assert symbol is None


@pytest.mark.order(4)
def test_replace_symbols(exchange_struct):
    return


@pytest.mark.order(5)
def test_set_pairs(exchange_struct):
    return


@pytest.mark.order(6)
def test_set_currencies(exchange_struct):
    return


@pytest.mark.order(7)
def test_match_currencies(exchange_struct):
    return
