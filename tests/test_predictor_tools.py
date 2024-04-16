from __future__ import unicode_literals, print_function
import sys
import libs.predictor.predictor_tools as PredictorTools
from libs.btrader.fullonfeed import FullonFeed
from libs.bot import Bot
import datetime
import pytest
import arrow
import backtrader as bt


@pytest.fixture
def fullon_feed(dbase):
    # You need to create a feed, helper, and broker instance here based on your application
    bot1 = Bot(1, 432)  # depends on fullon demo data
    feeds = dbase.get_bot_feeds(bot_id=bot1.id)
    feed = feeds[1]
    timeframe = bot1._set_timeframe(period=feed.period)
    fromdate = bot1.backload_from(str_id=feed.str_id, bars=bot1.bars)[0].floor('day')
    fullon_feed = FullonFeed(feed=feed,
                             timeframe=timeframe,
                             compression=int(feed.compression),
                             helper=bot1,
                             fromdate=fromdate,
                             mainfeed=None)
    setattr(fullon_feed.feed, 'strategy_name', 'pytest')
    yield fullon_feed


@pytest.fixture
def fromdate(fullon_feed):
    ts = PredictorTools.get_oldest_timestamp(feed=fullon_feed)
    assert isinstance(ts, datetime.datetime)
    yield ts


@pytest.mark.order(1)
def test_try_loading(fullon_feed, fromdate):
    regressors = ['GradientBoostingClassifier', 'CatBoostClassifier']
    todate = arrow.utcnow().floor('week')
    for regressor in regressors:
        _regressor, _file, _scaler, _ = PredictorTools.try_loading(
                                            fromdate=fromdate,
                                            todate=todate.format(),
                                            predictor=regressor,
                                            feed=fullon_feed.feed)
        assert _regressor is None
        assert _scaler is None

