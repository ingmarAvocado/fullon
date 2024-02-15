from libs.bot import Bot
from libs.database import Database
from libs.models.ohlcv_model import Database as DataBase_ohclv
from libs.btrader.fullonfeed import FullonFeed
import backtrader as bt
import pytest
import random
import arrow
from collections import deque
from unittest.mock import PropertyMock, MagicMock


@pytest.fixture
def fullon_feed():
    # You need to create a feed, helper, and broker instance here based on your application
    bot1 = Bot(1, 432)
    with Database() as dbase:
        feeds = dbase.get_bot_feeds(bot_id=bot1.id)
    feed = feeds[0]
    timeframe = bot1._set_timeframe(period=feed.period)
    fromdate = bot1.backload_from(bars=bot1.bars)[0].floor('day')
    fullon_feed = FullonFeed(feed=feed,
                             timeframe=timeframe,
                             compression=int(feed.compression),
                             helper=bot1,
                             fromdate=fromdate,
                             mainfeed=None)
    return fullon_feed


def test_init(fullon_feed):
    assert isinstance(fullon_feed, FullonFeed)
    assert fullon_feed.pos == 0
    assert fullon_feed.exit is False


def test_start(fullon_feed):
    fullon_feed.start(count=5)
    assert fullon_feed._state == fullon_feed._ST_HISTORY
    assert fullon_feed._table != ""


def test_islive(fullon_feed):
    fullon_feed._state = fullon_feed._ST_LIVE
    assert fullon_feed.islive() == True
    fullon_feed._state = fullon_feed._ST_HISTORY
    assert fullon_feed.islive() == False


def test_stop(fullon_feed):
    fullon_feed.stop()
    assert fullon_feed.exit is False


def test_get_time_factor(fullon_feed):
    fullon_feed.feed.period = "minutes"
    fullon_feed.compression = 5
    assert fullon_feed.get_time_factor() == 300

    fullon_feed.feed.period = "days"
    fullon_feed.compression = 3
    assert fullon_feed.get_time_factor() == 259200


def test_empty_bar(fullon_feed):
    fullon_feed._state = fullon_feed._ST_LIVE
    fullon_feed._empty_bar()
    assert fullon_feed.result == []
    assert fullon_feed._last_id is ''


def test_get_table(fullon_feed, mocker):
    mock_table_exists = mocker.patch.object(DataBase_ohclv, "table_exists")

    mock_table_exists.side_effect = [True, False]
    result = fullon_feed._get_table()
    assert result == "kraken_BTC_USD.trades"

    '''
    mock_table_exists.side_effect = [False, True]
    result = fullon_feed._get_table()
    assert result == "kraken_BTC_USD.candles1m"

    mock_table_exists.side_effect = [False, False]
    with pytest.raises(ValueError):
        fullon_feed._get_table()
    '''


def test_fetch_tick(fullon_feed, mocker):
    # Mock the cache's get_ticker method
    ticker_data = ("price", "timestamp")
    mocker.patch("libs.cache.Cache.get_ticker", return_value=ticker_data)
    fullon_feed._last_id = None

    # Test the _fetch_tick method
    result = fullon_feed._fetch_tick()
    assert result[1] == "price"


def test_get_last_date(fullon_feed,):
    # Mock the Database's get_last_date method
    result = fullon_feed.get_last_date()
    assert isinstance(result, arrow.Arrow)


''' mocking is not working well with the queue, need to figure out a way
def test_fetch_ohlcv(fullon_feed, mocker, dbohlcv_session):
    # Mock the necessary methods
    #fetch_ohlcv_mock = mocker.patch.object(dbohlcv_session, "_run_default")
    fullon_feed._fetch_ohlcv()
    assert fullon_feed._last_id == rows[-1][0]
    assert fullon_feed.result == deque(rows)
    fetch_ohlcv_mock.assert_called_once()
    empty_bar_mock.assert_not_called()

    # Reset the result for the next call
    fullon_feed.result = deque()
    # Test when no rows are returned
    fetch_ohlcv_mock.return_value = []
    fullon_feed._fetch_ohlcv()
    empty_bar_mock.assert_called_once()


def test_load_ohlcv(fullon_feed, mocker):
    # Mock _load_ohlcv_line method
    mock_load_ohlcv_line = mocker.patch.object(fullon_feed, "_load_ohlcv_line")

    # Define a mock result with OHLCV data
    ohlcv_row = ["2023-05-16T00:00:00+00:00", 60000, 61000, 59000, 60500, 500]
    fullon_feed.result = deque([ohlcv_row])
    # Test when everything goes as planned
    assert fullon_feed._load_ohlcv() is True


def test_load_ohlcv_line(fullon_feed):
    # Define a row of OHLCV data
    ohlcv_row = ["2023-05-16T00:00:00+00:00", 60000, 61000, 59000, 60500, 500]

    # Create mock Lines and LineBuffer objects
    mock_lines = MagicMock(spec=bt.Lines)
    mock_datetime = MagicMock(spec=bt.LineBuffer)
    mock_open = MagicMock(spec=bt.LineBuffer)
    mock_high = MagicMock(spec=bt.LineBuffer)
    mock_low = MagicMock(spec=bt.LineBuffer)
    mock_close = MagicMock(spec=bt.LineBuffer)
    mock_volume = MagicMock(spec=bt.LineBuffer)
    mock_openinterest = MagicMock(spec=bt.LineBuffer)

    # Assign mock LineBuffer objects to mock Lines attributes
    type(mock_lines).datetime = PropertyMock(return_value=mock_datetime)
    type(mock_lines).open = PropertyMock(return_value=mock_open)
    type(mock_lines).high = PropertyMock(return_value=mock_high)
    type(mock_lines).low = PropertyMock(return_value=mock_low)
    type(mock_lines).close = PropertyMock(return_value=mock_close)
    type(mock_lines).volume = PropertyMock(return_value=mock_volume)
    type(mock_lines).openinterest = PropertyMock(return_value=mock_openinterest)

    # Assign mock Lines object to FullonFeed's lines attribute
    type(fullon_feed).lines = PropertyMock(return_value=mock_lines)

    # Call the _load_ohlcv_line method
    fullon_feed._load_ohlcv_line(ohlcv_row, 0)

    # Assert that LineBuffer.__setitem__ was called on each line with the correct arguments
    mock_datetime.__setitem__.assert_called_once_with(0, bt.date2num(arrow.get(ohlcv_row[0])))
    mock_open.__setitem__.assert_called_once_with(0, float(ohlcv_row[1]))
    mock_high.__setitem__.assert_called_once_with(0, float(ohlcv_row[2]))
    mock_low.__setitem__.assert_called_once_with(0, float(ohlcv_row[3]))
    mock_close.__setitem__.assert_called_once_with(0, float(ohlcv_row[4]))
    mock_volume.__setitem__.assert_called_once_with(0, float(ohlcv_row[5]))
    mock_openinterest.__setitem__.assert_called_once_with(0, 0)
'''
