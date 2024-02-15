from libs import strategy, log, settings, exchange
from libs.database import Database
from libs.bot import Bot
from libs.settings_config import fullon_settings_loader
from libs.btrader.fullonsimfeed import FullonSimFeed
from libs.btrader.fullonresampler import FullonFeedResampler
import backtrader as bt
import arrow
import importlib
import pytest


FEED_CLASSES = {
    "FullonFeed": "libs.btrader.fullonfeed.FullonFeed",
    "FullonSimFeed": "libs.btrader.fullonsimfeed.FullonSimFeed",
    "FullonEventFeed": "libs.btrader.fulloneventfeed.FullonEventFeed"
}


@pytest.fixture
def bot():
    bot = Bot(1, 432)
    yield bot
    del bot
    # Any teardown code can be placed here, if necessary


def test_init(bot):
    assert bot.strategy == "trading101_pairs"
    assert bot.id == 1
    assert isinstance(bot.strategy, str)
    # Add more assertions for other attributes if necessary


def test__set_feeds(bot):
    dbase = Database()
    feeds = dbase.get_bot_feeds(bot_id=bot.id)
    bot._set_feeds(feeds, dbase=dbase)
    del dbase
    assert len(bot.str_feeds) == 4
    assert bot.str_feeds[0].symbol == "BTC/USD"
    assert bot.str_feeds[0].period == "Ticks"
    assert bot.str_feeds[0].compression == 1


def test__str_set_params(bot):
    dbase = Database()
    params = bot._str_set_params(dbase)
    del dbase
    assert isinstance(params['helper'], Bot)


def test_extend_str_params(bot):
    test_params = {"param1": 1, "param2": 2}
    bot.extend_str_params(test_params)
    assert bot.str_params["param1"] == 1
    assert bot.str_params["param2"] == 2


def test__set_timeframe(bot):
    # Test valid timeframes
    assert bot._set_timeframe("ticks") == bt.TimeFrame.Ticks
    assert bot._set_timeframe("minutes") == bt.TimeFrame.Minutes
    assert bot._set_timeframe("days") == bt.TimeFrame.Days
    assert bot._set_timeframe("weeks") == bt.TimeFrame.Weeks
    assert bot._set_timeframe("months") == bt.TimeFrame.Months

    # Test case insensitivity
    assert bot._set_timeframe("Days") == bt.TimeFrame.Days

    # Test invalid timeframe
    assert bot._set_timeframe("invalid") is None


def test_backload_from(bot):
    # Setup feeds
    with Database() as dbase:
        feeds = dbase.get_bot_feeds(bot_id=bot.id)
        bot._set_feeds(feeds, dbase=dbase)

    # Test valid bars
    backload_time_100 = bot.backload_from(100)
    backload_time_200 = bot.backload_from(200)

    assert isinstance(backload_time_100[0], arrow.Arrow)
    assert isinstance(backload_time_100[0], arrow.Arrow)
    assert isinstance(backload_time_200[1], arrow.Arrow)
    assert isinstance(backload_time_200[1], arrow.Arrow)

    # Test if backload_time_200 is before backload_time_100
    assert backload_time_200[0] < backload_time_100[0]

    # Test if backload_time_100 is before current time
    assert backload_time_100[0] < arrow.utcnow()


def test__load_feeds(bot, mocker):
    # Setup feeds
    dbase = Database()
    feeds = dbase.get_bot_feeds(bot_id=bot.id)
    bot._set_feeds(feeds, dbase=dbase)

    del dbase
    # Setup cerebro
    cerebro = bt.Cerebro()

    # Load feeds
    bot._load_feeds(cerebro, warm_up=450, event=False, ofeeds={})

    # Check if feeds are loaded correctly
    assert len(cerebro.datas) == len(bot.str_feeds)
    for i, data in enumerate(cerebro.datas):
        assert data._name == str(i)
        assert isinstance(data, FullonSimFeed)
    bot._pair_feeds(cerebro=cerebro)


'''
def test_start_bot():
    # Test that the bot is instantiated with a valid UUID
    bot1 = bot.Bot('00000000-0000-0000-0000-000000000002')
    assert isinstance(bot1, bot.Bot), "The bot instance is not of type 'bot.Bot'"

    # Test that the bot has a valid UUID attribute
    assert hasattr(bot1, 'id'), "The bot instance does not have a 'bot_id' attribute"
    assert isinstance(bot1.id, str), "The 'bot_id' attribute is not a string"
    assert len(bot1.id) == 36, "The 'bot_id' attribute is less than 36"

    #  Test it has feeds
    assert hasattr(bot1, 'str_feeds'), "The bot has no feeds"
    assert isinstance(bot1.str_feeds, list), "the bots feeds are not a list"
    assert len(bot1.str_feeds) > 0, "the bot feeds is empty"

    bot1 = bot.Bot('00000000-0000-0000-0000-000000000000')
    assert (bot1.id is None), "The bot instance can't handle unknown bot_id"


def get_date_from_bars(bars: int, period: str, compression: int = 1) -> arrow.arrow.Arrow:
    period_map = {
        "ticks": 1,
        "minutes": 60,
        "hours": 3600,
        "days": 86400,
        "weeks": 604800,
        "months": 2629746  # assuming 30.44 days per month
    }
    period = period.lower()
    baja = compression * period_map.get(period, 0) * bars
    return arrow.utcnow().shift(seconds=-baja).replace(second=0, microsecond=0)


def test_live_strategy():
    bot1 = bot.Bot('00000000-0000-0000-0000-000000000002')
    cerebro = bt.Cerebro()
    strategy.STRATEGY_TYPE = "testlive"
    module = importlib.import_module(
        'strategies.'+bot1.strategy+'.strategy',
        package='strategy')
    strat = cerebro.addstrategy(module.strategy, **bot1.str_params)
    strategy_instance = cerebro.strats[0][0]
    feed = bot1.str_feeds[0]
    # i need to change this 
    fromdate = get_date_from_bars(bars=module.strategy.params.bars,
                                  period='minutes',
                                  compression=10)
    # i need the method get_date_from_bars
    feed_class = FEED_CLASSES['FullonFeed']
    feed_module, feed_class_name = feed_class.rsplit(".", 1)
    FeedClass = getattr(importlib.import_module(feed_module), feed_class_name)
    data = FeedClass(feed=feed,
                     timeframe=1,
                     compression=1,
                     helper=bot1,
                     fromdate=fromdate)
    cerebro.adddata(data, name='0')

    resampled_data = cerebro.resampledata(data, timeframe=4, compression=3)
    sampler = FullonFeedResampler()
    fullon_resampled_data = sampler.prepare(data=resampled_data,
                                            bars=module.strategy.params.bars,
                                            timeframe=4,
                                            compression=3)
    cerebro.adddata(fullon_resampled_data, name='1')
    cerebro.run(runonce=True)


def test_simul_strategy():
    bot1 = bot.Bot('00000000-0000-0000-0000-000000000001', 432)
    test_params = {'sma1': '45', 'sma2': '13', 'zshort': '-3.0', 'zlong': '3.0', 'zexitlow': '-1.5', 'zexithigh': '1.5', 'stop_loss': 1.0, 'take_profit': 1.0}
    feeds = {}
    bot1.run_simul_loop(feeds=feeds,
                        visual=False,
                        test_params={},
                        warm_up=450,
                        event=False)
'''

