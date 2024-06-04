from __future__ import unicode_literals, print_function
import sys
import pytest
import arrow
from libs.crawler.apify.crawler import Crawler
from libs.structs.crawler_struct import CrawlerStruct
from libs.structs.crawler_post_struct import CrawlerPostStruct
from libs.structs.crawler_analyzer_struct import CrawlerAnalyzerStruct
from os import getpid
from time import sleep


@pytest.fixture(scope="module")
def crawler():
    crawler = Crawler()
    yield crawler
    del crawler

@pytest.fixture(scope="module")
def post():
    crawler_post = CrawlerPostStruct(
        account='Anbessa100',
        site='twitter',
        content='GN frens',
        timestamp=arrow.utcnow(),
        urls='',
        media=True,
        media_ocr='taxed stuff',
        is_reply=False,
        self_reply=False,
        account_id=226749344,
        reply_to=None,
        remote_id=1778937197871185951,
        pre_score=827.20,
        score=None,
        replies=28,
        views=19012,
        likes=98,
        reposts=0,
        followers=286683,
        post_id=2289
    )
    yield crawler_post


@pytest.mark.order(1)
def test_image_ocr(crawler):
    res = crawler.image_ocr(image_path='test_images/test1.jpg')
    assert "taxed" in res

