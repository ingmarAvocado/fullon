from __future__ import unicode_literals, print_function
import sys
import pytest
import arrow
from decimal import Decimal
from libs.models.crawler_model import Database
from libs.structs.crawler_struct import CrawlerStruct
from libs.structs.crawler_post_struct import CrawlerPostStruct
from libs.structs.crawler_analyzer_struct import CrawlerAnalyzerStruct


@pytest.fixture(scope="module")
def profile():
    return CrawlerStruct(fid=0, uid=1, site='anothernetwork', account='Snowden', ranking=2, contra=False, expertise='hacking')


@pytest.fixture(scope="module")
def dbase_c():
    dbase = Database()
    yield dbase
    del dbase


@pytest.fixture(scope="module")
def analyzer(dbase_c):
    test_analyzer = CrawlerAnalyzerStruct(title="Test Analyzer", prompt="Test Prompt")
    aid = dbase_c.add_analyzer(analyzer=test_analyzer)
    assert aid is not None and isinstance(aid, int)
    test_analyzer.aid = aid
    yield test_analyzer
    #dbase.del_analyzer(aid=aid)

@pytest.fixture(scope="module")
def posts():
    posts_list = [
        CrawlerPostStruct(
            account="Snowden",
            account_id=0,
            remote_id=1,
            site='anothernetwork',
            content='A big revelation',
            timestamp=arrow.utcnow().format("YYYY-MM-DD HH:mm:ss.SSS"),
            media="file.jpg",
            media_ocr="Lambo!",
            urls='www.lambo.com',
            is_reply=False,
            reply_to=None,
            self_reply=False,
            views=0,
            likes=0,
            reposts=0,
            replies=0,
            followers=0,
            pre_score=Decimal("0.5")
        ),
        CrawlerPostStruct(
            account="Snowden",
            account_id=0,
            remote_id=2,
            site='anothernetwork',
            content='Second big revelation',
            timestamp=arrow.utcnow().format("YYYY-MM-DD HH:mm:ss.SSS"),
            media="file2.jpg",
            media_ocr="Ferrari!",
            urls='www.ferrari.com',
            is_reply=True,
            reply_to=None,
            self_reply = False,
            views=10,
            likes=5,
            reposts=2,
            replies=1,
            followers=1000,
            pre_score=Decimal("0.9")
        )
    ]
    yield posts_list





@pytest.fixture(scope="function")
def added_analyzer(dbase_c, analyzer):
    aid = dbase_c.add_analyzer(analyzer=analyzer)
    assert aid is not None and aid > 0
    analyzer.aid = aid
    yield analyzer

@pytest.fixture(scope="function")
def setup_engine_follows(analyzer, profile):
    # Assuming existence of methods to add necessary referenced records
    # and returning their IDs for cleanup
    uid = profile.uid  # Add a user and get uid
    aid = analyzer.aid  # Add an analyzer and get aid
    fid = profile.fid  # Add a site follow and get fid
    yield uid, aid, fid


@pytest.mark.order(1)
def test_add_site(dbase_c):
    assert dbase_c.add_crawler_site(site='anothernetwork') is True
    assert dbase_c.add_crawler_site(site='anothernetwork2') is True


@pytest.mark.order(2)
def test_get_sites(dbase_c):
    sites = dbase_c.get_crawler_sites()
    assert 'anothernetwork' in sites
    assert 'anothernetwork2' in sites


@pytest.mark.order(3)
def test_upsert_profile_adds_new_profile(dbase_c, profile):
    fid = dbase_c.upsert_profile(profile=profile)
    assert fid is not None and fid > 0
    profile.fid = fid


@pytest.mark.order(4)
def test_get_crawling_list(dbase_c):
    sites = dbase_c.get_crawling_list(site='anothernetwork')
    assert isinstance(sites, list)
    assert len(sites) > 0


@pytest.mark.order(5)
def test_upsert_profile_updates_existing_profile(dbase_c, profile):
    profile.ranking = 1
    updated_fid = dbase_c.upsert_profile(profile=profile)
    assert updated_fid == profile.fid


