from libs import settings
from libs.settings_config import fullon_settings_loader
settings.LOG_LEVEL = "logging.INFO"
from libs import exchange, log
from libs.bot_launcher import start, stop
from libs.database_ohlcv import start as startohlcv, stop as stopohlcv, Database as DatabaseOhlcv
from libs.database import start as startdb, stop as stopdb, Database
from run import rpcdaemon_manager as rpc
from run.crawler_manager import CrawlerManager
from libs.crawler.llm_engines.openai import install
import pytest
#startohlcv()
#startdb()
'''
start()
from libs.bot_launcher import Launcher
launcher = Launcher()
res = launcher.start(1, no_check=True)
'''

#crawler = CrawlerManager()
#crawler._load_module_for_site(site='twitter')
#crawler._fetch_posts(site='twitter')

#stopdb()
#stopohlcv()

engine = install.Engine()

engine.score_posts([])

