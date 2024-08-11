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

settings.LOG_LEVEL = "logging.INFO"

since = arrow.utcnow().shift(days=-1).timestamp()
event = Event()


start_all()
startohlcv()
startdb()
params = {'exchange': 'kraken'}

with cache.Cache() as store:
    user_ex = store.get_exchange(ex_id=1)

exch = Exchange(user_ex.cat_name, user_ex)


stop_event = Event()
server_thread = Thread(target=rpc.rpc_server, args=[stop_event,], daemon=True)
server_thread.start()
time.sleep(1)


client = xmlrpc.client.ServerProxy(f"http://{settings.XMLRPC_HOST}:{settings.XMLRPC_PORT}", allow_none=True)
params = {'exchange': 'kraken'}
#rpc.tickers('start', params)
client.ohlcv('start', params)

#exch.start_trade_socket(tickers=['BTC/USD'])
#exch.start_trade_socket(tickers=['ETH/USD'])
#exch.start_trade_socket(tickers=['SOL/USD'])
#exch.start_trade_socket()
#del(exch)

#tm = TickManager()n
#tm.run_loop_one_exchange(exchange_name=user_ex.cat_name)
time.sleep(60)
pm = ProcessManager()
#print(pm.check_services(stop_event=event, test=True))
#res = pm.check_ohlcv()
#print(res)
#input("continue???)")
exch.stop_trade_socket()
print("closed")

for i in range(180):
    sys.stdout.write('.')
    sys.stdout.flush()
    time.sleep(1)
print("now we check should fail and restart")
res = pm.check_ohlcv()
print(res)
pm.check_services(stop_event=event, test=True)
time.sleep(20)
print("now should be ok")
input("tst")
pm.check_services(stop_event=event, test=True)

#rpc.tickers('stop', params)
rpc.ohlcv('stop', params)
print("stopping")
time.sleep(3)

#rpc.restart_exchange('kraken')
#time.sleep(20)


#since = arrow.utcnow().shift(minutes=-3).timestamp()
#symbol = "XBTUSD"
#trades = exch.fetch_trades(symbol=symbol, since=since)
#crawl = CrawlerManager()
#crawl._fetch_posts(site='twitter')
#crawl._llm_scores(engine='')

#stop_event.set()
stop_all()
stopdb()
stopohlcv()
print("bye")
time.sleep(2)

