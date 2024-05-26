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


#startohlcv()
startdb()

with Database() as dbase:
    list = dbase.get_crawling_list2(site='twitter')
print(list)
stopdb()
#stopohlcv()


