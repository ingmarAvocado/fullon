"""
Describe strategy
"""
import arrow
from typing import Optional
from libs.strategy import loader
from libs import log
import pandas
import pandas_ta as ta


logger = log.fullon_logger(__name__)

strat = loader.strategy


class Strategy(strat.Strategy):
    """description"""

    params = (
        ('sma_period', 20),  # Period for the simple moving average
        ('pre_load_bars', 20),
        ('balancing_days', 1),
        ('feeds', 2)
    )

    def local_init(self):
        """Initial setup for the strategy, including setting up required bars for the moving average calculation."""
        self.next_open: arrow.Arrow
        self.verbose = False
        self.order_cmd = "spread"
        self.trades_data = []
        # Maintain detailed positions for long and short

    def local_next(self):
        """ description """
        if self.entry_signal[0]:
            if self.curtime[0] >= self.next_open:
                self.open_pos(0)

    def set_indicators_df(self):
        if not self.indicators_df.empty:
            if self.indicators_df.index[-1] == self.str_feed[1].dataframe.index[-1]:
                return
        self.indicators_df = self.str_feed[1].dataframe[['close']].copy()
        self.indicators_df['sma'] = self.indicators_df['close'].rolling(
            window=int(self.p.sma_period)).mean()
        self._set_signals()
        next_date = arrow.get(self.indicators_df.index[-1]).shift(minutes=self.str_feed[1].bar_size_minutes)
        self.indicators_df.loc[next_date.format('YYYY-MM-DD HH:mm:ss')] = None
        new_index = self.indicators_df.index.to_series().shift(-1).ffill().astype('datetime64[ns]')
        self.indicators_df.index = new_index
        self.indicators_df = self.indicators_df.dropna()

    def _set_signals(self):
        # Create new columns for entry and exit signals, initialized to False
        self.indicators_df['entry'] = False
        self.indicators_df['exit'] = False
        # Define conditions for long entry and exit signals
        close_above_sma = self.indicators_df['close'].shift(1) > self.indicators_df['sma']
        close_below_sma = self.indicators_df['close'].shift(1) < self.indicators_df['sma']

        # Update the DataFrame with the entry and exit signals based on the conditions
        self.indicators_df.loc[close_above_sma, 'entry'] = True
        self.indicators_df.loc[close_below_sma, 'exit'] = True

    def set_indicators(self):
        current_time = self.curtime[1].format('YYYY-MM-DD HH:mm:ss')
        fields = ['entry', 'exit', 'sma']
        self._this_indicators(current_time=current_time, fields=fields)

    def local_nextstart(self):
        """ Only runs once, before local_next"""
        self.next_open = self.curtime[0]

    def get_entry_signal(self):
        """
        blah
        """
        try:
            if self.curtime[0] >= self.next_open:
                self.entry_signal[0] = ""
                if self.indicators.entry:
                    self.entry_signal[0] = "Buy"
        except KeyError:
            pass

    def risk_management(self):
        """
        Handle risk management for the strategy.
        This function checks for stop loss and take profit conditions,
        and closes the position if either of them are met.

        only works when there is a position, runs every tick
        """
        # Check for stop loss
        res = self.check_exit()
        #print(">>>", self.p.str_id, self.pos[0], self.curtime[0], self.balancer)
        if not res:
            if self.indicators.exit:
                self.close_position(feed=0, reason="strategy")  # Close position logic
                res = True
            else:
                """
                balancer logic
                """
                minute = int(self.curtime[0].format('m'))
                match minute:
                    case 0:
                        target = self._get_balancing_target()
                        if target < 0:
                            self.change_position(datas_num=0, size=target)
                            self.local_next_event()
                    case 1:
                        target = self._get_balancing_target()
                        if target > 0:
                            self.change_position(datas_num=0, size=target)
                        self.local_next_event()
        if res:
            self.local_next_event()

    def _get_balancing_target(self):
        """
        """
        fee_pct = self.broker.getcommissioninfo(self.datas[0]).p.commission
        buffered_size_pct = round(self.p.size_pct / (1 + fee_pct), 2)
        total_funds = self._get_true_funds()
        pre_target = total_funds * (buffered_size_pct/100)
        pos_value = self.pos[0]*self.tick[0]
        target = pre_target - pos_value
        target = round(target / (1 + fee_pct), 0)
        if abs(target) > self.cash[0] + 5:
            return 0
        if abs(target) < 30:
            return 0
        return target/self.tick[0]

    def _get_true_funds(self):
        value = 0
        for data in self.datas:
            pos = self.getposition(data)
            value += pos.size * self.tick[0]
        for num in self.cash:
            value += self.cash[num]
        return value

    def event_out(self):
        """
        """
        return self.time_to_next_bar(feed=1).shift(days=self.p.balancing_days-1)

