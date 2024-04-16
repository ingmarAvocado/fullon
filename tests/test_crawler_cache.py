from __future__ import unicode_literals, print_function
from libs.caches.crawler_cache import Cache
from libs.models.crawler_model import Database
from libs.structs.crawler_struct import CrawlerStruct
import pytest


@pytest.fixture(scope="module")
def profile():
    return CrawlerStruct(fid=0, uid=1, site='anothernetwork', account='Snowden', ranking=2, contra=False, expertise='hacking')


@pytest.mark.order(1)
def test_get_crawl_list(store, dbase, profile):
    pass
