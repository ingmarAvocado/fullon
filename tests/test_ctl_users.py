import pytest
from prompt_toolkit.input import create_pipe_input
from libs.ctl.ctl_users_lib import CTL
from unittest.mock import patch


# Mock function for PromptSession.prompt
def mock_prompt(prompt, **kwargs):
    # Map prompt strings to responses
    prompt_responses = {
        "(User Feed) Pick user - press [tab] > ": "admin@fullon",
        "(User Feed) Pick exchange - press [tab] > ": "kraken1",
    }
    response = prompt_responses.get(prompt, "")
    return response


@pytest.fixture
def ctl(server):
    if server:
        _ctl = CTL()
        yield _ctl
        del _ctl


@pytest.mark.order(1)
@patch('libs.ctl.ctl_users_lib.PromptSession', autospec=True)
def test_select_user_exchange(mock_prompt_session, ctl):
    # Mock the prompt function
    mock_prompt_session.return_value.prompt.side_effect = mock_prompt

    # Use create_pipe_input and DummyOutput
    with create_pipe_input() as inp:
        inp.send_text("admin@fullon\n")
        uid = ctl.select_user()

    # Check if uid is a valid int
    assert isinstance(uid, int)

    # Use create_pipe_input again for the second test
    with create_pipe_input() as inp:
        inp.send_text("kraken1\n")
        result = ctl.select_user_exchange(uid=uid)

    assert isinstance(result, int)
