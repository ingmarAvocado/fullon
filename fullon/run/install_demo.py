from run import install_manager
from run import user_manager
from run import bot_manager
from run.crawler_manager import CrawlerManager
from libs import log
from libs.structs.symbol_struct import SymbolStruct
from libs.structs.exchange_struct import ExchangeStruct
from libs.structs.crawler_analyzer_struct import CrawlerAnalyzerStruct
from libs.structs.crawler_struct import CrawlerStruct
from libs.database import Database
from typing import Optional, Tuple


logger = log.fullon_logger(__name__)


def install():
    install_symbols()
    uid = install_admin_user()
    if not uid:
        print("Could not install admin user")
        return
    ex_id, cat_ex_id = install_exchanges(uid=uid)
    if not ex_id or not cat_ex_id:
        print("Could not install admin exchanges")
    # install_secrets(uid=uid, cat_ex_id=cat_ex_id)
    install_bots(uid=uid, ex_id=ex_id, cat_ex_id=cat_ex_id)
    #install_crawler_follows(uid=uid)
    #install_crawler_analyzers()
    #add_analyzer_follows()


def install_symbols():
    # Instantiante install manager

    system = install_manager.InstallManager()

    # First lets install some symbols
    SYMBOL = {
        "symbol": "BTC/USD",
        "exchange_name": "kraken",
        "updateframe": "1h",
        "backtest": "2700",
        "decimals": 6,
        "base": "USD",
        "ex_base": "",
        "futures": "t"}
    system.install_symbol(symbol=SymbolStruct.from_dict(SYMBOL))

    SYMBOL = {
        "symbol": "ETH/USD",
        "exchange_name": "kraken",
        "updateframe": "1h",
        "backtest": "300",
        "decimals": 6,
        "base": "USD",
        "ex_base": "",
        "futures": "t"}
    system.install_symbol(symbol=SymbolStruct.from_dict(SYMBOL))

    SYMBOL = {
        "symbol": "ETH/BTC",
        "exchange_name": "kraken",
        "updateframe": "1h",
        "backtest": "365",
        "decimals": 6,
        "base": "USD",
        "ex_base": "",
        "futures": "t"}
    system.install_symbol(symbol=SymbolStruct.from_dict(SYMBOL))

    SYMBOL = {
        "symbol": "XMR/USD",
        "exchange_name": "kraken",
        "updateframe": "1h",
        "backtest": "365",
        "decimals": 6,
        "base": "USD",
        "ex_base": "",
        "futures": "t"}
    system.install_symbol(symbol=SymbolStruct.from_dict(SYMBOL))

    SYMBOL = {
        "symbol": "MATIC/USD",
        "exchange_name": "kraken",
        "updateframe": "1h",
        "backtest": "365",
        "decimals": 6,
        "base": "USD",
        "ex_base": "",
        "futures": "t"}
    system.install_symbol(symbol=SymbolStruct.from_dict(SYMBOL))

    SYMBOL = {
        "symbol": "XMR/BTC",
        "exchange_name": "kraken",
        "updateframe": "1h",
        "backtest": "365",
        "decimals": 6,
        "base": "USD",
        "ex_base": "",
        "futures": "t"}
    system.install_symbol(symbol=SymbolStruct.from_dict(SYMBOL))

    SYMBOL = {
        "symbol": "BTC/USDC",
        "exchange_name": "kraken",
        "updateframe": "1h",
        "backtest": "7",
        "decimals": 6,
        "base": "USD",
        "ex_base": "",
        "futures": "t"}
    system.install_symbol(symbol=SymbolStruct.from_dict(SYMBOL))

    SYMBOL = {
        "symbol": "SOL/USD",
        "exchange_name": "kraken",
        "updateframe": "1h",
        "backtest": "365",
        "decimals": 6,
        "base": "USD",
        "ex_base": "",
        "futures": "t"}
    system.install_symbol(symbol=SymbolStruct.from_dict(SYMBOL))

    SYMBOL = {
        "symbol": "ETH/USDC",
        "exchange_name": "kraken",
        "updateframe": "1h",
        "backtest": "365",
        "decimals": 6,
        "base": "USD",
        "ex_base": "",
        "futures": "t"}
    system.install_symbol(symbol=SymbolStruct.from_dict(SYMBOL))


