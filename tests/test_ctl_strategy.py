from libs.ctl.ctl_strategies_lib import CTL
from run.user_manager import UserManager
from prompt_toolkit.input import create_pipe_input
from unittest.mock import patch
import pytest


# Mock function for PromptSession.prompt
def mock_prompt(prompt, **kwargs):
    # Map prompt strings to responses
    prompt_responses = {
        "(Strategies Shell) Select a strategy by name: ": "trading101",
        "(Strategies Shell) Select a strategy from catalog: ": "trading101",
        "(Strategies Shell) Select a name: ": "testname",
        "(Strategies Shell) Select a strategy to delete> ": "trading101"
    }
    response = prompt_responses.get(prompt, "")
    return response


@pytest.fixture
def ctl(server):
    if server:
        _ctl = CTL()
        yield _ctl
        del _ctl

@pytest.fixture(scope="module")
def uid():
    user = UserManager()
    uid = user.get_user_id(mail='admin@fullon')
    yield uid


@pytest.mark.order(1)
def test_get_strat_list(ctl):
    strats = ctl.get_strat_list(page=1, page_size=2)
    assert isinstance(strats, list)
    assert len(strats) > 1


@pytest.mark.order(2)
def test_reload_strats(ctl):
    res = ctl.reload_strategies()
    assert isinstance(res, bool)


@pytest.mark.order(4)
@patch('libs.ctl.ctl_strategies_lib.PromptSession', autospec=True)
def test_delete_strategy(mock_prompt_session, ctl):
    # Mock the prompt function
    strats = ['trading101']
    mock_prompt_session.return_value.prompt.side_effect = mock_prompt
    # Use create_pipe_input and DummyOutput
    with create_pipe_input() as inp:
        inp.send_text("trading101\n")
        result = ctl.del_strategy(strats=strats)
        assert result is None
