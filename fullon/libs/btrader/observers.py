import backtrader as bt
import arrow
import random


class CashInterestObserver(bt.Observer):
    """
    An observer class for Backtrader that accrues interest on the unused cash
    in the brokerage account. The interest is calculated based on an annual rate and 
    applied at regular intervals, assuming a typical year has 252 trading days.

    Parameters:
    - interest_rate (float): Annual interest rate expressed as a decimal (e.g., 0.01 for 1%).

    Lines:
    - interest: Tracks the interest accrued each period.
    """

    lines = ('interest',)
    params = (
        ('interest_rate', 0.04),  # default annual interest rate of 4%
        ('main_str_id', 0)
    )

    def __init__(self):
        # Initialize any class variables here
        self.prev_cash: float
        self.prev_date: arrow.Arrow
        self.rate: float = self.params.interest_rate / 365
        self.totalinterest: float = 0

    def nextstart(self):
        self.prev_cash = self._owner.broker.get_cash()
        self.prev_date = arrow.get(bt.num2date(self.data.datetime[0]).date())

    def next(self):
        """
        Executes at each step in the backtesting loop. Interest is calculated once every year,
        assuming 252 trading days per year. The accrued interest is then added to the broker's
        cash balance.
        """
        if self._owner.p.str_id == self.p.main_str_id:
            cash = self._owner.broker.get_cash()
            curdate = arrow.get(bt.num2date(self.data.datetime[0]).date())
            difference = (curdate - self.prev_date).days
            if difference > 0:
                interest_earned = self.prev_cash * self.rate * difference
                self._owner.broker.add_cash(interest_earned)
                self.prev_date = curdate
                self.prev_cash = cash
                self.totalinterest += interest_earned
                self.lines.interest[0] = interest_earned
                current_date = bt.num2date(self.data.datetime[0]).date()
