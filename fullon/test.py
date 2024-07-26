from libs import settings
from libs.settings_config import fullon_settings_loader
from libs import exchange, log, cache
from libs.bot_launcher import start, stop
from libs.database_ohlcv import start as startohlcv, stop as stopohlcv, Database as DatabaseOhlcv2
from libs.database import start as startdb, stop as stopdb, Database
from run import rpcdaemon_manager as rpc
from run.process_manager import ProcessManager
from run.crawler_manager import CrawlerManager
from libs.crawler.llm_engines.openai.engine import Engine
from libs.exchange import start_all, stop_all, Exchange
from libs.exchange_methods import ExchangeMethods as Exchange
from libs.models.ohlcv_model import Database as  DatabaseOhlcv
import arrow
import time
from run.install_manager import InstallManager




settings.LOG_LEVEL = "logging.INFO"

since = arrow.utcnow().shift(days=-1).timestamp()

start_all()
startohlcv()
startdb()

manager = InstallManager()

#manager.list_symbols_exchange(exchange='krak')

with Database() as dbase:
    params = dbase.get_exchange(exchange_name='kraken')

print(params)




#with cache.Cache() as store:
#    user_ex = store.get_exchange(ex_id=1)

#exch = Exchange(exchange='krak')

#exch = Exchange(user_ex.cat_name, user_ex)

#exch.start_ticker_socket(tickers=['BTC/USD'])
#exch.start_ticker_socket(tickers=['XBTUSD'])
#exch.start_trade_socket(tickers=['XBTUSD'])
#exch.start_candle_socket(tickers=['BTC/USD'])
#exch.start_candle_socket(tickers=['ETH/USD'])
time.sleep(60000000)



#since = arrow.utcnow().shift(minutes=-3).timestamp()
#symbol = "XBTUSD"
#trades = exch.fetch_trades(symbol=symbol, since=since)
#crawl = CrawlerManager()
#crawl._fetch_posts(site='twitter')
#crawl._llm_scores(engine='')

stop_all()
stopdb()
#stopohlcv()
print("bye")

