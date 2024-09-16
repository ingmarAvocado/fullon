from libs import settings
from libs.settings_config import fullon_settings_loader
from libs import exchange, log, cache
from libs.bot_launcher import start, stop
from libs.database_ohlcv import start as startohlcv, stop as stopohlcv, Database as DatabaseOhlcv2
from libs.database import start as startdb, stop as stopdb, Database
from run import rpcdaemon_manager as rpc
from run.process_manager import ProcessManager
from run.crawler_manager import CrawlerManager
from run.tick_manager import TickManager
from run.ohlcv_manager import OhlcvManager
import run.rpcdaemon_manager as rpc
from libs.crawler.llm_engines.openai.engine import Engine
from libs.exchange import start_all, stop_all, Exchange as Exchange
from libs.exchange_methods import ExchangeMethods as Exchange2
from libs.models.ohlcv_model import Database as  DatabaseOhlcv
import arrow
import time
from run.install_manager import InstallManager
import json
from threading import Thread, Event
import xmlrpc
import sys
from run.account_manager import AccountManager
from run.trade_manager import TradeManager
import ipdb

settings.LOG_LEVEL = "logging.ERROR"

event = Event()
startohlcv()
startdb()
start_all()

params = {'exchange': 'kraken'}

with cache.Cache() as store:
    user_ex = store.get_exchange(ex_id=1)

exch = Exchange2(user_ex.cat_name, user_ex)
exch.connect_websocket()

'''
stop_event = Event()
server_thread = Thread(target=rpc.rpc_server, args=[stop_event,], daemon=True)
server_thread.start()
time.sleep(1)


client = xmlrpc.client.ServerProxy(f"http://{settings.XMLRPC_HOST}:{settings.XMLRPC_PORT}", allow_none=True)
client.services('services', 'start')
'''
# params = {'exchange': 'kraken'}
# rpc.tickers('start', params)
# client.ohlcv('start', params)
#exch.stop_ticker_socket()
'''
for i in range(200):
    sys.stdout.write(f"\r{i} ")
    sys.stdout.flush()
    time.sleep(1)


pm = ProcessManager()
pm.check_services(stop_event=event, test=True)
input("finish? ")
'''
#rpc.restart_exchange('kraken')
#time.sleep(20)


#since = arrow.utcnow().shift(minutes=-3).timestamp()
#symbol = "XBTUSD"
#trades = exch.fetch_trades(symbol=symbol, since=since)
crawl = CrawlerManager()
crawl._fetch_posts(site='twitter')
#crawl._llm_scores(engine='')

#stop_event.set()
stop_all()
stopdb()
stopohlcv()
print("bye")
