from __future__ import unicode_literals, print_function
import sys
from libs.models.bot_model import Database
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


@pytest.fixture(scope="module")
def bot_test_id():
    yield 2


@pytest.mark.order(1)
def test_get_base_str_params(dbase, bot_test_id):
    strat = dbase.get_base_str_params(bot_id=bot_test_id)
    if strat:
        assert 'take_profit' in dir(strat)
    else:
        assert strat is None


@pytest.mark.order(2)
def test_get_str_params(dbase, bot_test_id):
    strat = dbase.get_str_params(bot_id=bot_test_id)
    strat = dict(strat)
    assert isinstance(strat, dict)


@pytest.mark.order(3)
def test_update_base_str_params(dbase, bot_test_id):
    strat = dbase.get_bot_params(bot_id=bot_test_id)
    _ = strat.pop('dry_run', None)
    _ = strat.pop('active', None)
    _ = strat.pop('uid', None)
    bot_id = strat.pop('bot_id')
    result = dbase.edit_base_strat_params(bot_id=bot_id, params=strat)
    assert result is True


@pytest.mark.order(4)
def test_update_str_params(dbase, bot_test_id):
    strat = dbase.get_str_params(bot_id=bot_test_id)
    strat = dict(strat)
    result = dbase.edit_strat_params(bot_id=bot_test_id, params=strat)
    assert result is True


@pytest.mark.order(5)
def test_get_cat_strategies(dbase):
    strats = dbase.get_cat_strategies(page=1, page_size=2, all=False)
    assert isinstance(strats, list)
    assert len(strats) > 1
    strats = dbase.get_cat_strategies(page=1, page_size=2, all=True)
    assert isinstance(strats, list)
    assert len(strats) > 1


@pytest.mark.order(6)
def test_get_user_strategies(dbase, uid):
    strats = dbase.get_user_strategies(uid=uid)
    assert isinstance(strats, list)
    assert len(strats) > 0


@pytest.mark.order(7)
def test_install_strategy(dbase):
    strname = 'pytest'
    base_params = {'take_profit': 2.5, 'trailing_stop': None, 'timeout': 30, 'stop_loss': 1.5, 'pre_load_bars': 30, 'feeds': 2} 
    params = {'rsi_period': 14, 'rsi_upper': 63, 'rsi_lower': 36}
    res = dbase.install_strategy(name=strname, base_params=base_params, params=params)
    assert res is None


@pytest.mark.order(8)
def test_get_strategies_bot(dbase):
    cat_str_name = "trading101"
    res = dbase.get_strategies_bots(cat_str_name=cat_str_name)
    assert isinstance(res[0].name, str)


@pytest.mark.order(9)
def test_delete_cat_strategy(dbase):
    cat_str_name = "pytest"
    res = dbase.del_cat_strategy(cat_str_name=cat_str_name)
    assert res is True
