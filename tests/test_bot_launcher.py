import pytest
from libs.bot_launcher import Launcher


@pytest.fixture(scope="module")
def launcher():
    launcher = Launcher()
    yield launcher


def test_start_bot(launcher):
    res = launcher.start(1)
    assert res is True


def test_get_list(launcher):
    res = launcher.get_bots()
    assert isinstance(res, list)
    assert len(res) > 0


def test_ping(launcher):
    res = launcher.ping(1)
    assert res is True


def test_stop(launcher):
    res = launcher.stop(1)
    assert res is True
