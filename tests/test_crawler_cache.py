from __future__ import unicode_literals, print_function
from libs.caches.crawler_cache import Cache
from libs.models.crawler_model import Database
from libs.structs.crawler_struct import CrawlerStruct
import pytest


@pytest.fixture(scope="module")
def store():
    return Cache(reset=True)


@pytest.fixture(scope="module")
def dbase():
    with Database() as dbase:
        yield dbase

@pytest.fixture(scope="module")
def profile():
    return CrawlerStruct(fid=0, uid=1, site='anothernetwork', account='Snowden', ranking=2, contra=False, expertise='hacking')


@pytest.mark.order(1)
def test_get_crawl_list(store, dbase, profile):
    dbase.del_crawler_site(site='anothernetwork')
    assert dbase.add_crawler_site(site='anothernetwork') is True
    fid = dbase.upsert_profile(profile=profile)
    assert fid is not None and fid > 0
    sites = store.get_crawling_list(site='anothernetwork')
    assert isinstance(sites, list)
    assert len(sites) > 0
    assert isinstance(sites[0], str)
    assert dbase.del_crawler_site(site='anothernetwork') is True
