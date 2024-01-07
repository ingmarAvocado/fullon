from __future__ import unicode_literals, print_function
from libs import settings
from run import rpcdaemon_manager as rpc
from run.user_manager import UserManager
import psutil
import pytest
from time import sleep
import xmlrpc.client
import time


@pytest.fixture(scope="module")
def client(server):
    client = xmlrpc.client.ServerProxy(
        f"http://{settings.XMLRPC_HOST}:{settings.XMLRPC_PORT}")
    yield client
    del client

@pytest.fixture(scope="module")
def uid():
    user = UserManager()
    uid = user.get_user_id(mail='admin@fullon')
    yield uid


def test_bots_list(client):
    response = client.bots('list', {'page': 1, 'page_size': 10})
    assert len(response) > 0
    assert response[0]['bot_id'] == 1
    response = client.bots('list', {'pagee': 1, 'sdfs': 10})
    assert 'Missing' in response


def test_bots_live_list(client):
    response = client.bots('live_list')
    assert isinstance(response, dict)
    response = client.bots('live_lists')
    assert 'Error' in response


def test_bots_detail(client):
    response = client.bots('details', {'bot_id': 1})
    assert isinstance(response, dict)
    assert len(response) > 0
    assert response['bot_id'] == 1
    response = client.bots('details')
    assert 'Error' in response


def test_start_tickers():
    response = rpc.start_tickers()
    assert ("Ticker" in response)
    sleep(2)
    response = rpc.stop_component('tick')
    assert "stopped" in response


def test_start_accounts():
    response = rpc.start_accounts()
    sleep(2)
    response = rpc.stop_component('account')
    assert "stopped" in response


def test_start_ohlcv():
    response = rpc.start_ohlcv()
    assert ("OHLCV" in response)
    response = rpc.stop_component('ohlcv')
    assert "stopped" in response


def test_start_bot_status():
    response = rpc.start_bot_status()
    assert ('Bot status' in response)
    response = rpc.stop_component('bot_status')
    assert "stopped" in response


def test_daemon_startup():
    assert (rpc.daemon_startup())


def test_stop_full():
    response = rpc.stop_full()
    assert ("Full services stopped" in response)


def test_stop_component():
    response = rpc.stop_component("tick")
    assert ("stopped" in response)


def test_start_services():
    response = rpc.start_services()
    rpc.stop_services()
    assert ("Services" in response)


def test_stop_services():
    response = rpc.stop_services()
    assert ("Services" in response)


def test_list_symbols(client):
    args = {'page': 1, 'page_size': 2}
    response = client.symbols('list', args)
    assert isinstance(response, list)
    assert len(response) > 1


def test_strategies_list(client):
    args = {'page': 1, 'page_size': 2}
    response = client.strategies('list', args)
    assert isinstance(response, list)
    assert len(response) > 1


def test_strategies_user_list(client, uid):
    response = client.strategies('user_list', {'uid': uid})
    assert isinstance(response, list)
    assert len(response) > 1


def test_strategies_bot(client):
    response = client.strategies('get_bots', {'cat_str_name': 'trading101'})
    assert len(response) > 0


def test_del_cat_str(client):
    response = client.strategies('del_cat_str', {'cat_str_name': 'pytest'})
    assert response is False


def test_reload_str(client):
    response = client.strategies('reload')
    assert isinstance(response, bool)


def test_list_users_exchange(client):
    args = {'page': 1, 'page_size': 2}
    response = client.users('list', args)
    assert isinstance(response, list)
    assert len(response) > 0
    uid = response[0]['uid']
    response = client.users('exchange', {'uid': uid})
    assert isinstance(response, list)
    assert len(response) > 0


def test_exchanges_list(client):
    response = client.exchanges('list')
    assert (isinstance(response, list))


def test_get_system_status(client):
    response = client.get_system_status()
    assert (isinstance(response, dict))


def test_btc_ticker(client):
    response = client.tickers('btc')


def test_get_top(client):
    response = client.get_top()
    print(response)


def test_check_services():
    response = rpc.check_services()
    assert response is False
    rpc.start_services()
    response = rpc.check_services()
    assert response is True
    rpc.stop_services()
    response = rpc.check_services()
    assert response is False
    rpc.start_tickers()
    response = rpc.check_services()
    assert response is False
    rpc.stop_services()


def test_delete_symbol(client):
    res = client.symbols('delete', {'symbol_id': '9999999'})
    assert res is False


def test_tickers_list(client):
    res = client.tickers('list')
    print(res)


def test_services(client):
    res = client.services('tickers', 'start')
    assert 'Launched' in res
    res = client.services('ohlcv', 'start')
    assert 'started' in res
    res = client.services('accounts', 'start')
    assert 'launched' in res
    res = client.services('services', 'stop')
