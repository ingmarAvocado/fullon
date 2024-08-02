from fullon.exchanges.bitmex.interface import Interface
from fullon.run.user_manager import UserManager
import pytest


'''
@pytest.fixture(scope="module")
def exchange_instance(dbase):
    user = UserManager()
    uid = user.get_user_id(mail='admin@fullon')
    exch = dbase.get_exchange(user_id=uid)[0]
    iface = Interface('bitmex', params=exch)
    yield iface
    iface.stop()
    del iface


@pytest.mark.order(1)
def test__reconnect_ws_subscriptions(exchange_instance):
    return


@pytest.mark.order(2)
def test_generate_auth_token(exchange_instance):
    return


@pytest.mark.order(3)
def test_replace_symbol(exchange_instance):
    symbol = exchange_instance.replace_symbol('BTC/USD')
    assert symbol == 'XBTUSD'
'''