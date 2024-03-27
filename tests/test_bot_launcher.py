import pytest
from libs.bot_launcher import Launcher


@pytest.fixture(scope="module")
def launcher():
    launcher = Launcher()
    yield launcher


@pytest.mark.order(1)
def test_start_bot(launcher):
    res = launcher.start(1, no_check=True)
    assert res is True


@pytest.mark.order(2)
def test_get_list(launcher):
    res = launcher.get_bots()
    assert isinstance(res, list)
    assert len(res) > 0


@pytest.mark.order(3)
def test_ping(launcher):
    res = launcher.ping(1)
    assert res is True


@pytest.mark.order(4)
def test_stop(launcher):
    res = launcher.stop(1)
    assert res is True
