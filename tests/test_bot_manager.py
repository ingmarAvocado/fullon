import pytest
from run.bot_manager import BotManager
import time


@pytest.fixture(scope="module")
def bot_manager():
    bm = BotManager()
    yield bm
    del bm


@pytest.mark.order(1)
def test_bots_list(bot_manager):
    bot_list = bot_manager.bots_list(10, 1)
    assert isinstance(bot_list, list) is True
    assert len(bot_list) > 1


@pytest.mark.order(2)
def test_bot_details(bot_manager):
    details = bot_manager.bot_details(bot_id=1)
    assert len(details) > 4
    assert isinstance(details['feeds']['0'], dict)


@pytest.mark.order(3)
def test_edit_bot(bot_manager):
    bot = bot_manager.bot_details(bot_id=1)
    res = bot_manager.edit(bot=bot)


@pytest.mark.order(4)
def test_start_bot(bot_manager):
    bot = bot_manager.start_bot(bot_id=1)
    assert bot is True


@pytest.mark.order(5)
def test_start_bot2(bot_manager):
    bot = bot_manager.start_bot(bot_id=1)
    assert bot is False


@pytest.mark.order(6)
def test_stop_bot2(bot_manager):
    bot = bot_manager.stop_bot(bot_id=1)
    assert bot is True

'''
def test_edit_bot(bot_manager):
    # Add code to create a bot and edit it using bot_manager.edit(bot)



def test_dry_delete(bot_manager):
    # Add code to delete dry trades for a bot using bot_manager.dry_delete(bot_id)

def test_launch_simul(bot_manager):
    # Add code to launch a simulation for a bot using bot_manager.launch_simul()

def test_run_bot_loop(bot_manager):
    # Add code to run bot loop using bot_manager.run_bot_loop()

def test_relaunch_dead_threads(bot_manager):
    # Add code to test relaunch_dead_threads() method
'''