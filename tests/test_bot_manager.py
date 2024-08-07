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
    assert bot_list[0]['bot_id'] == 1


@pytest.mark.order(2)
def test_bot_details(bot_manager):
    details = bot_manager.bot_details(bot_id=1)
    for key, value in details.items():
        assert key >= 1
        assert value['bot_id'] == 1
        for feed, attrs in value['feeds'].items():
            assert int(feed) >= 0
            assert attrs['str_id'] >= 1
    details = bot_manager.bot_details(bot_id=3)
    for key, value in details.items():
        assert key >= 1
        assert value['bot_id'] == 3
        for feed, attrs in value['feeds'].items():
            assert int(feed) >= 0
            assert attrs['str_id'] >= 1
    details = bot_manager.bot_details(bot_id=10)


@pytest.mark.order(3)
def test_edit_bot_strat(bot_manager, bot_id):
    bot = bot_manager.bot_details(bot_id=bot_id)
    str_id = next(iter(bot))
    assert bot[str_id]['bot_id'] == bot_id
    _strat = {"bot_id": bot_id,
              "str_id": str_id,
              "size": None,
              "size_pct": 10,
              "size_currency": "USD",
              "take_profit": 14,
              "trailing_stop": 13,
              "timeout": None
              }
    extended = {
          'rsi': "14",  #
    }
    _strat['extended'] = extended
    res = bot_manager.edit_bot_strat(bot_id=bot_id, strat=_strat)
    assert res is True


@pytest.mark.order(4)
def test_start_bot(bot_manager, bot_id):
    bot = bot_manager.start(bot_id=bot_id)
    assert bot is True


@pytest.mark.order(5)
def test_start_bot2(bot_manager):
    bot = bot_manager.start(bot_id=-1)
    assert bot is False


@pytest.mark.order(6)
def test_stop_bot2(bot_manager, bot_id):
    bot = bot_manager.stop(bot_id=bot_id)
    assert bot is True

@pytest.mark.order(7)
def test_edit_bot2(bot_manager):
    bot_details = {
        '3': {
            'bot_id': 3,
            'dry_run': True,
            'active': False,
            'uid': 1,
            'str_id': 3,
            'strategy': 'trading101',
            'take_profit': None,
            'stop_loss': None,
            'trailing_stop': None,
            'timeout': None,
            'leverage': 2.0,
            'size_pct': 10.0,
            'size': None,
            'size_currency': 'USD',
            'pre_load_bars': 100,
            'feeds': {
                '0': {
                    'str_id': 3,
                    'symbol': 'BTC/USD',
                    'exchange': 'kraken',
                    'compression': 1,
                    'period': 'Ticks',
                    'feed_id': 7
                },
                '2': {
                    'str_id': 3,
                    'symbol': 'BTC/USD',
                    'exchange': 'kraken',
                    'compression': 120,
                    'period': 'Minutes',
                    'feed_id': 8
                }
            },
            'extended': {
                'str_id': 3,
                'sma1': '45'
            }
        },
        '4': {
            'bot_id': 3,
            'dry_run': True,
            'active': False,
            'uid': 1,
            'str_id': 4,
            'strategy': 'trading101',
            'take_profit': None,
            'stop_loss': None,
            'trailing_stop': None,
            'timeout': None,
            'leverage': 5.0,
            'size_pct': 15.0,
            'size': None,
            'size_currency': 'USD',
            'pre_load_bars': 100,
            'feeds': {
                '1': {
                    'str_id': 4,
                    'symbol': 'ETH/USD',
                    'exchange': 'kraken',
                    'compression': 1,
                    'period': 'Ticks',
                    'feed_id': 9
                },
                '3': {
                    'str_id': 4,
                    'symbol': 'ETH/USD',
                    'exchange': 'kraken',
                    'compression': 10,
                    'period': 'Minutes',
                    'feed_id': 10
                }
            },
            'extended': {
                'str_id': 4,
                'sma1': '45'
            }
        }
    }
    res = bot_manager.edit(bot_id=3, strats=bot_details)
    assert res is True

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
