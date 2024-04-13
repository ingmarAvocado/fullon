from libs import strategy, log, settings, exchange
from libs.database import Database
from libs.bot import Bot
from libs.settings_config import fullon_settings_loader
from libs.btrader.fullonsimfeed import FullonSimFeed
from libs.btrader.fullonfeed import FullonFeed
from libs.btrader.fullonresampler import FullonFeedResampler
import backtrader as bt
import arrow
import importlib
import pytest


cerebro = None

FEED_CLASSES = {
    "FullonFeed": "libs.btrader.fullonfeed.FullonFeed",
    "FullonSimFeed": "libs.btrader.fullonsimfeed.FullonSimFeed",
    "FullonEventFeed": "libs.btrader.fulloneventfeed.FullonEventFeed"
}


@pytest.fixture
def bot(bot_id, feed1, feed2):
    bot = Bot(bot_id, 432)
    yield bot
    del bot
    # Any teardown code can be placed here, if necessary


@pytest.mark.order(1)
def test_init(bot, symbol1, bot_id):
    assert bot.id == bot_id
    assert isinstance(bot.bot_name, str)
    # Add more assertions for other attributes if necessary


@pytest.mark.order(2)
def test__set_feeds(bot, dbase, str_id1, str_id2, symbol1, symbol2):
    bot._set_feeds(dbase=dbase)
    assert len(bot.str_feeds) == 2
    assert bot.str_feeds[str_id1][0].symbol == symbol1.symbol
    assert bot.str_feeds[str_id1][0].period == "Ticks"
    assert bot.str_feeds[str_id1][0].compression == 1
    assert bot.str_feeds[str_id2][0].symbol == symbol2.symbol
    assert bot.str_feeds[str_id2][0].period == "Ticks"
    assert bot.str_feeds[str_id2][0].compression == 1


@pytest.mark.order(3)
def test__str_set_params(bot, dbase, str_id1):
    params = bot._str_set_params(dbase)
    assert isinstance(params[str_id1]['helper'], Bot)


@pytest.mark.order(4)
def test_extend_str_params(bot, str_id1):
    test_params = {"param1": 1, "param2": 2}
    bot.extend_str_params(test_params=test_params, str_id=str_id1)
    assert bot.str_params[str_id1]["param1"] == 1
    assert bot.str_params[str_id1]["param2"] == 2

@pytest.mark.order(5)
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


@pytest.mark.order(6)
def test_backload_from(bot, str_id1, str_id2):
    # Test valid bars
    backload_time_100 = bot.backload_from(str_id=str_id1, bars=100)
    backload_time_200 = bot.backload_from(str_id=str_id2, bars=200)
    assert isinstance(backload_time_100[0], arrow.Arrow)
    assert isinstance(backload_time_100[0], arrow.Arrow)
    assert isinstance(backload_time_200[1], arrow.Arrow)
    assert isinstance(backload_time_200[1], arrow.Arrow)
    # Test if backload_time_200 is before backload_time_100
    assert backload_time_200[0] < backload_time_100[0]
    # Test if backload_time_100 is before current time
    assert backload_time_100[0] < arrow.utcnow()

@pytest.mark.order(7)
def test__load_feeds(bot, mocker):
    global cerebro
    mocker.patch.object(bot, '_sim_feeds_can_start', return_value=True)
    cerebro = bt.Cerebro()
    # Load feeds
    bot._load_feeds(cerebro, warm_up=450, event=False, ofeeds={})
    # Check if feeds are loaded correctly
    loaded = []
    for feeds in bot.str_feeds.values():
        for feed in feeds:
            key = f"{feed.ex_id}:{feed.symbol}:{feed.period}:{feed.compression}"
            if key not in loaded:
                loaded.append(key)
    assert len(cerebro.datas) == len(loaded)
    for i, data in enumerate(cerebro.datas):
        assert data._name == str(i)
        assert isinstance(data, FullonSimFeed)


@pytest.mark.order(8)
def test_pair_feeds(bot):
    bot._pair_feeds(cerebro=cerebro)

@pytest.mark.order(9)
def test__load_live_feeds(bot, mocker):
    global cerebro
    cerebro = bt.Cerebro()
    # Load feeds
    bot._load_live_feeds(cerebro, bars=200)
    # Check if feeds are loaded correctly
    loaded = []
    for feeds in bot.str_feeds.values():
        for feed in feeds:
            key = f"{feed.ex_id}:{feed.symbol}:{feed.period}:{feed.compression}"
            if key not in loaded:
                loaded.append(key)
    assert len(cerebro.datas) == len(loaded)


@pytest.mark.order(10)
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


'''
def test_simul_strategy(bot):
    test_params = {'sma1': '45'}
    feeds = {}
    bot.run_simul_loop(feeds=feeds,
                       visual=False,
                       test_params={},
                       warm_up=450,
                       event=False)



def test_live_strategy():
    bot1 = bot.Bot('2')
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
    bot1 = bot.Bot('1', 432)
    test_params = {'sma1': '45', 'sma2': '13', 'zshort': '-3.0', 'zlong': '3.0', 'zexitlow': '-1.5', 'zexithigh': '1.5', 'stop_loss': 1.0, 'take_profit': 1.0}
    feeds = {}
    bot1.run_simul_loop(feeds=feeds,
                        visual=False,
                        test_params={},
                        warm_up=450,
                        event=False)
'''

