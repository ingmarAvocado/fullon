from __future__ import unicode_literals, print_function
import pytest


@pytest.mark.order(1)
def test_update_trade_status(store):
    res = store.update_trade_status(key="test1")
    res = store.update_trade_status(key="test2")
    assert res is True


@pytest.mark.order(2)
def test_get_trade_status(store):
    res = store.get_trade_status(key="test1")
    assert isinstance(res, float)


@pytest.mark.order(3)
def test_get_trade_status_keys(store):
    res = store.get_trade_status_keys()
    assert len(res) > 1

@pytest.mark.order(4)
def test_get_all_trade_statuses(store):
    res = store.get_all_trade_statuses()
    assert len(res) > 1
