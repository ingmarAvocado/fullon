"""
Describe strategy
"""
from libs.strategy import loader
import time

#from libs.strategy import strategy as strat

# logger = log.setup_custom_logger('pairtrading1a', settings.STRTLOG)

strat = loader.strategy


class Strategy(strat.Strategy):
    """description"""

    params = (('sma1', 45), ('pre_load_bars', 100))

    def local_init(self):
        """description"""
        self.verbose = True
        self.order_cmd = "spread"
        self.count = 0
        
        return None

    def local_next(self):
        """ description """
        self.count = 0
        import ipdb
        ipdb.set_trace()
        time.sleep(1)
        if self.entry_signal[0]:
            self.open_pos(0)

    def get_entry_signal(self):
        #self.entry_signal[0] = random.choice(["Buy", "Sell"])
        pass

    def risk_management(self):
        time.sleep(1)
        res = self.check_exit()
