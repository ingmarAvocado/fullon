from __future__ import unicode_literals, print_function
import sys
from libs.models.bot_model import Database
from run.user_manager import UserManager
from libs.structs.exchange_struct import ExchangeStruct
import pytest


@pytest.mark.order(4)
def test_get_base_str_params(dbase, bot_id, cat_str_name):
    strats = dbase.get_base_str_params(bot_id=bot_id)
    for strat in strats:
        assert strat.cat_name == cat_str_name


@pytest.mark.order(5)
def test_get_str_params(dbase, bot_id, str_id1):
    params = dbase.get_str_params(bot_id=bot_id)
    param = params[0]
    assert param['str_id'] == str_id1


@pytest.mark.order(6)
def test_update_base_str_params(dbase, bot_id):
    strat = dbase.get_bot_params(bot_id=bot_id)
    _ = strat[0].pop('dry_run', None)
    _ = strat[0].pop('active', None)
    _ = strat[0].pop('uid', None)
    _ = strat[0].pop('bot_id', None)
    _ = strat[0].pop('strategy', None)
    str_id = strat[0].pop('str_id', None)
    strat[0]['take_profit'] = 10
    result = dbase.edit_base_strat_params(str_id=str_id, params=strat[0])
    assert result is True
    strats = dbase.get_base_str_params(bot_id=bot_id)
    for strat in strats:
        if strat.str_id == str_id:
            assert float(strat.take_profit) == 10


@pytest.mark.order(7)
def test_get_cat_strategies(dbase):
    strats = dbase.get_cat_strategies(page=1, page_size=2, all=False)
    assert isinstance(strats, list)
    assert len(strats) >= 1
    strats = dbase.get_cat_strategies(page=1, page_size=2, all=True)
    assert isinstance(strats, list)
    assert len(strats) >= 1


@pytest.mark.order(8)
def test_get_cat_strategies_params(dbase, cat_str_id):
    strats = dbase.get_cat_strategies_params(cat_str_id=cat_str_id)
    assert isinstance(strats, list)
    assert len(strats) >= 1
    strats = dbase.get_cat_strategies_params(cat_str_id=cat_str_id)
    assert isinstance(strats, list)
    assert len(strats) >= 1


@pytest.mark.order(9)
def test_edit_str_params(dbase, bot_id):
    params = dbase.get_str_params(bot_id=bot_id)
    for param in params:
        str_id = param.pop('str_id')
        param['rsi_period'] = 100
        result = dbase.edit_strat_params(str_id=str_id, params=param)
        assert result is True
    strats = dbase.get_str_params(bot_id=bot_id)
    for strat in strats:
        assert int(strat['rsi_period']) == 100


@pytest.mark.order(10)
def test_get_bots_strategies(dbase, bot_id, cat_str_name):
    bots = dbase.get_bots_strategies(cat_str_name=cat_str_name)
    exists = False
    for bot in bots:
        if bot.bot_id == bot_id:
            exists = True
    assert exists is True


@pytest.mark.order(11)
def test_get_user_strategies(dbase, uid):
    strats = dbase.get_user_strategies(uid=uid)
    strat_match = False
    for strat in strats:
        if strat.uid == uid:
            if strat.bot_id == 1:
                strat_match = True
    assert strat_match is True


@pytest.mark.order(12)
def test_get_cat_str_id(dbase, cat_str_name, cat_str_id):
    _cat_str_id = dbase.get_cat_str_id(name=cat_str_name)
    assert cat_str_id == _cat_str_id


@pytest.mark.order(13)
def test_get_cat_strategy(dbase, cat_str_id):
    strat = dbase.get_cat_strategy(cat_str_id=cat_str_id)
    assert strat.cat_str_id == cat_str_id
