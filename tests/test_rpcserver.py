from __future__ import unicode_literals, print_function
from libs import settings
from run import rpcdaemon_manager as rpc
from run.user_manager import UserManager
from run.crawler_manager import CrawlerManager
import psutil
import pytest
from time import sleep
import xmlrpc.client
import json


@pytest.fixture(scope="module")
def client(rpc_client):
    yield rpc_client

@pytest.fixture(scope="module")
def uid():
    user = UserManager()
    uid = user.get_user_id(mail='admin@fullon')
    yield uid



@pytest.mark.order(1)
def test_bots_list(client):
    response = client.bots('list', {'page': 1, 'page_size': 10})
    assert len(response) > 0
    assert response[0]['bot_id'] == 1
    response = client.bots('list', {'pagee': 1, 'sdfs': 10})
    assert 'Missing' in response


@pytest.mark.order(2)
def test_bots_live_list(client):
    response = client.bots('live_list')
    assert isinstance(response, dict)
    response = client.bots('live_lists')
    assert 'Error' in response


@pytest.mark.order(3)
def test_bots_detail(client):
    response = client.bots('details', {'bot_id': 1})
    assert isinstance(response, str)
    response = json.loads(response)
    assert isinstance(response, dict)
    assert len(response) > 0
    assert response['1']['bot_id'] == 1
    response = client.bots('details')
    assert 'Error' in response


@pytest.mark.order(4)
def test_start_tickers():
    response = rpc.start_tickers()
    assert ("Ticker" in response)
    sleep(2)
    response = rpc.stop_component('tick')
    assert "stopped" in response


@pytest.mark.order(5)
def test_start_accounts():
    response = rpc.start_accounts()
    sleep(2)
    response = rpc.stop_component('account')
    assert "stopped" in response


@pytest.mark.order(6)
def test_start_ohlcv():
    response = rpc.start_ohlcv()
    assert ("OHLCV" in response)
    response = rpc.stop_component('ohlcv')
    assert "stopped" in response


@pytest.mark.order(7)
def test_start_bot_status():
    response = rpc.start_bot_status()
    assert ('Bot status' in response)
    response = rpc.stop_component('bot_status')
    assert "stopped" in response


@pytest.mark.order(8)
def test_daemon_startup():
    assert (rpc.daemon_startup())


@pytest.mark.order(9)
def test_stop_full():
    response = rpc.stop_full()
    assert ("Full services stopped" in response)


@pytest.mark.order(10)
def test_stop_component():
    response = rpc.stop_component("tick")
    assert ("stopped" in response)

'''
@pytest.mark.order(11)
def test_start_services():
    response = rpc.start_services()
    rpc.stop_services()
    assert ("Services" in response)


@pytest.mark.order(12)
def test_stop_services():
    response = rpc.stop_services()
    assert ("Services" in response)
'''

@pytest.mark.order(13)
def test_list_symbols(client):
    args = {'page': 1, 'page_size': 2}
    response = client.symbols('list', args)
    assert isinstance(response, list)
    assert len(response) > 1


@pytest.mark.order(14)
def test_strategies_list(client):
    args = {'page': 1, 'page_size': 2}
    response = client.strategies('list', args)
    assert isinstance(response, list)
    assert len(response) > 1


@pytest.mark.order(15)
def test_strategies_user_list(client, uid):
    response = client.strategies('user_list', {'uid': uid})
    assert isinstance(response, list)
    assert len(response) > 1


@pytest.mark.order(16)
def test_strategies_bot(client):
    response = client.strategies('get_bots', {'cat_str_name': 'trading101'})
    assert len(response) > 0


@pytest.mark.order(17)
def test_del_cat_str(client):
    response = client.strategies('del_cat_str', {'cat_str_name': 'pytest'})
    assert response is False


@pytest.mark.order(18)
def test_reload_str(client):
    response = client.strategies('reload')
    assert isinstance(response, bool)


@pytest.mark.order(19)
def test_list_users_exchange(client):
    args = {'page': 1, 'page_size': 2}
    response = client.users('list', args)
    assert isinstance(response, list)
    assert len(response) > 0
    uid = response[0]['uid']
    response = client.users('exchange', {'uid': uid})
    assert isinstance(response, list)
    assert len(response) > 0


@pytest.mark.order(20)
def test_exchanges_list(client):
    response = client.exchanges('list')
    assert (isinstance(response, list))


@pytest.mark.order(21)
def test_get_system_status(client):
    response = client.get_system_status()
    assert (isinstance(response, dict))


@pytest.mark.order(22)
def test_btc_ticker(client):
    response = client.tickers('btc')


@pytest.mark.order(23)
def test_get_top(client):
    response = client.get_top()
    print(response)


'''
@pytest.mark.order(24)
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
'''

@pytest.mark.order(25)
def test_delete_symbol(client):
    res = client.symbols('delete', {'symbol_id': '9999999'})
    assert res is False


@pytest.mark.order(26)
def test_tickers_list(client):
    res = client.tickers('list')


@pytest.mark.order(27)
def test_crawler_flow(client):
    crawler = CrawlerManager()
    crawler.add_site(site='anothernetwork4')
    profile = {"fid": 0,
               "uid": 1,
               "site": "anothernetwork4",
               "account": "Snowden",
               "ranking": 2,
               "contra": False}
    fid = client.crawler('add', profile)
    assert isinstance(fid, int)
    assert fid > 0
    res = client.crawler('profiles', {'sieve': 'anothernetwork4', 'page': 1, 'page_size': 1})
    assert 'Error' not in str(res)
    res = client.crawler('del', {"fid": fid})
    assert res is True
    crawler.del_site(site='anothernetwork4')

'''
@pytest.mark.order(28)
def test_services(client):
    res = client.services('tickers', 'start')
    assert 'Launched' in res
    res = client.services('ohlcv', 'start')
    assert 'started' in res
    res = client.services('accounts', 'start')
    assert 'launched' in res
    res = client.services('services', 'stop')
'''