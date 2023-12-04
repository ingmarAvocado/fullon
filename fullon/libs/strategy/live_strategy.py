"""
description
"""
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals)

from typing import Optional
import arrow
import backtrader as bt
from libs import log, cache
from libs.strategy import drylive_strategy as strategy
from libs.database import Database
from libs.cache import Cache
from time import sleep

logger = log.fullon_logger(__name__)

_SLEEP_IF_BLOCKED = 5  # seconds


class Strategy(strategy.Strategy):
    """
    A trading strategy that uses a fixed number of bars for data feeds.

    Attributes:
        verbose (bool): Whether to print out detailed information.
        loop (int): The number of times the strategy has looped.
    """

    verbose: bool = False
    loop: int = 0

    def nextstart(self):
        """This only runs once... before init... before pre_next()...
        before next() but only once"""
        #super().nextstart()
        if self.nextstart_done is False:
            self._while_bot_blocked()
            self._state_variables()
            self._save_status()
            """
            This will cancel all orders  without regards if its on a different exchange or not... just all of them
            this might have to be adjusted
            """
            #aqui tengo que mandar llamar un self.broker.cancel_all"
            '''
            self.dbase.update_orders_status(
                bot_id=self.helper.id,
                status='Cancel',
                restrict='Open')
            self.dbase.update_orders_status(
                bot_id=self.helper.id, status='Cancel', restrict='New')
            self._load_bot_vars()
            '''
        self.nextstart_done = True
        self.set_indicators_df()
        try:
            self.local_nextstart()  # How to check whether this exists or not
        except AttributeError:
            pass

    def next(self) -> None:
        """
        The main method that runs on every iteration of the strategy.
        """
        # Check if data feed is live
        if not self.datas[0].islive():
            self.set_indicators_df()
            return
        self.status = "looping"
        self._while_bot_blocked()
        self._validate_block()
        self._stop_signal()
        if not self._validate_orders():
            return self._end_next()
        self._set_indicators()
        self._save_status()
        # Print position variables if verbose is enabled
        if self.verbose:
            self._print_position_variables(0)
        # If there are no positions, call local_next, else call risk_management
        if self.anypos == 0:
            self.local_next()
        else:
            """
            here i should some how check ocassionally if my long is indeed mine?
            """
            self.risk_management()
            self._end_next()

    def _while_bot_blocked(self):
        """
        Checks if a bot is blocked, if it is, it wont proceed
        """
        # self._sync_exchange_status()
        block_count = 0
        if self._bot_is_blocked(bot_id=self.helper.id):
            logger.warning("Exchange and symbol for bot %s is blocked", self.helper.id)
            sleep(1)
        while self._bot_is_blocked(bot_id=self.helper.id):
            """
            here we loop for some time and then hard recheck after a while
            """
            sleep(_SLEEP_IF_BLOCKED)
            block_count += 1
            if block_count > 30:
                logger.warning("Exchange and symbol for bot %s is blocked", self.helper.id)
                # self._sync_exchange_status()
                block_count = 0

    def save_log(self, order: bt.Order, num: int) -> None:
        """ description """
        datas = self.datas[num]
        if datas.feed.trading:
            with Database() as dbase:
                dbase.save_bot_log(bot_id=self.helper.id,
                                   ex_id=datas.feed.ex_id,
                                   symbol=datas.symbol,
                                   position=str(order.size),
                                   message=order.Status[order.status],
                                   feed_num=num)
            with Cache() as store:
                res = store.block_exchange(ex_id=datas.feed.ex_id,
                                           symbol=datas.symbol,
                                           bot_id=0)
        return None

    def _bot_is_blocked(self, bot_id) -> bool:
        """
        checks if one exchange and symbol are blocked, if they are return True
        """
        res = False
        with cache.Cache() as store:
            for _, datas in enumerate(self.datas):
                if datas.feed.trading:
                    blocked_by = store.is_blocked(ex_id=datas.feed.ex_id,
                                                  symbol=datas.symbol)
                    if blocked_by:
                        if int(blocked_by) != bot_id:
                            return True
        return res

    def kill_orders(self):
        """ description """
        for num in range(0, len(self.datas)):
            self.datas[num].broker.cancel_all_orders(self.getdatas[0].symbol)

    def _get_last_trade(self, datas_num):
        datas = self.datas[datas_num]
        last_trade = self.dbase.get_trades(
                ex_id=datas.feed.ex_id, symbol=datas.symbol, last=True)
        return last_trade[0]

    def notify_trade(self, trade: bt.Trade):
        print("hice un trade: ", trade)
        exit()
        pass

    def get_value(self, num: int):
        """
        returns how much value there is in an exchange
        """
        return self.broker.getvalue()

    def entry(self, datas_num: int, price: Optional[float] = None):
        """
        Compute the position size for trading, considering either a set position size,
        a percentage of available cash, or defaulting to the latest tick price.

        Args:
            datas_num (int): Index for data feed.
            price (Optional[float]): Price at which trading is considered. Defaults to the latest tick price.

        Returns:
            float: Computed position size for the trade.

        Note:
            This method uses `self.get_value(pair)` to ensure accuracy across varying collateral currencies.
        """
        # Defaulting to tick data if price not provided
        if not price:
            price = self.tick[datas_num]
        symbol = self.datas[datas_num].symbol
        # If the base currency isn't USD
        if not symbol.endswith("/USD"):
            base_currency = symbol.split("/")[1]
            conversion_rate = self.broker.get_symbol_value(symbol=f"{base_currency}/USD")
            if not conversion_rate:
                volume = 0
        else:
            conversion_rate = 1
        if self.size[datas_num]:
            usd_equivalent = self.size[datas_num] / conversion_rate  # self.p.leverage
            volume = usd_equivalent / price
        else:
            #now this is wrong, review later
            usd_equivalent = (self.cash[datas_num] * (self.p.size_pct / 100)) / conversion_rate #self.p.leverage
            volume = usd_equivalent / price
        return volume

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
        with Cache() as store:
            if not store.is_opening_position(ex_id=self.datas[datas_num].feed.ex_id,
                                             symbol=self.datas[datas_num].feed.symbol):
                store.mark_opening_position(ex_id=self.datas[datas_num].feed.ex_id,
                                            symbol=self.datas[datas_num].feed.symbol,
                                            bot_id=self.helper.id)
            else:
                logger.warning("Position opening is blocked as another bot is already opening it.")
                return False
        res = super().open_pos(datas_num=datas_num, otype=otype)
        now = arrow.utcnow()
        max_iterations = 50  # Set a maximum number of iterations to prevent infinite loop
        iteration_count = 0

        with Cache() as store:
            if res:
                while iteration_count < max_iterations:
                    status = store.get_process(tipe="bot_status_service", key='service')
                    if 'timestamp' in status and arrow.get(status['timestamp']) > now:
                        break
                    sleep(0.2)
                    iteration_count += 1

                if iteration_count >= max_iterations:
                    logger.error("Timeout reached while waiting for bot status update.")
                    self.close_pos()  # Close position if stuck in an infinite loop
                    self.cerebro.runstop()
                    return False

            store.unmark_opening_position(ex_id=self.datas[datas_num].feed.ex_id,
                                          symbol=self.datas[datas_num].feed.symbol)

        return res

    def _validate_block(self):
        """
        Validates a opening_position for all trading feeds

        Args:
            datas_num (int, optional): The index of the data feed. Defaults to 0.
            otype (Optional[str], optional): The type of operation. Defaults to None.

        Returns:
            Optional[bool]: Returns True if the operation was successful,
                            None if the operation was not successful.
        """
        for _, datas in enumerate(self.datas):
            if datas.feed.trading:
                with Cache() as store:
                    if store.is_opening_position(ex_id=datas.feed.ex_id,
                                                 symbol=datas.feed.symbol):
                        store.unmark_opening_position(ex_id=datas.feed.ex_id,
                                                      symbol=datas.feed.symbol)
