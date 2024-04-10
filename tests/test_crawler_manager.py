from __future__ import unicode_literals, print_function
import sys
import pytest
import arrow
from run.crawler_manager import CrawlerManager
from libs.structs.crawler_struct import CrawlerStruct
from libs.structs.crawler_post_struct import CrawlerPostStruct
from libs.structs.crawler_analyzer_struct import CrawlerAnalyzerStruct

SITES = ['twitter']


@pytest.fixture(scope="module")
def crawler():
    yield CrawlerManager()


@pytest.fixture(scope="module")
def profile():
    profile = {"uid": 1,
               "site": "anothernetworkz",
               "account": "Snowdens",
               "ranking": 2,
               "contra": False,
               "expertise": 'hackingz'}
    return profile


@pytest.fixture(scope="module")
def analyzer(crawler):
    # Create an analyzer to use its aid for the post
    test_analyzer = CrawlerAnalyzerStruct(title="Test Analyzerz", prompt="Test Promptz")
    aid = crawler.add_analyzer(test_analyzer)
    assert aid is not None and aid > 0
    test_analyzer.aid = aid
    yield test_analyzer
    # Clean up by deleting the analyzer after the test module finishes
    crawler.del_analyzer(aid=aid)


@pytest.mark.order(1)
def test_add_site(crawler):
    res = crawler.add_site(site='anothernetworkz')
    assert res > 0
    res = crawler.add_site(site='anothernetworkz2')
    assert res > 0


@pytest.mark.order(2)
def test_get_sites(crawler):
    sites = crawler.get_sites()
    assert 'anothernetworkz' in sites
    assert 'anothernetworkz2' in sites


@pytest.mark.order(3)
def test_upsert_profile(crawler, profile):
    fid = crawler.upsert_profile(profile=profile)
    assert fid is not None and fid > 0
    profile['fid'] = fid


@pytest.mark.order(4)
def test_upsert_profile_updates_existing_profile(crawler, profile):
    profile['ranking'] = 1
    updated_fid = crawler.upsert_profile(profile=profile)
    assert updated_fid == profile['fid']


@pytest.mark.order(5)
def test_get_profiles(crawler):
    profiles = crawler.get_profiles(site='anothernetworkz')
    assert any(p.account == 'Snowdens' for p in profiles)
    profiles = crawler.get_profiles(page=1, page_size=5)
    assert len(profiles) > 0
    profiles = crawler.get_profiles(all=True)
    assert len(profiles) > 0


@pytest.mark.order(7)
def test_edit_analyzer(crawler, analyzer):
    # Update some fields of the analyzer
    success = crawler.edit_analyzer(analyzer.to_dict())
    assert success


@pytest.mark.order(8)
def test_add_llm_engine(crawler):
    assert crawler.add_llm_engine(engine='anotherllm1z') is True
    assert crawler.add_llm_engine(engine='anotherllm2z') is True


@pytest.mark.order(9)
def test_get_engines(crawler):
    engines = crawler.get_llm_engines()
    assert 'anotherllm1z' in engines
    assert 'anotherllm2z' in engines


@pytest.mark.parametrize("site", SITES)
@pytest.mark.order(11)
def test__load_module(crawler, site):
    module = crawler._load_module(site=site)
    assert module is not None, f"Failed to load module for site: {site}"


@pytest.mark.parametrize("site", SITES)
@pytest.mark.order(11)
def test__fetch_posts(crawler, site):
    #crawler._fetch_posts(site=site)
    pass


@pytest.mark.order(12)
def test_add_follows_analyzer(crawler, profile, analyzer):
    assert crawler.add_follows_analyzer(uid=profile['uid'],
                                        aid=analyzer.aid,
                                        fid=profile['fid'],
                                        account=profile['account'])


@pytest.mark.order(13)
def test_del_follows_analyzer(crawler, profile, analyzer):
    assert crawler.delete_follows_analyzer(uid=profile['uid'],
                                           aid=analyzer.aid,
                                           fid=profile['fid'])


@pytest.mark.order(17)
def test_del_llm_engine(crawler):
    assert crawler.del_llm_engine(engine='anotherllm1z') is True
    assert crawler.del_llm_engine(engine='anotherllm2z') is True


@pytest.mark.order(18)
def test_del_profile(crawler, profile):
    assert crawler.del_profile(fid=profile['fid']) is True


@pytest.mark.order(19)
def test_del_site(crawler):
    assert crawler.del_site(site='anothernetworkz') is True
    assert crawler.del_site(site='anothernetworkz2') is True
