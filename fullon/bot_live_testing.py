from libs.settings_config import fullon_settings_loader
from libs import settings, exchange, log
from libs.bot import Bot
from libs.database_ohlcv import start as startohlcv, stop as stopohlcv
from libs.database import start as startdb, stop as stopdb
from run.system_manager import AccountManager
from run.system_manager import OhlcvManager
from run.system_manager import TickManager
from run.system_manager import BotStatusManager
from multiprocessing import Event

settings.LOG_LEVEL = 'logging.INFO'

logger = log.fullon_logger(__name__)

startohlcv()
startdb()
exchange.start_all()

ohlcv = OhlcvManager()
ohlcv.run_loop()
t = TickManager()
t.run_loop()
am = AccountManager()
am.run_account_loop()
bmanager = BotStatusManager()
bmanager.run_loop()

bot1 = Bot(2)
bot1.dry_run = False
print("starting")
try:
    signal = Event()
    bot1.run_loop(test=False, stop_signal=signal)
except KeyboardInterrupt:
    print("Keyboard")


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
