from __future__ import unicode_literals, print_function
from libs.caches.symbol_cache import Cache
import pytest

exchange_list = ['kraken']


@pytest.fixture(scope="module")
def store():
    return Cache(reset=True)


@pytest.mark.order(1)
@pytest.mark.parametrize("exchange_name", exchange_list)
def test_get_symbols(store, exchange_name):
    res = store.get_symbols(exchange=exchange_name)
    assert isinstance(res, list)
    assert len(res) > 1
