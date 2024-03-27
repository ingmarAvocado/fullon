from __future__ import unicode_literals, print_function
from run import system_manager
import pytest



@pytest.fixture
def process_manager():
    pmanager = system_manager.ProcessManager()
    yield pmanager
    del pmanager


@pytest.mark.order(1)
def test_get_top(process_manager):
    res = process_manager.get_top()
    print(res)
