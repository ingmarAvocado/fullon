from libs.settings_config import fullon_settings_loader
from libs import exchange, log, settings
from libs.bot import Bot
from libs.database_ohlcv import start as startohlcv, stop as stopohlcv, Database as database_ohlcv
from libs.database import start as startdb, stop as stopdb, Database
import ipdb
from multiprocessing import Event
settings.LOGLEVEL = 'logging.DEBUG'
from run.install_manager import InstallManager
logger = log.fullon_logger(__name__)
startohlcv()
startdb()
exchange.start_all()
signal = Event()

#ins = InstallManager()
#ins.install_strategies()


bot1 = Bot(1)
bot1.dry_run = True
print("starting")
try:
    bot1.run_loop(test=False, stop_signal=signal)
except KeyboardInterrupt:
    print("hola")

print("minitest complete")
exchange.stop_all()
stopdb()
stopohlcv()
print("Script over")