def install_admin_user() -> Optional[int]:
    """
    installs users
    """
    user_system = user_manager.UserManager()
    # now lets add a user
    USER = {
        "mail": "admin@fullon",
        "password": "password",
        "f2a": '---',
        "role": "admin",
        "name": "robert",
        "lastname": "plant",
        "phone": 666666666,
        "id_num": 3242}
    user_system.add_user(USER)
    uid = user_system.get_user_id(mail='admin@fullon')
    return uid


def install_exchanges(uid: int) -> Tuple[str, str]:
    """
    """
    user = user_manager.UserManager()
    with Database() as dbase:
        cat_ex_id = dbase.get_cat_exchanges(exchange='kraken')[0][0]

    exchange = {
        "uid": uid,
        "cat_ex_id": cat_ex_id,
        "name": "kraken1",
        "test": "False",
        "active": "True"}
    ex_id = user.add_exchange(exch=ExchangeStruct.from_dict(exchange))
    return (ex_id, cat_ex_id)


def install_secrets(uid: int, cat_ex_id: str):
    """
    """
    user = user_manager.UserManager()
    key = input("Please give your exchange API key to fullon: ")
    secret = input("\nPlease give your exchange SECRET key to fullon: ")

    user.set_secret_key(user_id=uid, exchange=cat_ex_id, key=key, secret=secret)

    # -------------------------------------------------------
    # New bot # 1


