"""
runs a test live testing
"""
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals)
from libs import log
from libs.strategy import live_strategy as strategy
from libs.structs.trade_struct import TradeStruct
from typing import Optional

logger = log.fullon_logger(__name__)


class Strategy(strategy.Strategy):
    """
    This is a derived Strategy class from the strategy.Strategy parent class.
    Additional methods or overrides can be implemented here.
    """

    verbose = False
    loop = 0
    test_side = "Buy"

    def nextstart(self):
        """This only runs once... before init... before pre_next"""
        self._state_variables()
        self.set_indicators_df()
        self.local_nextstart()
        if self.anypos != 0:
            logger.error("can't do this test with a position, please close it first")
            self.cerebro.runstop()

    def next(self) -> None:
        """
        The main method that runs on every iteration of the strategy.
        """
        # Check if data feed is live
        self._stop_signal()
        if not self.datas[0].islive():
            self.set_indicators_df()
            return
        self.status = "looping"
            # Validate orders
        if not self._validate_orders():
            return self._end_next()
        self._set_indicators()
        self._validate_block()
        #self._save_status()
        self._pairs_test()
        # If there are no positions, call local_next, else call risk_management
        if self.anypos == 0:
            for num, data in enumerate(self.datas):
                try:
                    if data.feed.trading:
                        if self.entry_signal[num]:
                            self.open_pos(num)
                except AttributeError:
                    pass
        else:
            did_exit = self.check_exit()
            if did_exit:
                logger.info("Exited my position")
        self._end_next()

    def end_next(self):
        pass

    def _pairs_test(self):
        """ description """
        print("\n\n=======================================")
        print(f"Current loop: {self.loop}\n")
        for num in range(0, len(self.datas)):
            if self.datas[num].feed.trading:
                #print(f"Current feed: {num}")
                self._test(num, side=self.test_side)
        print("========================================")
        self.loop += 1

    def _test(self, num: int, side: str = "Buy") -> None:
        """
        Tests different kinds of sell and buy operations.

        Params:
            num: int = feed number to test on
            side: str =  what type of side (buy/sell)
        """
        self.new_candle[num] = False
        self.entry_signal[num] = ""

        match self.loop:
            case 1:
                print(f"\nStarting test for feed {num}")
                if self.pos[num] != 0:
                    print("Position when i shouldn't have")
                    self.cerebro.runstop()
                print(f"\nTest simple buying 3 for rolling stop feed {num}")
                self._print_position_variables(num)
                self.new_candle[num] = False
                self.entry_signal[num] = ""
                self.p.trailing_stop = None
            case 2:
                print(f"\nCheck get_entry_signal feed {num}")
                self.entry_signal[num] = ""
                print(f"signal = {self.entry_signal[num]}")
            case 3:
                print(f"\nTest simple buying 1 feed {num}")
                self.entry_signal[num] = side
                print(f"signal = {side}")
                self.p.take_profit = 1
                self.p.stop_loss = 1
            case 4:
                self._print_position_variables(num)
                #import ipdb
                #ipdb.set_trace()
            case 5:
                print("I bought, i should have a position")
                self._print_position_variables(num)
                print("Now lets proceed to sell: ", self.take_profit)
                try:
                    self.tick[num] = self.take_profit[num] * 1.25 if self.pos[num] > 0 else self.take_profit[num] / 1.25
                    self.price_pct[num] = 10
                except (KeyError, TypeError):
                    raise ValueError("Strategy doesn't open a position, when it should have.")
            case 7:
                if self.pos[num] != 0:
                    print("Position when i shouldn't have")
                    self.cerebro.runstop()
                self._print_position_variables(num)
                self.entry_signal[num] = ""
            case 8:
                print(f"\nTest simple buying 2 feed {num} {side}")
                self.entry_signal[num] = side
            case 9:
                if self.pos[num] == 0:
                    print("No position when i should have")
                    self.cerebro.runstop()
                self._print_position_variables(num)
            case 10:
                print(f"\nTest Stop Loss feed {num}")
                self.tick[num] = self.stop_loss[num] * 1.15 if self.pos[num] > 0 else self.stop_loss[num] / 1.15
                self.price_pct[num] = -10
            case 11:
                self._print_position_variables(num)
                self.entry_signal[num] = ""
            case 12:
                if self.pos[num] != 0:
                    print("Position when i shouldn't have")
                    self.cerebro.runstop()
                print(f"\nTest simple buying 3 for rolling stop feed {num}")
                self.entry_signal[num] = side
                self.p.trailing_stop = 2
                self.p.stop_loss = 2
            case 13:
                self._print_position_variables(num)
            case 14:
                if self.pos[num] == 0:
                    print("No position when I should have")
                    self.cerebro.runstop()
                print(f"\nTest trailing_stop (stop {self.stop_loss[num]} should change in next loop)  feed {num} ")
                self.entry_signal[num] = side
                stop_loss_old = self.stop_loss[num]
                self.tick[num] = self.stop_loss[num] * 1.05 if self.pos[num] > 0 else self.stop_loss[num] / 1.05
                self.price_pct[num] = 2.2
                self.update_trade_vars(feed=num)
                if stop_loss_old == self.stop_loss[num]:
                    print("Stop loss didn't update")
                    self.cerebro.runstop()
                print("Now it should trigger a sale before next toop")

            case 15:
                self._print_position_variables(num)
            case 16:
                if self.pos[num] != 0:
                    print("Position when i shouldn't have")
                    self.cerebro.runstop()
                if self.test_side == "Buy":
                    self.test_side = "Sell"
                    self.loop = 0
            case 17:
                self.cerebro.runstop()

    def entry(self, datas_num, price=None):
        """
        Lets buy only for five USD
        """
        if self.dry_run:
            entry = strategy.strategy.Strategy.entry(
                     self=self,
                     datas_num=datas_num,
                     price=price)
        else:
            entry = self.broker.get_min_entry(datas=self.datas[datas_num])
        return entry

    def open_pos(self, datas_num: int = 0, otype: Optional[str] = None) -> Optional[bool]:
        """
        Open a position for a given feed.

        Args:
            datas_num (int, optional): The index of the data feed. Defaults to 0.
            otype (Optional[str], optional): The type of operation. Defaults to None.

        Returns:
            Optional[bool]: Returns True if the operation was successful, 
                            None if the operation was not successful.
        """
        if self.dry_run:
            return strategy.strategy.Strategy.open_pos(self=self,
                                                       datas_num=datas_num,
                                                       otype=otype)
        else:
            return super().open_pos(datas_num=datas_num,
                                    otype=otype)

    def notify_trade(self, trade):
        if self.dry_run:
            return strategy.strategy.Strategy.notify_trade(
                self=self, trade=trade)
        else:
            print("check here")
            exit()
            return super().notify_trade(trade=trade)

    def time_to_next_bar(self, feed: int) -> int:
        """
        Calculates the number of minutes until the next period/bar in the OHLCV data.

        Args:
            feed (int): The index of the feed for which time to next bar is calculated.

        Returns:
            int: Number of minutes until the next bar.
        """
        return self.curtime[feed].shift(minutes=1)

    def _get_last_trade(self, datas_num: int) -> TradeStruct:
        """
        returns last open trade
        """
        return self.open_trade[datas_num]

    def get_value(self, num: Optional[int] = None):
        """
        returns how much value there is in an exchange
        """
        if self.dry_run:
            open_trade = self._get_last_trade(num)
            if open_trade:
                value = open_trade.cost-open_trade.fee
                return self.broker.cash + value
            return self.broker.cash
        else:
            self.broker.getvalue()
