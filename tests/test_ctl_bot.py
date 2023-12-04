from libs.ctl.ctl_bot_lib import CTL
from run.bot_manager import BotManager
import pytest
from prompt_toolkit.input import create_pipe_input
from unittest.mock import patch


def mock_prompt(prompt, **kwargs):
    # Map prompt strings to responses
    prompt_responses = {
        "(Strategy Shell) Select a strategy by name: ": "trading101",
        "(Bots Shell Feed) Pick Feed Exchange - press [tab] > ": "kraken",
        "(Bots Shell Feed) Pick Symbol > ": "BTC/USD",
        "(Symbols Shell Feed) Pick feed 0 period > ": "Ticks",
        "(Symbols Shell Feed) Pick feed 0 compression > ": "1",
        "(Symbols Shell Feed) Pick feed 1 period > ": "Minutes",
        "(Symbols Shell Feed) Pick feed 1 compression > ": "60",
        "(Edit Bot Shell) Name your bot > ": "bot1test",

    }
    response = prompt_responses.get(prompt, "")
    return response

@pytest.fixture
def ctl(server):
    if server:
        _ctl = CTL()
        yield _ctl
        del _ctl


@pytest.fixture
def bot():
    _bot = BotManager()
    yield _bot
    del _bot


def test_add_bot(ctl):
    pass
    #ctl.add_bot()


def test_prep_bots(ctl, bot):
    #we would need to save in cache some bots first
    bots = bot.bots_live_list()
    _bots = ctl._prep_bots(bots=bots)
    assert isinstance(_bots, list)


def test_display_bots(ctl, bot):
    pass
    #all_feeds: dict = self.RPC.bots('all_feeds')
    #_bots = ctl._prep_bots(bots=bots)
    #ctl.display_bots(bots=_bots)


def test_change_bot_feed(ctl, bot):
    _bot = bot.bot_details(bot_id=1)
    #ctl._change_bot_feed(feed=_bot['feeds']['0'])
    #ctl.display_bots(bots=_bots)

