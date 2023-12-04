"""
Describe strategy
"""
import pandas
import decimal
import backtrader.indicators as btind
import backtrader as bt
import arrow
from typing import Union
from libs.strategy import loader
import ipdb
import random

#from libs.strategy import strategy as strat

# logger = log.setup_custom_logger('pairtrading1a', settings.STRTLOG)

strat = loader.strategy


class Strategy(strat.Strategy):
    """description"""

    params = (('sma1', 45), ('pre_load_bars', 45))

    def local_init(self):
        """description"""
        self.verbose = False
        self.count = 0
        return None

    def local_next(self):
        """ description """
        ran = random.choice(["Buy", "Sell"])
        self.entry_signal[0] = ran
        self.entry_signal[1] = ran
        self.count = 0
        self.open_pos(0)
        self.open_pos(1)

    def get_entry_signal(self):
        self.entry_signal[0] = None

    def risk_management(self):
        # return super().risk_management()
        if self.count > 10:
            self.close_position(feed=0)
            self.close_position(feed=1)
            self.count = 0
        self.count += 1
