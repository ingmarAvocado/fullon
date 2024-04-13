#!/usr/bin/python3
"""
This is a command line tool for managing persea
"""
import pytest
from libs.simulator_prompts import Prompts
from run.user_manager import UserManager
from libs.models.bot_model import Database

cat_str_name: str = 'pytest'
rsi_upper: int = 63


@pytest.fixture(scope="module")
def str_ids(bot_id, dbase, cat_str_id):
    STRAT = {
        "cat_str_id": cat_str_id,
        "bot_id": bot_id,
        "size_pct": 10,
        "size_currency": 'USD',
        "leverage": 2}
    str_id1 = dbase.add_bot_strategy(strategy=STRAT)
    STRAT = {
        "cat_str_id": cat_str_id,
        "bot_id": bot_id,
        "size_pct": 10,
        "size_currency": 'BTC',
        "leverage": 5}
    str_id2 = dbase.add_bot_strategy(strategy=STRAT)
    yield (str_id1, str_id2)



@pytest.fixture(scope="module")
def prompts(bot_id):
    prompts = Prompts()
    numbots = prompts._get_bot_dict()
    prompts.BOT = numbots[1]
    yield prompts
    del prompts


@pytest.mark.order(1)
def test__get_str_params(prompts, str_ids):
    strats = prompts._get_str_params()
    for strat in strats:
        assert strat.str_id > 0

@pytest.mark.order(2)
def test__str_get_feeds(prompts):
    #now i need to set the bot first
    feeds = prompts._get_feeds()
    print(feeds)
    #assert (isinstance(p, dict))
