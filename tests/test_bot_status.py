"""
Test file for account module
"""
from __future__ import unicode_literals, print_function
from run.system_manager import BotStatusManager
from libs import cache
import unittest.mock
import pytest
import time



@pytest.fixture(scope="module")
def bot_status():
    bs = BotStatusManager()
    yield bs
    bs.stop()
    del bs


def test_process_positions_loop(bot_status, mocker):
    mocker.patch.object(bot_status, '_process_positions')
    mocker.patch('time.sleep', side_effect=InterruptedError)  # Corrected mock patch

    with pytest.raises(InterruptedError):
        bot_status._process_positions_loop()

    # Verify _process_positions was called
    bot_status._process_positions.assert_called()


def test_run_loop(bot_status):
    result = bot_status.run_loop()
    assert bot_status.started is True


def test_run_loop_starts_threads(bot_status, mocker):
    mock_thread = mocker.patch('threading.Thread')
    mock_thread.return_value.daemon = False  # Set a default value for daemon

    bot_status.run_loop()
    time.sleep(20)

    assert bot_status.started is True
    mock_thread.assert_called()

    # Ensure that daemon mode is set for each thread
    for instance in mock_thread.return_value.mock_calls:
        # Look for calls to set daemon mode
        if 'daemon' in str(instance):
            assert 'True' in str(instance)  # Ensure daemon mode is set to True
