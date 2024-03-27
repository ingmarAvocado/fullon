from __future__ import unicode_literals, print_function
import sys
from libs.models.bot_model import Database
import pytest

@pytest.fixture(scope="module")
def dbase():
    with Database() as dbase:
        yield dbase


def test_get_bot_details(dbase):
    bot = dbase.get_bot_list(bot_id=1)
    assert len(bot) > 0


def test_edit_bot(dbase):
    bot = dbase.get_bot_list(bot_id=1)[0]
    _bot = {'bot_id': bot.bot_id,
            'dry_run': bot.dry_run,
            'name': bot.name,
            'uid': bot.uid,
            'timestamp': bot.timestamp}
    res = dbase.edit_bot(bot=_bot)


def test_edit_feeds(dbase):
    feeds = {}
    _feeds = dbase.get_bot_feeds(1)
    if _feeds:
        for feed in _feeds:
            feeds[feed.feed_id] = {
                              'symbol': feed.symbol,
                              'exchange': feed.exchange_name,
                              'compression': feed.compression,
                              'period': feed.period,
                              'feed_id': feed.feed_id
                              }
    res = dbase.edit_feeds(bot_id=1, feeds=feeds)
    assert res is True


def test_save_bot_log(dbase):
    bot_id = 2
    message = 'open'
    position = 0.0001
    feed_num = 0
    symbol = 'BTC/USD'
    ex_id = '0'
    res = dbase.save_bot_log(bot_id=bot_id,
                             message=message,
                             position=position,
                             feed_num=feed_num,
                             ex_id=ex_id,
                             symbol=symbol)
    assert res is True
