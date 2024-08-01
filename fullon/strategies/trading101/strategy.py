"""
Describe strategy
"""
from libs.strategy import loader
from libs import log
import time


logger = log.fullon_logger(__name__)

strat = loader.strategy


class Strategy(strat.Strategy):
    """description"""

    params = (('sma1', 45), ('pre_load_bars', 100))

    def local_init(self):
        """description"""
        self.verbose = False
        self.order_cmd = "spread"
        self.count = 0
        return None

    def local_next(self):
        """ description """
        logger.warning(f"???new candle {self.new_bar}")
        '''
        if self.new_bar(feed=1):
            msg = f'forest long: entry_signal({self.entry_signal}), curtime= {self.curtime[0]} next_open{self.next_open}'
            logger.warning(msg)
            print(self.indicators_df.tail(10))
        '''
        time.sleep(5)
        if self.entry_signal[0]:
            self.open_pos(0)

    def get_entry_signal(self):
        #self.entry_signal[0] = random.choice(["Buy", "Sell"])
        pass

    def risk_management(self):
        time.sleep(1)
        res = self.check_exit()
