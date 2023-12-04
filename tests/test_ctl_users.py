import pytest
from prompt_toolkit.input import create_pipe_input
from libs.ctl.ctl_users_lib import CTL
from unittest.mock import patch
import uuid


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


@patch('libs.ctl.ctl_users_lib.PromptSession', autospec=True)
def test_select_user_exchange(mock_prompt_session, ctl):
    # Mock the prompt function
    mock_prompt_session.return_value.prompt.side_effect = mock_prompt

    # Use create_pipe_input and DummyOutput
    with create_pipe_input() as inp:
        inp.send_text("admin@fullon\n")
        uid = ctl.select_user()

    # Check if uid is a valid UUID
    assert isinstance(uid, str)
    assert is_valid_uuid(uid)  # Helper function to validate UUID

    # Use create_pipe_input again for the second test
    with create_pipe_input() as inp:
        inp.send_text("kraken1\n")
        result = ctl.select_user_exchange(uid=uid)

    # Check if result is a valid UUID
    assert isinstance(result, str)
    assert is_valid_uuid(result)  # Helper function to validate UUID


# Helper function to check if a string is a valid UUID
def is_valid_uuid(uid_str):
    try:
        uuid.UUID(uid_str)
        return True
    except ValueError:
        return False

