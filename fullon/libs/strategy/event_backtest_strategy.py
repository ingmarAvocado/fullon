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

    def nextstart(self):
        """prepare the startegy"""
        self.loop = 0
        self.block_next_loop = False
        self._last_close = False
        self.curtime_prev = arrow.get('2020-01-01')
        super().nextstart()
        for feed in range(0, len(self.str_feed)):
            self.str_feed[feed].trailing_stop = self.p.stop_loss

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

        if not self._next_step_check():
            return

        #print(self.p.str_id, self.curtime, self.anypos)

        if self.anypos == 0:
            self.order_placed = False
            self.local_next()
            if not self.order_placed:
                self.next_event_no_pos()
        else:
            stime = self.str_feed[-1].bar_size_minutes
            filter_date = pandas.to_datetime(self.curtime[0].shift(minutes=-stime).format('YYYY-MM-DD HH:mm:ss'))
            self.indicators_df = self.indicators_df[self.indicators_df.index > filter_date]
            if not self._check_end_simul():
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

    def _next_step_check(self):
        """
        Check if it's time to move the simulation forward by one step.

        Returns:
        - True if it's time to move forward
        - False otherwise
        """
        feeds = len(self.str_feed) // 2
        # Check if the current time for each pair of feeds is in sync
        for feed in range(feeds):
            if self.curtime[feed] < self.curtime[feed + feeds]:
                return False
        if self.curtime_prev == self.curtime[0]:
            return False
        self.curtime_prev = self.curtime[0]
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
        self.str_feed[feed].just_closed_trade = True
        self.str_feed[feed].pos = 0
        return True

    def _check_end_simul(self) -> bool:
        """
        Checks wether this is last loop and if it is, it closes positions
        """
        if self.curtime[0] >= self.last_trading_date:
            for pos_num in range(0, len(self.str_feed)):
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
        for num, datas in enumerate(self.str_feed):
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
        for num, _ in enumerate(self.str_feed):
            self.str_feed[num].event_timeout = times[0].shift(minutes=self.str_feed[1].bar_size_minutes)
            #self.str_feed[num].event_timeout = times[0]

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

        for num, data in enumerate(self.str_feed):
            if data.timeframe == TimeFrame.Ticks:
                if self.pos[num]:
                    if self.p.stop_loss:
                        stop_loss_date, price = self.str_feed[num].get_event_date(
                            event="stop_loss",
                            price=self.stop_loss[num],
                            cur_ts=self.curtime[0])
                        times.append(stop_loss_date)
                        event[stop_loss_date] = "stop_loss"
                    if self.p.take_profit:
                        take_profit_date, price = self.str_feed[num].get_event_date(
                            event="take_profit",
                            price=self.take_profit[num],
                            cur_ts=self.curtime[0])
                        times.append(take_profit_date)
                        event[take_profit_date] = "take_profit"
                    if self.p.trailing_stop:
                        trailing_date, price = self.str_feed[num].get_event_date(
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
        for num, _ in enumerate(self.str_feed):
            self.str_feed[num].event_timeout = times[0]

    def event_in(self) -> Optional[arrow.Arrow]:
        """
        Find the date of the next buy or sell signal based on the current time.
        """
        curtime = pandas.to_datetime(self.next_open.shift(minutes=-self.str_feed[1].bar_size_minutes).format('YYYY-MM-DD HH:mm:ss'))
        try:
            # Filter based on conditions and time
            mask = (self.indicators_df['entry'] == True) & (self.indicators_df.index.date >= curtime.date())
            filtered_df = self.indicators_df[mask]
            # Check if the filtered dataframe has any rows
            if not filtered_df.empty:
                first_entry_date = filtered_df.index[0]
                return arrow.get(str(first_entry_date))
            else:
                return None
        except KeyError as error:
            if 'entry' in str(error):
                logger.error("No entry column in indicators_df")
                self.cerebro.runstop()
            else:
                raise

    def event_in2(self) -> Optional[arrow.Arrow]:
        """
        Find the date of the next buy or sell signal based on the current time.
        """
        curtime = pandas.to_datetime(self.next_open.format('YYYY-MM-DD HH:mm:ss'))
        try:
            # Filter based on conditions and time, do not change == to is
            mask = (self.indicators_df['entry'] == True) \
                    & (self.indicators_df.index >= curtime)
        except KeyError as error:
            if 'entry' in str(error):
                logger.error("No entry or exit in  indicators_df")
                self.cerebro.runstop()
            else:
                raise
        filtered_df = self.indicators_df[mask]
        # Check if the filtered dataframe has any rows
        if not filtered_df.empty:
            return arrow.get(str(filtered_df.index[0]))

    def event_out(self) -> Optional[arrow.Arrow]:
        """
        take profit and stop_loss are automatic
        """
        curtime = pandas.to_datetime(self.curtime[1].format('YYYY-MM-DD HH:mm:ss'))

        # Check the position before proceeding
        # Filter based on conditions and time for long exit
        # do not change == to is
        try:
            mask = (self.indicators_df['exit'] == True) \
            & (self.indicators_df.index >= curtime)
        except KeyError as error:
            if 'exit' in str(error):
                logger.error("No entry or exit in  indicators_df")
                self.cerebro.runstop()

        filtered_df = self.indicators_df[mask]

        # Check if the filtered dataframe has any rows
        if not filtered_df.empty:
            return arrow.get(str(filtered_df.index[0]))

    def notify_trade(self, trade):
        """
        this gets executed after a trade has finished
        """
        super().notify_trade(trade=trade)
        feed = int(trade.getdataname())
        if trade.justopened is True:
            self.str_feed[feed].pos = trade.size
            self.anypos = True
        else:
            self.str_feed[feed].pos = 0
            self.reset_any_pos()
        self.block_next_loop = True
        if self.p.take_profit:
            self.str_feed[feed].take_profit = self.take_profit[feed]
        if self.p.stop_loss:
            self.str_feed[feed].stop_loss = self.stop_loss[feed]
        if self.p.timeout:
            self.str_feed[feed].timeout = self.timeout[feed]
