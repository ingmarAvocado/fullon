from libs.settings_config import fullon_settings_loader
from libs import settings
from libs import exchange, exchange_methods, log,  strategy, settings
from libs import cache
from libs.bot import Bot
from libs.settings_config import fullon_settings_loader
from libs.btrader.fullonsimfeed import FullonSimFeed
from libs.btrader.fullonresampler import FullonFeedResampler
from run import user_manager
import backtrader as bt
import arrow
import importlib
import pytest
import time
from libs.exchange import start_all, stop_all
from libs.database_ohlcv import start as startohlcv, stop as stopohlcv, Database as database_ohlcv
from libs.database import start as startdb, stop as stopdb, Database
from run.system_manager import AccountManager
from run.system_manager import OhlcvManager
from run.system_manager import TickManager

from run.bot_manager import BotManager
from run.system_manager import BotStatusManager
#from run.system_manager import OhlcvManager
from run.system_manager import TradeManager
#from libs.calculations import TradeCalculator
from libs.order_methods import OrderMethods
from run import rpcdaemon_manager as rpc
from libs import cache
from libs.structs.order_struct import OrderStruct
import ipdb
settings.LOGLEVEL = 'logging.DEBUG'
from run.install_manager import InstallManager
from multiprocessing import Event


startohlcv()
startdb()
exchange.start_all()

logger = log.fullon_logger(__name__)
dbase = Database()
store = cache.Cache()

#manager = InstallManager()
#manager.install_strategies()


#UID = ''
user = user_manager.UserManager()
UID = user.get_user_id(mail='admin@fullon')
exch = dbase.get_exchange(user_id=UID)[0]


orderBuy = {"ex_id": exch.ex_id,
            "cat_ex_id": exch.cat_ex_id,
            "exchange": exch.cat_name,
            "symbol": 'BTC/USD',
            "order_type": "market",
            "volume": 0.00013423432342,
            "price": 57600,
            "plimit": None,
            "side": "Buy",
            "reason": 'signal',
            "command": "spread",
            "subcommand": "60:minutes",
            "leverage": "2.0",
            "bot_id": "00000000-0000-0000-0000-000000000002"}
orderBuy = OrderStruct.from_dict(orderBuy)

orderSell = {"ex_id": exch.ex_id,
             "cat_ex_id": exch.cat_ex_id,
             "exchange": exch.cat_name,
             "symbol": 'BTC/USD',
             "order_type": "market",
             "volume": 0.00013423432342,
             "price": 58000,
             "plimit": None,
             "side": "Sell",
             "reason": 'signal',
             "command": "spread",
             "leverage": "2.0",
             "reduce_only": True,
             "bot_id": "00000000-0000-0000-0000-000000000002"}
orderSell = OrderStruct.from_dict(orderSell)


orderStopLoss = {"ex_id": exch.ex_id,
                 "cat_ex_id": exch.cat_ex_id,
                 "exchange": exch.cat_name,
                 "symbol": 'BTC/USD',
                 "order_type": "stop-loss",
                 "volume": 0.0001,
                 "price": 57600,
                 "plimit": None,
                 "side": "Sell",
                 "reason": 'signal',
                 "command": "",
                 "leverage": 3,
                 "reduce_only": True,
                 "bot_id": "00000000-0000-0000-0000-000000000002"}
orderStopLoss = OrderStruct.from_dict(orderStopLoss)

# 2020-09-18 01:19:14.832102
#exch = exchange_methods.ExchangeMethods(exchange='kraken', params=exch)
#exch.create_order(order=orderBuy)
#exit()
#exch.minimum_order_cost(symbol='ETH/USDT')
#exch.quote_symbol(symbol='ETH/USDT')
#exch = exchange.Exchange(exchange='kraken', params=exch)
#exch.connect_websocket()
#print("m2")
#exch.socket_connected()
#print("m")
#exch.socket_connected()
#time.sleep(365)
#print("bye")
#exch.my_open_orders_socket()
#print(exch.cancel_order(oid=oid))
#print("Aqui nueva orden")
#orderBuy.order_type = "market"
#oid = exch.create_order(order=orderBuy)
#oid = exch.create_order(order=orderSell)
#print(exch.cancel_order(oid=oid))
#time.sleep(1)
#del exch
ohlcv = OhlcvManager()
ohlcv.run_ohlcv_loop(symbol='BTC/USD', exchange='bitmex')
#ohlcv.run_loop()
#ohlcv.stop_all()
#exch.get_positions()
#exch.connect_websocket()
#exch.socket_con0nected()
#del exch
#t = TickManager()
#t.run_loop()
time.sleep(60000)
#am = AccountManager()
#am.run_account_loop()
#time.sleep(150000000)
#print("\nplacing buy: \n")
#_order = om._can_place_order(order=orderBuy)
#_order = om.new_order(order=orderBuy)
#print(_order.ex_order_id, " processed")
#print("\nplacing stopbuy: \n")
#_order = om.new_order(order=orderStopLoss)
#print(f"\nabout to cancel stoploss {_order.order_id}: \n")
#om.cancel_order(oid=_order.order_id, ex_id=_order.ex_id)
#print("\nabout to sell: \n")
#_order = om.new_order(order=orderSell)
#print(_order.ex_order_id, " processed")
#del om
#print(oid)
#time.sleep(100000)
#print("turning off")

'''
bmanager = BotStatusManager()
bmanager.run_loop()

bot1 = Bot(2)
bot1.dry_run = False
print("starting")
try:
    signal = Event()
    bot1.run_loop(test=True, stop_signal=signal)
except KeyboardInterrupt:
    print("Keyboard")
'''

try:
    am.stop_all()
    del am
except:
    pass
try:
    t.stop_all()
    del t
except:
    pass
try:
    ohlcv.stop_all()
    del ohlcv
except:
    pass
exchange.stop_all()
stopdb()
stopohlcv()
print("Script over")
