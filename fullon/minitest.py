from libs.settings_config import fullon_settings_loader
from libs import exchange, log, settings
from libs.bot import Bot
from libs.database_ohlcv import start as startohlcv, stop as stopohlcv, Database as database_ohlcv
from libs.database import start as startdb, stop as stopdb, Database
import ipdb
from multiprocessing import Event
settings.LOGLEVEL = 'logging.DEBUG'
#from run.install_manager import InstallManager
logger = log.fullon_logger(__name__)
startohlcv()
startdb()
exchange.start_all()
signal = Event()
bot1 = Bot(8)
bot1.dry_run = False
print("starting")
try:
    bot1.run_loop(test=True, stop_signal=signal)
except KeyboardInterrupt:
    print("hola")
#bot1
'''
manager = BotManager()
manager.start_bot(4)
time.sleep(4)
print("next one")
manager.start_bot(7)
#print(manager.is_running(3))
#ipdb.set_trace()
#manager.start(3)
#res = manager.bots_list()
#manager.bots_live_list()
'''
print("minitest complete")

exchange.stop_all()
stopdb()
stopohlcv()
print("Script over")