@pytest.mark.order(5)
def test_add_analyzer(dbase_c, analyzer):
    aid = dbase_c.add_analyzer(analyzer=analyzer)
    assert aid is not None and aid > 0
    # Store aid for later use in update and delete tests
    analyzer.aid = aid


@pytest.mark.order(6)
def test_edit_analyzer(dbase_c, added_analyzer):
    # Update the analyzer details
    added_analyzer.title = "Updated Title"
    added_analyzer.prompt = "Updated Prompt"
    success = dbase_c.edit_analyzer(analyzer=added_analyzer)
    assert success is True


@pytest.mark.order(7)
def test_get_analyzers(dbase_c, analyzer):
    # Retrieve all analyzers from the database
    analyzers = dbase_c.get_analyzers()
    # Check if the returned value is a list of CrawlerAnalyzerStruct instances
    assert isinstance(analyzers, list), "get_analyzers should return a list"
    assert all(isinstance(a, CrawlerAnalyzerStruct) for a in analyzers), "All items in the list should be CrawlerAnalyzerStruct instances"
    # Check if the list contains the analyzer added by the fixture
    found = any(a.aid == analyzer.aid and a.title == analyzer.title and a.prompt == analyzer.prompt for a in analyzers)
    assert found, "The added analyzer should be in the list returned by get_analyzers"


@pytest.mark.order(8)
def test_add_and_retrieve_posts(dbase_c, posts):
    # Bulk add posts and assert success
    assert dbase_c.add_posts(posts=posts) is True, "Bulk add posts should did not succeed"

    # Retrieve added posts to capture post_ids
    for post in posts:
        retrieved_posts = dbase_c.get_posts(account=post.account, site=post.site)
        assert len(retrieved_posts) > 0, f"Should retrieve posts for account {post.account} and site {post.site}"
        post.post_id = retrieved_posts[0].post_id  # Assuming the first post is the one we want
        assert post.post_id is not None, "Each post should have a post_id assigned"


@pytest.mark.order(10)
def test_get_post(dbase_c, posts):
    # Assuming posts[0] was successfully added and retrieved previously
    post = dbase_c.get_post(post_id=posts[0].post_id)
    assert post is not None, "Should successfully retrieve the post by post_id"
    assert post.account == posts[0].account, "Retrieved post should have the correct account"


@pytest.mark.order(11)
def test_get_last_post_date(dbase_c, posts):
    dates = dbase_c.get_last_post_date(site='anothernetwork', account=posts[0].account)
    account = posts[0].account
    if dates[account]:
        assert isinstance(dates[account], arrow.Arrow)


@pytest.mark.order(12)
def test_add_llm_engine(dbase_c):
    assert dbase_c.add_llm_engine(engine='anotherllm1') is True
    assert dbase_c.add_llm_engine(engine='anotherllm2') is True


@pytest.mark.order(13)
def test_get_llm_engines(dbase_c):
    engines = dbase_c.get_llm_engines()
    assert 'anotherllm1' in engines
    assert 'anotherllm2' in engines


@pytest.mark.order(14)
def test_add_follows_engine_record(dbase_c, analyzer, profile):
    """
    """
    uid = profile.uid  # Add a user and get uid
    aid = analyzer.aid  # Add an analyzer and get aid
    fid = profile.fid  # Add a site follow and get fid
    account = profile.account
    success = dbase_c.add_follows_analyzer(uid=uid, aid=aid, fid=fid, account=account)
    assert success, "Expected method to successfully insert record"