def install_bots(uid: int, ex_id: str, cat_ex_id: str):
    """
    """
    user = user_manager.UserManager()

    BOT = {
        'user': uid,
        'name': 'test pair',
        'dry_run': 'True',
        'active': 'False'
    }
    bot_id = user.add_bot(bot=BOT)
    exchange = {"exchange_id": ex_id}
    user.add_bot_exchange(bot_id=bot_id, exchange=exchange)
    with Database() as dbase:
        cat_str_id = dbase.get_cat_str_id(name='trading101_pairs')
    STRAT = {
        "cat_str_id": cat_str_id,
        "bot_id": bot_id,
        "size_pct": 20,
        "size_currency": 'USD',
        "leverage": 2}
    str_id = user.add_bot_strategy(strategy=STRAT)
    feed = {
        "symbol_id": 1,
        "str_id": str_id,
        "period": 'Ticks',
        "compression": 1,
        "order": 1}
    user.add_feed_to_bot(feed=feed)
    feed = {
        "symbol_id": 2,
        "str_id": str_id,
        "period": 'Ticks',
        "compression": 1,
        "order": 2}
    user.add_feed_to_bot(feed=feed)

    feed = {
        "symbol_id": 1,
        "str_id": str_id,
        "period": 'Minutes',
        "compression": 10,
        "order": 3}
    user.add_feed_to_bot(feed=feed)

    feed = {
        "symbol_id": 2,
        "str_id": str_id,
        "period": 'Minutes',
        "compression": 10,
        "order": 4}
    user.add_feed_to_bot(feed=feed)
    logger.info(f"Bot {bot_id} has been installed")

    # -------------------------------------------------------
    # New bot #2

    BOT = {
        'user': uid,
        'name': 'trading101',
        'dry_run': 'True',
        'active': 'False'
    }
    bot_id = user.add_bot(bot=BOT)
    exchange = {"exchange_id": ex_id}
    user.add_bot_exchange(bot_id=bot_id, exchange=exchange)

    with Database() as dbase:
        cat_str_id = dbase.get_cat_str_id(name='trading101')
    STRAT = {
        "cat_str_id": cat_str_id,
        "bot_id": bot_id,
        "size_pct": 20,
        "size_currency": 'USD',
        "leverage": 2}
    str_id = user.add_bot_strategy(strategy=STRAT)

    feed = {
        "symbol_id": 1,
        "str_id": str_id,
        "period": 'Ticks',
        "compression": 1,
        "order": 1}
    user.add_feed_to_bot(feed=feed)
    feed = {
        "symbol_id": 1,
        "str_id": str_id,
        "period": 'Minutes',
        "compression": 10,
        "order": 2}
    user.add_feed_to_bot(feed=feed)
    logger.info(f"Bot {bot_id} has been installed")

    # -------------------------------------------------------
    # New bot #3

    BOT = {
        'user': uid,
        'name': 'doubles test',
        'dry_run': 'True',
        'active': 'False'
    }
    bot_id = user.add_bot(bot=BOT)
    exchange = {"exchange_id": ex_id}
    user.add_bot_exchange(bot_id=bot_id, exchange=exchange)

    with Database() as dbase:
        cat_str_id = dbase.get_cat_str_id(name='rsi_reversal')
    STRAT = {
        "cat_str_id": cat_str_id,
        "bot_id": bot_id,
        "size_pct": 20,
        "size_currency": 'USD',
        "leverage": 2}
    str_id = user.add_bot_strategy(strategy=STRAT)

    feed = {
        "symbol_id": 1,
        "str_id": str_id,
        "period": 'Ticks',
        "compression": 1,
        "order": 1}
    user.add_feed_to_bot(feed=feed)
    feed = {
        "symbol_id": 1,
        "str_id": str_id,
        "period": 'Days',
        "compression": 1,
        "order": 2}
    user.add_feed_to_bot(feed=feed)

    STRAT = {
        "cat_str_id": cat_str_id,
        "bot_id": bot_id,
        "size_pct": 20,
        "size_currency": 'USD',
        "leverage": 5}
    str_id2 = user.add_bot_strategy(strategy=STRAT)

    feed = {
        "symbol_id": 2,
        "str_id": str_id2,
        "period": 'Ticks',
        "compression": 1,
        "order": 1}
    user.add_feed_to_bot(feed=feed)
    feed = {
        "symbol_id": 2,
        "str_id": str_id2,
        "period": 'Days',
        "compression": 1,
        "order": 2}
    user.add_feed_to_bot(feed=feed)

    logger.info(f"Bot {bot_id} has been installed")

    # -------------------------------------------------------
    # New bot #4

    BOT = {
        'user': uid,
        'name': 'FOREST LONG BTC/USD',
        'dry_run': 'True',
        'active': 'True'
    }
    bot_id = user.add_bot(bot=BOT)
    exchange = {"exchange_id": ex_id}
    user.add_bot_exchange(bot_id=bot_id, exchange=exchange)

    with Database() as dbase:
        cat_str_id = dbase.get_cat_str_id(name='xgb_forest_mom_long')
    STRAT = {
        "cat_str_id": cat_str_id,
        "bot_id": bot_id,
        "leverage": 2}
    str_id = user.add_bot_strategy(strategy=STRAT)

    feed = {
        "symbol_id": 1,
        "str_id": str_id,
        "period": 'Ticks',
        "compression": 1,
        "order": 1}
    user.add_feed_to_bot(feed=feed)
    feed = {
        "symbol_id": 1,
        "str_id": str_id,
        "period": 'Days',
        "compression": 1,
        "order": 2}
    user.add_feed_to_bot(feed=feed)

    bot = bot_manager.BotManager()
    _strat = {"bot_id": bot_id,
              "str_id": str_id,
              "size": None,
              "size_pct": 20,
              "size_currency": "USD",
              "take_profit": 14,
              "trailing_stop": 13,
              "timeout": None
              }
    extended = {
          'rsi': "14",  #
          'rsi_entry': "60",
          'cmf': "18",
          'cmf_entry': '9',
          'vwap_entry': "0.4",
          'macd_entry': "2.5",
          "sma": "200",
          "prediction_steps": "1",
          "threshold": "0.48"}
    _strat['extended'] = extended
    bot.edit_bot_strat(bot_id=bot_id, strat=_strat)
    logger.info(f"Bot {bot_id} has been installed")

    # -------------------------------------------------------
    # bot 5

    BOT = {
        'user': uid,
        'name': 'FOREST LONG ETH/USD',
        'dry_run': 'True',
        'active': 'True'
    }
    bot_id = user.add_bot(bot=BOT)
    exchange = {"exchange_id": ex_id}
    user.add_bot_exchange(bot_id=bot_id, exchange=exchange)

    with Database() as dbase:
        cat_str_id = dbase.get_cat_str_id(name='xgb_forest_mom_long')
    STRAT = {
        "cat_str_id": cat_str_id,
        "bot_id": bot_id,
        "leverage": 2}
    str_id = user.add_bot_strategy(strategy=STRAT)

    feed = {
        "symbol_id": 2,
        "str_id": str_id,
        "period": 'Ticks',
        "compression": 1,
        "order": 1}
    user.add_feed_to_bot(feed=feed)
    feed = {
        "symbol_id": 2,
        "str_id": str_id,
        "period": 'Days',
        "compression": 1,
        "order": 2}
    user.add_feed_to_bot(feed=feed)

    bot = bot_manager.BotManager()
    _bot = {"bot_id": bot_id,
            "str_id": str_id,
            "size": None,
            "size_pct": 20,
            "size_currency": "USD",
            "take_profit": 14,
            "trailing_stop": 13,
            "timeout": None
            }
    extended = {
          'rsi': "14",  #
          'rsi_entry': "60",
          'cmf': "18",
          'cmf_entry': '13',
          'vwap_entry': "0.4",
          'macd_entry': "2.5",
          "sma": "200",
          "prediction_steps": "1",
          "threshold": "0.35"}
    _strat['extended'] = extended
    bot.edit_bot_strat(bot_id=bot_id, strat=_strat)
    logger.info(f"Bot {bot_id} has been installed")

    # -------------------------------------------------------
    # New bot #6
    BOT = {
        'user': uid,
        'name': 'FOREST LONG SOL/USD',
        'dry_run': 'True',
        'active': 'True'
    }
    bot_id = user.add_bot(bot=BOT)
    exchange = {"exchange_id": ex_id}
    user.add_bot_exchange(bot_id=bot_id, exchange=exchange)

    with Database() as dbase:
        cat_str_id = dbase.get_cat_str_id(name='xgb_forest_mom_long')
    STRAT = {
        "cat_str_id": cat_str_id,
        "bot_id": bot_id,
        "leverage": 2}
    str_id = user.add_bot_strategy(strategy=STRAT)

    feed = {
        "symbol_id": 8,
        "str_id": str_id,
        "period": 'Ticks',
        "compression": 1,
        "order": 1}
    user.add_feed_to_bot(feed=feed)
    feed = {
        "symbol_id": 8,
        "str_id": str_id,
        "period": 'Days',
        "compression": 1,
        "order": 2}
    user.add_feed_to_bot(feed=feed)

    bot = bot_manager.BotManager()
    _bot = {"bot_id": bot_id,
            "str_id": str_id,
            "size": None,
            "size_pct": 20,
            "size_currency": "USD",
            "take_profit": 14,
            "trailing_stop": 13,
            "timeout": None
            }
    extended = {
          'rsi': "14",  #
          'rsi_entry': "60",
          'cmf': "18",
          'cmf_entry': '9',
          'vwap_entry': "0.4",
          'macd_entry': "2.5",
          "sma": "200",
          "prediction_steps": "1",
          "threshold": "0.48"}
    _bot['extended'] = extended
    _strat['extended'] = extended
    bot.edit_bot_strat(bot_id=bot_id, strat=_strat)
    logger.info(f"Bot {bot_id} has been installed")

    # -------------------------------------------------------
    # New bot #7
    BOT = {
        'user': uid,
        'name': 'FOREST SHORT BTC/USD',
        'dry_run': 'True',
        'active': 'True'
    }
    bot_id = user.add_bot(bot=BOT)
    exchange = {"exchange_id": ex_id}
    user.add_bot_exchange(bot_id=bot_id, exchange=exchange)

    with Database() as dbase:
        cat_str_id = dbase.get_cat_str_id(name='xgb_forest_mom_short')
    STRAT = {
        "cat_str_id": cat_str_id,
        "bot_id": bot_id,
        "leverage": 2}
    str_id = user.add_bot_strategy(strategy=STRAT)

    feed = {
        "symbol_id": 1,
        "str_id": str_id,
        "period": 'Ticks',
        "compression": 1,
        "order": 1}
    user.add_feed_to_bot(feed=feed)
    feed = {
        "symbol_id": 1,
        "str_id": str_id,
        "period": 'Days',
        "compression": 1,
        "order": 2}
    user.add_feed_to_bot(feed=feed)

    bot = bot_manager.BotManager()
    _strat = {"bot_id": bot_id,
            "str_id": str_id,
            "size": None,
            "size_pct": 20,
            "size_currency": "USD",
            "take_profit": 16,
            "trailing_stop": 13,
            "timeout": None
            }
    extended = {
          'rsi': "14",
          'rsi_entry': "40",
          'macd_entry': "1.5",
          'stoch_entry': "50",
          "prediction_steps": "1",
          "threshold": "0.35"
          }
    _strat['extended'] = extended
    bot.edit_bot_strat(bot_id=bot_id, strat=_strat)
    logger.info(f"Bot {bot_id} has been installed")

    # -------------------------------------------------------
    # New bot #8
    BOT = {
        'user': uid,
        'name': 'FOREST SHORT ETH/USD',
        'dry_run': 'True',
        'active': 'True'
    }
    bot_id = user.add_bot(bot=BOT)
    exchange = {"exchange_id": ex_id}

    with Database() as dbase:
        cat_str_id = dbase.get_cat_str_id(name='xgb_forest_mom_short')
    STRAT = {
        "cat_str_id": cat_str_id,
        "bot_id": bot_id,
        "leverage": 2}
    str_id = user.add_bot_strategy(strategy=STRAT)

    feed = {
        "symbol_id": 2,
        "str_id": str_id,
        "period": 'Ticks',
        "compression": 1,
        "order": 1}
    user.add_feed_to_bot(feed=feed)
    feed = {
        "symbol_id": 2,
        "str_id": str_id,
        "period": 'Days',
        "compression": 1,
        "order": 2}
    user.add_feed_to_bot(feed=feed)

    bot = bot_manager.BotManager()
    _strat = {"bot_id": bot_id,
            "str_id": str_id,
            "size": None,
            "size_pct": 20,
            "size_currency": "USD",
            "take_profit": 16,
            "trailing_stop": 13,
            "timeout": None
            }
    extended = {
          'rsi': "14",
          'rsi_entry': "40",
          'macd_entry': "1.5",
          'stoch_entry': "50",
          "prediction_steps": "1",
          "threshold": "0.35"
          }
    _strat['extended'] = extended
    bot.edit_bot_strat(bot_id=bot_id, strat=_strat)
    logger.info(f"Bot {bot_id} has been installed")

    # -------------------------------------------------------
    # New bot #9
    BOT = {
        'user': uid,
        'name': 'FOREST SHORT SOL/USD',
        'dry_run': 'True',
        'active': 'True'
    }
    bot_id = user.add_bot(bot=BOT)
    exchange = {"exchange_id": ex_id}
    user.add_bot_exchange(bot_id=bot_id, exchange=exchange)

    with Database() as dbase:
        cat_str_id = dbase.get_cat_str_id(name='xgb_forest_mom_short')
    STRAT = {
        "cat_str_id": cat_str_id,
        "bot_id": bot_id,
        "leverage": 2}
    str_id = user.add_bot_strategy(strategy=STRAT)

    feed = {
        "symbol_id": 8,
        "str_id": str_id,
        "period": 'Ticks',
        "compression": 1,
        "order": 1}
    user.add_feed_to_bot(feed=feed)
    feed = {
        "symbol_id": 8,
        "str_id": str_id,
        "period": 'Days',
        "compression": 1,
        "order": 2}
    user.add_feed_to_bot(feed=feed)

    bot = bot_manager.BotManager()
    _strat = {"bot_id": bot_id,
              "str_id": str_id,
              "size": None,
              "size_pct": 20,
              "size_currency": "USD",
              "take_profit": 16,
              "trailing_stop": 13,
              "timeout": None
              }
    extended = {
          'rsi': "14",
          'rsi_entry': "40",
          'macd_entry': "1.5",
          'stoch_entry': "50",
          "prediction_steps": "1",
          "threshold": "0.35"
          }
    _strat['extended'] = extended
    bot.edit_bot_strat(bot_id=bot_id, strat=_strat)


