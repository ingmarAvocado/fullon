#!/usr/bin/python3
"""
This is a command line tool for managing persea
"""
import pytest
from libs.simulator_prompts import Prompts


@pytest.fixture(scope="module")
def prompts():
    prompts = Prompts()
    numbots = prompts._get_bot_dict()
    prompts.BOT = numbots[1]
    yield prompts
    del prompts


@pytest.mark.order(1)
def test__get_str_params(prompts):
    #now i need to set the bot first
    p = prompts._get_str_params()
    assert 'stop_loss' in p


@pytest.mark.order(2)
def test__str_get_feeds(prompts):
    #now i need to set the bot first
    p = prompts._get_feeds()
    assert (isinstance(p, dict))
