import pytest
from unittest.mock import patch
from libs.bot import Bot
from libs.database import Database
from libs.models.ohlcv_model import Database as DataBase_ohclv
from libs.btrader.fullonsimfeed import FullonSimFeed


@pytest.fixture
def fullon_sim_feed():
    # You need to create a feed, helper, and broker instance here based on your application
    bot1 = Bot(1, 432)
    with Database() as dbase:
        feeds = dbase.get_bot_feeds(bot_id=bot1.id)
    feed = feeds[0]
    timeframe = bot1._set_timeframe(period=feed.period)
    fromdate = bot1.backload_from(bars=bot1.bars)[0].floor('day')
    fullon_feed = FullonSimFeed(feed=feed,
                                timeframe=timeframe,
                                compression=int(feed.compression),
                                helper=bot1,
                                fromdate=fromdate,
                                mainfeed=None)
    setattr(fullon_feed, 'time_factor', 1)
    return fullon_feed


@pytest.mark.order(1)
def test_fetch_ohlcv(fullon_sim_feed):
    with patch.object(fullon_sim_feed, '_load_from_pickle') as mock_load_from_pickle, \
            patch.object(fullon_sim_feed, '_save_to_df') as mock_save_to_df, \
            patch.object(fullon_sim_feed, '_save_to_pickle') as mock_save_to_pickle, \
            patch.object(fullon_sim_feed, '_empty_bar') as mock_empty_bar:
        # Test when pickle file exists
        mock_load_from_pickle.return_value = [('2023-05-16 00:00:00', 60000, 61000, 59000, 60500, 500)]
        fullon_sim_feed._fetch_ohlcv()
        mock_load_from_pickle.assert_called_once_with(fromdate=fullon_sim_feed.p.fromdate)
        mock_save_to_df.assert_called_once()
        assert len(fullon_sim_feed.result) == 1
        assert fullon_sim_feed.result[0] == ('2023-05-16 00:00:00', 60000, 61000, 59000, 60500, 500)
        mock_save_to_pickle.assert_not_called()
        mock_empty_bar.assert_not_called()

        # Test when pickle file does not exist
        mock_load_from_pickle.return_value = []
        fullon_sim_feed._fetch_ohlcv()
        mock_load_from_pickle.assert_called_with(fromdate=fullon_sim_feed.p.fromdate)
        mock_save_to_df.assert_called_once()
