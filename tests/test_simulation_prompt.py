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
def prompts(bot_id):
    prompts = Prompts()
    numbots = prompts._get_bot_dict()
    prompts.BOT = numbots[1]
    yield prompts
    del prompts


@pytest.mark.order(1)
def test__get_str_params(prompts):
    strats = prompts._get_str_params()
    for strat in strats:
        assert strat.str_id > 0

@pytest.mark.order(2)
def test__str_get_feeds(prompts):
    #now i need to set the bot first
    feeds = prompts._get_feeds()
    print(feeds)
    #assert (isinstance(p, dict))