def install_crawler_follows(uid: int):
    """
    Upsert multiple profiles for a given UID using CrawlerManager.
    """
    crawler = CrawlerManager()
    profiles = [
        {"uid": uid, "site": "twitter", "account": "Anbessa100", "ranking": 9, "contra": False, "expertise":
         "TA expert in bitcoin and prety good with little known alts, creative"},
        {"uid": uid, "site": "twitter", "account": "CryptoDonAlt", "ranking": 7, "contra": False, "expertise":
         "Solid bitcion trader and mayor alts"},
        {"uid": uid, "site": "twitter", "account": "Melt_Dem", "ranking": 7, "contra": False, "expertise":
         "crypto manager at coinshares"},
        {"uid": uid, "site": "twitter", "account": "PeterLBrandt", "ranking": 7, "contra": False, "expertise":
         "well known TA trader, good with markets in general, pretty good with Bitcoin"},
        {"uid": uid, "site": "twitter", "account": "Pentosh1", "ranking": 6, "contra": False, "expertise":
         "Well known trader, good with Bitcoin and mayor alts"},
        {"uid": uid, "site": "twitter", "account": "HoneybadgerC", "ranking": 6, "contra": False, "expertise":
         "Solid TA trader of crypto and bitcoin"},
        {"uid": uid, "site": "twitter", "account": "trader1sz", "ranking": 6, "contra": False, "expertise":
         "Solid TA trader of bitcoin and crypto"},
        {"uid": uid, "site": "twitter", "account": "EmperorBTC", "ranking": 8, "contra": False, "expertise":
         "Great TA trader and analyst of Bitcoin"},
        {"uid": uid, "site": "twitter", "account": "NicTrades", "ranking": 6, "contra": False, "expertise":
         "well known TA trader, good with markets in general, pretty good with Bitcoin"},
        {"uid": uid, "site": "twitter", "account": "LSDinmycoffee", "ranking": 2, "contra": False, "expertise":
         "well known TA trader, good with markets in general, pretty good with Bitcoin"},
        {"uid": uid, "site": "twitter", "account": "MacnBTC", "ranking": 5, "contra": False, "expertise":
         "Alt crypto trader"},
        {"uid": uid, "site": "twitter", "account": "CryptoCred", "ranking": 5, "contra": False, "expertise":
         "Solid bitcion trader and mayor alts"},
        {"uid": uid, "site": "twitter", "account": "Crypto_Core", "ranking": 6, "contra": False, "expertise":
         "Solid bitcion trader and mayor alts"},
        {"uid": uid, "site": "twitter", "account": "laughncow1", "ranking": 5, "contra": False, "expertise":
         "Solid TA trader of crypto and bitcoin"},
        {"uid": uid, "site": "twitter", "account": "CryptoYoda1338", "ranking": 5, "contra": False, "expertise":
         "Solid TA trader of crypto and bitcoin"},
        {"uid": uid, "site": "twitter", "account": "FatihSK87", "ranking": 5, "contra": False, "expertise":
         "Solid TA trader of crypto and bitcoin"},
        {"uid": uid, "site": "twitter", "account": "InsiderBuySS", "ranking": 2, "contra": False, "expertise":
         "Solid TA trader of crypto and bitcoin"},
        {"uid": uid, "site": "twitter", "account": "CryptoBadr", "ranking": 5, "contra": False, "expertise":
         "Solid TA trader of crypto and bitcoin"},
        {"uid": uid, "site": "twitter", "account": "mBTCPiz", "ranking": 5, "contra": False, "expertise":
         "Solid TA trader of crypto and bitcoin"},
        {"uid": uid, "site": "twitter", "account": "AngeloBTC", "ranking": 5, "contra": False, "expertise":
         "Solid TA trader of crypto and bitcoin"},
    ]

    for profile in profiles:
        crawler.upsert_profile(profile=profile)


