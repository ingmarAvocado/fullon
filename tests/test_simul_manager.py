from __future__ import unicode_literals, print_function
from libs import settings
from run.simul_manager import SimulManager
from threading import Thread, Event
import pytest


@pytest.fixture(scope="module")
def simul():
    simul = SimulManager()
    yield simul
    del simul


@pytest.mark.order(1)
def test_get_simul_bot_listz(simul):
    response = simul.get_simul_list(
        {
            'limit': '1.2,1.3,1.8',
            'timeout': '20,25,30',
            'take_profit': '4',
            'stop_loss': '2:4',
            'pred_name': 'pruebastring'})
    assert (isinstance(response, list) and 'ERROR' not in response[0])


@pytest.mark.order(2)
def test_get_simul_bot_list1(simul):
    params = {
        "limit": "1.8",
        "timeout": "25",
        "take_profit": "9",
        "stop_loss": "2:A"}
    response = simul.get_simul_list(params)
    assert (isinstance(response, list) and 'ERROR' in response[0])


@pytest.mark.order(3)
def test_get_simul_bot_list2(simul):
    params = {
        "limit": "9:10)",
        "timeout": "25,27,A",
        "take_profit": "9:11",
        "stop_loss": "4"}
    response = simul.get_simul_list(params)
    # print("2",response)
    assert (isinstance(response, list) and 'ERROR' in response[0])


@pytest.mark.order(4)
def test_get_simul_bot_list3(simul):
    params = {
        "limit": "1-3",
        "timeout": "25,3",
        "take_profit": "9:2",
        "stop_loss": "4"}
    response = simul.get_simul_list(params)
    # print("3",response)
    assert (isinstance(response, list) and 'ERROR' in response[0])


@pytest.mark.order(5)
def test_get_simul_bot_list4(simul):
    params = {"timeout": "A,3", "take_profit": "9:2", "stop_loss": "4"}
    response = simul.get_simul_list(params)
    # print("4",response)
    assert (isinstance(response, list) and 'ERROR' in response[0])


@pytest.mark.order(6)
def test_get_simul_bot_list5(simul):
    params = {"limit": "1-3", "take_profit": "9:2", "stop_loss": "4"}
    response = simul.get_simul_list(params)
    # print("5",response)
    assert (isinstance(response, list) and 'ERROR' in response[0])


@pytest.mark.order(7)
def test_get_simul_bot_list6(simul):
    params = {"limit": "1-3", "take_profit": "9:A", "stop_loss": "4"}
    response = simul.get_simul_list(params)
    # print("6",response)
    assert (isinstance(response, list) and 'ERROR' in response[0])
