from libs import settings
from libs.settings_config import fullon_settings_loader
from libs import exchange, log, cache
from libs.bot_launcher import start, stop
from libs.database_ohlcv import start as startohlcv, stop as stopohlcv, Database as DatabaseOhlcv
from libs.database import start as startdb, stop as stopdb, Database
from run import rpcdaemon_manager as rpc
from run.process_manager import ProcessManager
from run.crawler_manager import CrawlerManager
from libs.crawler.llm_engines.openai.engine import Engine
import pytest
import json
import xmlrpc

settings.LOG_LEVEL = "logging.INFO"


startohlcv()
startdb()

#crawler = CrawlerManager()

#crawler._load_module_for_site(site='twitter')
#crawler._fetch_posts(site='twitter', llm_scores=True)
'''
from libs.simulator_prompts import Prompts
prompts = Prompts()
numbots = prompts._get_bot_dict()
prompts.BOT = numbots[1]
strats = prompts._get_str_params()
'''
stopdb()
stopohlcv()

details = {'3': {'bot_id': 3, 'dry_run': True, 'active': False, 'uid': 1, 'str_id': 3, 'strategy': 'trading101', 'take_profit': None, 'stop_loss': None, 'trailing_stop': None, 'timeout': None, 'leverage': 2.0, 'size_pct': 10.0, 'size': None, 'size_currency': 'USD', 'pre_load_bars': 100, 'feeds': {'0': {'str_id': 3, 'symbol': 'BTC/USD', 'exchange': 'kraken', 'compression': 1, 'period': 'Ticks', 'feed_id': 7}, '3': {'str_id': 3, 'symbol': 'BTC/USD', 'exchange': 'kraken', 'compression': 120, 'period': 'Minutes', 'feed_id': 8}}, 'extended': {'str_id': '3', 'sma1': '4'}}, '4': {'bot_id': 3, 'dry_run': True, 'active': False, 'uid': 1, 'str_id': 4, 'strategy': 'trading101', 'take_profit': None, 'stop_loss': None, 'trailing_stop': None, 'timeout': None, 'leverage': 5.0, 'size_pct': 15.0, 'size': None, 'size_currency': 'USD', 'pre_load_bars': 100, 'feeds': {'1': {'str_id': 4, 'symbol': 'ETH/USD', 'exchange': 'kraken', 'compression': 1, 'period': 'Ticks', 'feed_id': 9}, '2': {'str_id': 4, 'symbol': 'ETH/USD', 'exchange': 'kraken', 'compression': 10, 'period': 'Minutes', 'feed_id': 10}}, 'extended': {'str_id': '4', 'sma1': '45'}}}
details = json.dumps(details)

client = xmlrpc.client.ServerProxy(f"http://{settings.XMLRPC_HOST}:{settings.XMLRPC_PORT}", allow_none=True)
if client:
    details = client.bots('edit', {'bot_id': '3', 'strats': details})
    print(details)


#engine = Engine()
#print(engine._analyze_image(file='1767873893115576609.jpg'))

#post = 'I think BTC is ok, but watch out looks oversold'

#engine.score_post(post)