def install_crawler_analyzers():
    """
    install analyzers
    """
    analyzers = [{"title": "BTC/USD Longs 1",
                  "prompt": """Automatically analyze the sentiment of the
                           following post with a focus on its implications
                           for long positions in BTC/USD trading.
                           Determine whether the sentiment suggests a
                           bullish outlook for Bitcoin by considering the
                           presence and context of keywords such as
                           'inflows,' 'outflows,' 'breakout,' 'breakdown,'
                           'ATH' (all-time high), and other indicators of
                           positive momentum or significant developments in
                           the Bitcoin market. Evaluate the post for
                           explicit and implicit messages that could
                           influence investor confidence positively towards
                           taking a long position in Bitcoin. Summarize the
                           sentiment as bullish, neutral, or bearish, and
                           highlight any specific phrases or terms in the post
                           that significantly contribute to this sentiment
                           assessment"""},
                 {"title": "BTC/USD Shorts 1",
                  "prompt": """Automatically analyze the sentiment of the
                          following post with a focus on its implications for short
                          positions in BTC/USD trading. Determine whether the sentiment
                          suggests a bearish outlook for Bitcoin by examining the
                          presence and context of keywords such as 'sell-off,'
                          'downturn,' 'correction,' 'volatility,' 'bear market,'
                          'regulatory concerns,' and other indicators of negative
                          momentum or significant risks in the Bitcoin market. Evaluate
                          the post for explicit and implicit messages that could
                          influence investor confidence negatively towards taking a
                          short position in Bitcoin. Summarize the sentiment as
                          bullish, neutral, or bearish, specifically noting any
                          phrases or terms in the post that critically contribute to
                          this sentiment assessment."""},
                 {"title": "ETH/USD Longs 1",
                  "prompt": """Automatically analyze the sentiment of the
                            following post with regard to its implications for
                            long positions in ETH/USD trading. Ascertain whether
                            the sentiment indicates a bullish outlook for Ethereum
                            by focusing on the presence and context of keywords such
                            as 'scaling solutions,' 'DeFi growth,' 'NFT boom,' 
                            'network upgrade,' 'EIP implementation,' 'staking rewards,'
                            and other signals of positive momentum or significant
                            advancements in the Ethereum market. Investigate
                            the post for both explicit and implicit messages
                            that might boost investor confidence positively
                            towards taking a long position in Ethereum.
                            Conclude the sentiment as bullish, neutral, or bearish,
                            while pinpointing any specific phrases or elements
                            in the post that substantially influence this
                            sentiment evaluation."""},
                 {"title": "ETH/USD Shorts 1",
                  "prompt": """Automatically analyze the sentiment of the
                            following post with specific attention to its
                            implications for short positions in ETH/USD trading.
                            Identify whether the sentiment suggests a bearish
                            outlook for Ethereum by focusing on the presence and
                            context of keywords such as 'overvalued,' 
                            'technical resistance,' 'regulatory scrutiny,'
                            'network congestion,' 'gas fees,' 'security issues,'
                            and other signals of potential challenges or negative
                            momentum in the Ethereum market. Assess both explicit
                            and implicit messages that might lead investors to
                            consider a short position in Ethereum due to perceived
                            risks or downward trends. Provide a sentiment summary
                            categorized as bullish, neutral, or bearish, and underline
                            particular phrases or elements within the post that
                            significantly influence this sentiment analysis."""
                            }]
    crawler = CrawlerManager()
    for alyz in analyzers:
        analyzer = CrawlerAnalyzerStruct(title=alyz['title'], prompt=alyz['prompt'])
        aid = crawler.add_analyzer(analyzer=analyzer)


def add_analyzer_follows():
    crawler = CrawlerManager()
    profiles = crawler.get_profiles()
    for profile in profiles:
        crawler.add_follows_analyzer(uid=1, fid=profile.fid, aid=1, account=profile.account)
