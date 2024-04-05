"""
This module contains the implementation of a custom Backtrader Strategy
class that extends a base strategy class provided by the same library.
The custom class provides additional functionality for managing a trading
simulation, including methods for performing risk management, closing
positions, and syncing the current time for multiple data feeds.
"""
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals)

from libs import log
from libs.strategy import backtest_strategy as strategy
import arrow
from backtrader import TimeFrame
import pandas
from typing import Optional


logger = log.fullon_logger(__name__)


class Strategy(strategy.Strategy):
    """
    This class represents a trading strategy.

    Attributes:
    - block_next_loop (bool): A flag indicating whether
      to block the next iteration of the next() method.
    - _last_close (bool): A flag indicating whether the last trade was closed.
    """

    loop = 0
    block_next_loop = False
    _last_close = False

    def nextstart(self):
        """prepare the startegy"""
        super().nextstart()
        for feed in range(0, len(self.datas)):
            self.datas[feed].trailing_stop = self.p.stop_loss

    def next(self):
        """
        This method is called on each iteration of the simulation.
        It updates the strategy and determines
        the next course of action based on whether
        there is an existing position or not.
        """
        self.loop += 1
        self._set_indicators()

        # if self.verbose:
        #    self._print_position_variables(0)

        if self.block_next_loop:
            self.local_next_event()
            self.block_next_loop = False
            return

        if not self._next_simul_check():
            return

        if self.anypos == 0:
            self.order_placed = False
            self.local_next()
            if not self.order_placed:
                self.next_event_no_pos()
        else:
            filter_date = pandas.to_datetime(self.curtime[0].format('YYYY-MM-DD HH:mm:ss'))
            self.indicators_df = self.indicators_df[self.indicators_df.index > filter_date]
            self._check_end_simul()
            self.risk_management()
            self._end_next()

    def update_trade_vars(self, feed: int = 0) -> None:
        """
        Update the dynamic trade variables (trailing_stop) for a specific feed.

        Args:
            feed (int, optional): The index of the feed for which trade variables
                                  are updated. Defaults to 0.
        """
        pass

    def _next_simul_check(self):
        """
        Check if it's time to move the simulation forward by one step.

        Returns:
        - True if it's time to move forward
        - False otherwise
        """
        feeds = len(self.datas) // 2
        # Check if the current time for each pair of feeds is in sync
        for feed in range(feeds):
            if self.curtime[feed] < self.curtime[feed + feeds]:
                return False
        return True

    def close_position(self, feed: int = 0, reason: str = "no reason",  otype=None) -> bool:
        """
        This method is used to close an open position.

        Args:
        - reason (str): The reason for closing the position.
        - feed (int): The index of the data feed.
        - otype: Order type
        """
        super().close_position(feed=feed, reason=reason, otype=otype)
        self.datas[feed].just_closed_trade = True
        self.datas[feed].pos = 0
        return True

    def _check_end_simul(self) -> bool:
        """
        Checks wether this is last loop and if it is, it closes positions
        """
        if self.curtime[0] >= self.last_trading_date:
            for pos_num in range(0, len(self.datas)):
                try:
                    if self.pos[pos_num]:
                        self.close_position(feed=pos_num, reason="loop end")
                except KeyError:
                    pass
            return True
        return False

    def reset_any_pos(self):
        """
        Reset the `anypos` and `pos` attributes based on the current positions for each data feed.
        `anypos` will be set to True if any position exists, and False otherwise.
        The `pos` attribute will be set for each data feed to the size of its current position.
        """
        anypos = False
        for num, datas in enumerate(self.datas):
            position = self.getposition(datas)
            self.pos[num] = position.size
            if position.size != 0:
                anypos = True
        self.anypos = anypos

    def local_next_event(self) -> None:
        """
        This function determines the next event that should be triggered by the strategy.
        If there are any open positions, it calls the next_event_pos function,
        otherwise it calls the next_event_no_pos function.
        """
        if self.anypos:
            self.next_event_pos()
        else:
            self.next_event_no_pos()

    def next_event_no_pos(self):
        """
        This function finds the next event without position by getting the event date for
        strategy open for each feed, and then setting the event in for each data feeds.
        """
        # Define a time list with the last date

        #if self.curtime[0].timestamp() >= arrow.get('2023-06-23T19:37:00+00:00').timestamp():
        times = [self.last_trading_date]

        # Define a dictionary to store the events with their dates
        event: dict = {self.last_trading_date: 'end'}

        # Get the next strategy open event date from the strategy and append to the
        # time list and event dictionary
        t_in = self.event_in()
        if t_in:
            times.append(t_in)
            event[t_in] = "Strategy Open"

        # Sort the time list in ascending order to find the closest event
        times.sort()

        # Set the event timeout for all data feeds to the closest event
        for num, _ in enumerate(self.datas):
            self.datas[num].event_timeout = times[0]

    def next_event_pos(self) -> None:
        """
        This function is responsible for determining the next event for the position,
        whether it's a stop loss or a strategy event. It also sets the event timeout for
        both feeds to the closest event date.
        """
        # Define a time list with the last date
        times = [self.last_trading_date]

        # Define a dictionary to store the events with their dates
        event = {self.last_trading_date: 'end'}

        for num, data in enumerate(self.datas):
            if data.timeframe == TimeFrame.Ticks:
                if self.pos[num]:
                    if self.p.stop_loss:
                        stop_loss_date, price = self.datas[num].get_event_date(
                            event="stop_loss",
                            price=self.stop_loss[num],
                            cur_ts=self.curtime[0])
                        times.append(stop_loss_date)
                        event[stop_loss_date] = "stop_loss"
                    if self.p.take_profit:
                        take_profit_date, price = self.datas[num].get_event_date(
                            event="take_profit",
                            price=self.take_profit[num],
                            cur_ts=self.curtime[0])
                        times.append(take_profit_date)
                        event[take_profit_date] = "take_profit"
                    if self.p.trailing_stop:
                        trailing_date, price = self.datas[num].get_event_date(
                            event="trailing_stop",
                            price=self.stop_loss[num],
                            cur_ts=self.curtime[0])
                        if trailing_date < stop_loss_date:
                            self.stop_loss[num] = price
                        times.append(trailing_date)
                        event[trailing_date] = "trailing_stop"
        tout = self.event_out()
        if tout:
            times.append(tout)
            event[tout] = "strategy"
        # Sort the events by date and set the closest event as the next event
        times.sort()
        # Set the event timeout for both feeds to the closest event date
        for num, _ in enumerate(self.datas):
            self.datas[num].event_timeout = times[0]

    def event_in(self) -> Optional[arrow.Arrow]:  # pylint: disable=no-self-use
        '''
        Returns the date of the first of an in event occurrence by the child if there is any.
        '''
        return ""

    def event_out(self) -> Optional[arrow.Arrow]:  # pytint: disable=no-self-use
        '''
        Returns the date of the first of an out event occurrence by the child if there is any.
        '''
        return ""

    def notify_trade(self, trade):
        """
        this gets executed after a trade has finished
        """
        super().notify_trade(trade=trade)
        feed = int(trade.getdataname())
        if trade.justopened is True:
            self.datas[feed].pos = trade.size
            self.anypos = True
        else:
            self.datas[feed].pos = 0
            self.reset_any_pos()
        self.block_next_loop = True
        if self.p.take_profit:
            self.datas[feed].take_profit = self.take_profit[feed]
        if self.p.stop_loss:
            self.datas[feed].stop_loss = self.stop_loss[feed]
        if self.p.timeout:
            self.datas[feed].timeout = self.timeout[feed]