@pytest.mark.order(15)
def test_get_account_analyzers(dbase_c, analyzer):
    """
    Test to ensure get_unique_account_analyzers method returns a unique list
    of analyzers based on the follows_analyzers table.
    """
    # Preconditions are met by previous tests and fixtures
    # Execution: Call the method under test
    unique_analyzers = dbase_c.get_account_analyzers()
    # Verification: Check for the presence of the analyzer used in setup and uniqueness
    assert unique_analyzers, "Expected non-empty list of unique analyzers"
    found = False
    for ua in unique_analyzers:
        if ua.aid == analyzer.aid:
            found = True
            break
    assert found, "Expected to find the test analyzer in the list of unique analyzers"
    # Verifying uniqueness
    aids = [ua.aid for ua in unique_analyzers]
    assert len(aids) == len(set(aids)), "Expected list of analyzers to be unique"
    # Further tests could include more detailed checks on the titles, prompts, etc.
    # Cleanup not explicitly required if relying on broader test suite's setup and teardown


@pytest.mark.order(16)
def test_get_unscored_posts(dbase_c, posts, analyzer):
    test_post = posts[0]

    # Ensure the setup has correctly inserted the post
    assert test_post.post_id is not None, "Setup failed to insert the test post"

    # Use a known analyzer ID and engine for which the post should not have a score
    engine = 'anotherllm1'  # Example engine name
    # Execute: Call the method under test
    unscored_posts = dbase_c.get_unscored_posts(aid=analyzer.aid, engine=engine)

    # Verify that the method returns the correct unscored post
    assert unscored_posts, "get_unscored_posts should return a non-empty list"
    found = any(post.post_id == test_post.post_id for post in unscored_posts)
    assert found, "The setup post was not found in the returned unscored posts"


@pytest.mark.order(17)
def test_add_engine_score(posts, dbase_c, analyzer):
    edited_post = posts[0]
    score = 9.423423423
    engine = 'anotherllm1'
    res = dbase_c.add_engine_score(post_id=edited_post.post_id,
                                   aid=analyzer.aid,
                                   engine=engine,
                                   score=score)
    assert res is True


@pytest.mark.order(19)
def test_get_post_score(posts, dbase_c):
    score = posts[0].pre_score
    res = dbase_c.get_post(post_id=posts[0].post_id)
    assert isinstance(res.pre_score, Decimal)
    assert res.pre_score == score


@pytest.mark.order(20)
def test_update_post_media(dbase_c, posts):
    # For this test, let's change the `media_ocr` for each post
    for post in posts:
        post.media_ocr = f"Updated OCR for post {post.post_id}"

    success = dbase_c.update_post_media(posts=posts)
    assert success, "Batch OCR update failed"

    # Step 3: Retrieve the updated posts and verify the updates
    for original_post in posts:
        updated_post = dbase_c.get_post(post_id=original_post.post_id)
        assert updated_post is not None, f"Post {original_post.post_id} not found"
        assert updated_post.media_ocr == f"Updated OCR for post {original_post.post_id}", \
            f"OCR update not applied for post {original_post.post_id}"


@pytest.mark.order(21)
def test_get_pre_scores(dbase_c):
    scores = dbase_c.get_pre_scores()
    assert isinstance(scores, list)
    assert isinstance(scores[0], float)
    assert len(scores) > 0



@pytest.mark.order(26)
def test_del_follows_engine_record(dbase_c, analyzer, profile):
    """
    """
    uid = profile.uid  # Add a user and get uid
    aid = analyzer.aid  # Add an analyzer and get aid
    fid = profile.fid  # Add a site follow and get fid
    success = dbase_c.delete_follows_analyzer(uid=uid, aid=aid, fid=fid)
    assert success, "Expected method to successfully delere record"

@pytest.mark.order(27)
def test_del_llm_engine(dbase_c):
    assert dbase_c.del_llm_engine(engine='anotherllm1') is True
    assert dbase_c.del_llm_engine(engine='anotherllm2') is True


@pytest.mark.order(28)
def test_del_analyzer(dbase_c, added_analyzer):
    success = dbase_c.del_analyzer(aid=added_analyzer.aid)
    assert success is True


@pytest.mark.order(29)
def test_del_profile(dbase_c, profile):
    assert dbase_c.del_profile(fid=profile.fid) is True


@pytest.mark.order(30)
def test_del_site(dbase_c):
    assert dbase_c.del_crawler_site(site='anothernetwork') is True
    assert dbase_c.del_crawler_site(site='anothernetwork2') is True
