"""
System manager
"""
from libs import log
from run import install_manager
from run import tick_manager
from run import ohlcv_manager
from run import account_manager
from run import bot_manager
from run import trade_manager
from run import process_manager
from run import user_manager
from run import bot_status_manager

logger = log.fullon_logger(__name__)


class InstallManager(install_manager.InstallManager):
    """ description """


class TickManager(tick_manager.TickManager):
    """ description """


class OhlcvManager(ohlcv_manager.OhlcvManager):
    """ description """


class AccountManager(account_manager.AccountManager):
    """ description """


class BotManager(bot_manager.BotManager):
    """ description """


class TradeManager(trade_manager.TradeManager):
    """ description """


class ProcessManager(process_manager.ProcessManager):
    """ description """


class UserManager(user_manager.UserManager):
    """ description """


class BotStatusManager(bot_status_manager.BotStatusManager):
    """ description """