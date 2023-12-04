import pytest
from prompt_toolkit.input import create_pipe_input
from libs.ctl.ctl_symbols_lib import CTL
from unittest.mock import patch

# Mock function for PromptSession.prompt


def mock_prompt(prompt, **kwargs):
    # Map prompt strings to responses
    prompt_responses = {
        "(Symbols Shell Feed) Pick Feed Exchange - press [tab] > ": "kraken",
        "(Symbols Shell Feed) Pick Symbol > ": "BTC/USD",
        "(Symbols Shell Feed) Pick feed 0 period > ": "Ticks",
        "(Symbols Shell Feed) Pick feed 0 compression > ": "1",
        "(Symbols Shell Feed) Pick feed 1 period > ": "Minutes",
        "(Symbols Shell Feed) Pick feed 1 compression > ": "60",
        "(Symbols Shell Feed) Pick Exchange - press [tab] > ": "kraken",
        "(Symbols Shell Feed) Pick Symbol - press [tab] > ": "WAVES/ETH",
        "(Symbols Shell Feed) Pick Symbol - Backload data from (days) > ": 10,
        "(Symbols Shell Feed) are you sure you want delete type 'yes' > ": "yes"
        }
    response = prompt_responses.get(prompt, "")
    return response


@pytest.fixture
def ctl(server):
    if server:
        _ctl = CTL()
        yield _ctl
        del _ctl


@patch('libs.ctl.ctl_symbols_lib.PromptSession', autospec=True)
def test_select_symbol(mock_prompt_session, ctl):
    # Mock the prompt function
    mock_prompt_session.return_value.prompt.side_effect = mock_prompt

    # Use create_pipe_input and DummyOutput
    with create_pipe_input() as inp:
        inp.send_text("kraken\n")
        inp.send_text("BTC/USD\n")
        result = ctl.select_symbol()
    assert result[1] is "BTC/USD"  # Check the expected result


@patch('libs.ctl.ctl_symbols_lib.PromptSession', autospec=True)
def test_select_feed(mock_prompt_session, ctl):
    mock_prompt_session.return_value.prompt.side_effect = mock_prompt
    with create_pipe_input() as inp:
        inp.send_text("Ticks\n")
        inp.send_text("Minutes\n")
        inp.send_text("60\n")
        results = ctl.build_feeds(feeds=2)
    assert results[0]['period'] is 'Ticks'


@patch('libs.ctl.ctl_symbols_lib.PromptSession', autospec=True)
def test_add_symbol(mock_prompt_session, ctl):
    mock_prompt_session.return_value.prompt.side_effect = mock_prompt
    with create_pipe_input() as inp:
        inp.send_text("kraken\n")
        inp.send_text("WAVES/ETH\n")
        inp.send_text("10\n")
        num = ctl.add_symbol()
        assert isinstance(num, int)
        res = ctl.delete_symbol(num)
        assert res is True
