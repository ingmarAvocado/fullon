from __future__ import unicode_literals, print_function
from libs.messaging import x
import pytest


@pytest.fixture
def messenger():
    m =  x.Messenger()
    yield m
    del m



@pytest.mark.order(1)
def test_try_loading(messenger):
    _id = messenger.post(post="Automated testing tweet")
    assert isinstance(int(_id), int)
    assert messenger.delete_post(post_id=_id)
