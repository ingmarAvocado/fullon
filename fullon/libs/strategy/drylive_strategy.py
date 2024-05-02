"""
description
"""
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals)
from libs import log, cache
from libs.strategy.strategy import Strategy
from libs.structs.trade_struct import TradeStruct
from libs.database import Database
from typing import Dict, Optional
import backtrader as bt
import json
import arrow
from time import sleep

logger = log.fullon_logger(__name__)


class Strategy(Strategy):
    """
    Parent Strategy class that focuses on base methods for dry but live testing
    its a child a backtrader strategy, this is not a strategy that will trade,
    but rather additional methods that can be used by a strategy that actually trades..
    """

    last_update: Optional[arrow.Arrow] = None

    def nextstart(self):
        """This only runs once... before init... before pre_next()...
        before next() but only once"""
        super().nextstart()
        if self.nextstart_done is False:
            self._state_variables()
            self.set_indicators_df()
            for n in range(0, len(self.str_feed)):
                if self.str_feed[n].feed.trading:
                    self.update_simulated_cash_account(datas_num=n)
            self._save_status()
            self.local_nextstart()
            self.nextstart_done = True
            try:
                self.local_nextstart()
            except AttributeError:
                pass
            return None

    def next(self) -> None:
        """
        The main method that runs on every iteration of the strategy.
        """
        # Check if data feed is live
        if not self.str_feed[0].islive():
            # print(arrow.get(bt.num2date(self.str_feed[0].datetime[0])))
            #self.set_indicators_df()
            return
        self.status = "looping"
        self._stop_signal()
                # Validate orders
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
            self.risk_management()
            self._end_next()

    def _stop_signal(self):
        """
        details
        """
        stop_signal = getattr(self.params, 'stop_signal', None)
        if stop_signal and stop_signal.is_set():
            msg = f"Stopping bot {self.helper.id}"
            logger.info(msg)
            self.cerebro.runstop()

    def _validate_orders(self):
        """ description """
        self.orders = self.broker.get_orders_open()
        if self.orders or self.order_placed:
            self.order_placed = False
            sleep(0.00001)
            return False
        else:
            return True

    def _bar_start_date(self, compression: int, period: str):
        """
        Gets starting date of bot data feed
        """
        bars = self.p.pre_load_bars
        period_map = {
            "ticks": 1,
            "minutes": 60,
            "days": 86400,
            "weeks": 604800,
            "months": 2629746  # assuming 30.44 days per month
        }
        seconds = compression * period_map.get(period, 0)
        return self.curtime[0].shift(seconds=-seconds*bars)

    def kill_orders(self):
        """ description """
        orders = self.broker.get_orders_open(self.str_feed[0])
        for order in orders:
            self.broker.cancel(order)

    def notify_order(self, order):
        """ description """
        if order.status == 7:
            logger.error(
                "Trying to buy more than can be afforded, check your entry")

    def save_log(self, order: bt.Order, num: int) -> None:
        """ description """
        datas = self.str_feed[num]
        if datas.feed.trading:
            with Database() as dbase:
                dbase.save_bot_log(bot_id=self.helper.id,
                                   ex_id=datas.feed.ex_id,
                                   symbol=datas.symbol,
                                   position=str(order.size),
                                   message=order.Status[order.status],
                                   feed_num=num)
        return None

    def get_value(self, num: str = ''):
        """
        returns how much value there is in an exchange
        """
        open_trade = self._get_last_trade(num)
        if open_trade:
            value = open_trade.cost-open_trade.fee
            return self.broker.cash + value
        return self.broker.cash

    def notify_trade(self, trade: bt.Trade) -> None:
        """
        Notifies when a trade is completed.
        Args:
            trade (bt.Trade): The trade object with trade information.
        """
        datas_num: int = int(trade.data._name)
        _trade = self._bt_trade_to_struct(trade)
        if trade.justopened:
            self.str_feed[datas_num].pos = _trade.volume
            cash = self.cash[datas_num] - _trade.cost
            self.open_trade[datas_num] = _trade
        else:
            self.str_feed[datas_num].pos = 0
            cash = self.cash[datas_num] + _trade.prev_cost + _trade.roi
            self.open_trade[datas_num] = None
        self.broker.set_cash(cash)
        with Database() as store:
            store.save_dry_trade(
                bot_id=self.helper.id,
                trade=_trade,
                reason='strategy'
            )

    def _bt_trade_to_struct(self, trade: bt.Trade) -> TradeStruct:
        """
        Convert a backtrader Trade object to a TradeStruct dictionary.

        Args:
            trade (bt.Trade): The backtrader Trade object.

        Returns:
            Dict: The TradeStruct dictionary containing trade information.
        """

        # Extract relevant data from the Trade object
        datas_num: int = int(trade.data._name)
        symbol: str = self.str_feed[datas_num].symbol
        ex_id: str = self.str_feed[datas_num].feed.ex_id

        # Create the initial trade dictionary
        trade_dict: Dict = {
            'uid': self.helper.uid,
            'ex_id': ex_id,
            'symbol': symbol,
            'side': 'Buy' if trade.size > 0 else 'Sell',
            'volume': abs(trade.size),
            'price': self.tick[datas_num],
            'cost': abs(trade.value),
            'fee': trade.commission
        }
        trade_struct = TradeStruct.from_dict(trade_dict)

        if not trade.justopened:
            open_trade = self._get_last_trade(datas_num=datas_num)
            trade_struct.price = self.tick[datas_num]
            trade_struct.volume = open_trade.volume
            trade_struct.prev_cost = open_trade.cost
            trade_struct.cost = open_trade.volume * trade_struct.price
            trade_struct.fee = trade_struct.fee - open_trade.fee
            if open_trade.side == "Buy":
                trade_struct.side = "Sell"
                trade_struct.roi = trade_struct.cost - open_trade.cost - trade_struct.fee - open_trade.fee
            else:
                trade_struct.side = "Buy"
                trade_struct.roi = open_trade.cost - trade_struct.cost - trade_struct.fee - open_trade.fee
            trade_total = trade_struct.roi + open_trade.cost
            trade_struct.roi_pct = ((trade_total - open_trade.cost) / open_trade.cost) * 100
            trade_struct.closingtrade = True
        return trade_struct

    def udpate_indicators_df(self) -> None:
        """
        updates self.indicator_df with lastest self.str_feed[num].dataframe
        """
        for num, data in enumerate(self.str_feed):
            if data.timeframe != bt.TimeFrame.Ticks:
                if self.new_candle[num]:
                    self.set_indicators_df()

    def set_indicators_df(self):
        """ description"""
        pass

    def _save_status(self) -> None:
        """
        Save the status of each data feed in the strategy based on the timeframe and
        trading status. This method distinguishes between live and simulation mode,
        calling the appropriate save status method accordingly.

        The method only executes once every minute to avoid flooding the cache with updates.

        Returns:
            None
        """
        # Get the current time
        current_time = arrow.utcnow()

        # If the last update happened less than a minute ago, skip this run
        if self.last_update is not None and (current_time - self.last_update).seconds < 5:
            return

        # Initialize an empty dictionary to store the status of each data feed
        datas_status = {}

        # Loop over all data feeds in the strategy
        for n in range(len(self.str_feed)):
            # If the data feed's timeframe is Ticks and trading is active
            if self.str_feed[n].timeframe == bt.TimeFrame.Ticks and self.str_feed[n].feed.trading:
                # Retrieve the simulated status for the current feed and store it in the dictionary
                datas_status[n] = self._get_bot_status(n)

        if datas_status:

            # Connect to the cache
            with cache.Cache() as mem:
                # Update the bot's status in the cache
                mem.update_bot(bot_id=self.helper.id, bot=datas_status)
                # Update the process in the cache
                mem.update_process(tipe="bot_status", key=self.helper.id, message="Updated")

        # Update the time of the last update
        self.last_update = current_time

    def _get_last_trade(self, datas_num):
        return self.open_trade[datas_num]

    def _get_bot_status(self, datas_num: int = 0) -> dict:
        """
        Gets the simulated status of the trading bot.

        This function captures the current state of the bot's simulated trading activity and saves it into a dictionary.
        The dictionary includes information such as the bot ID, exchange ID, the trading symbol, ROI, current funds,
        position, position price, and other details.

        Args:
            datas_num (int): The data index number. Defaults to 0.

        Returns:
            dict: A dictionary containing the simulated status of the bot.
        """
        # Get the data for the specified data index number
        datas = self.str_feed[datas_num]
        tick = self.str_feed[datas_num].params.mainfeed.close
        bot_id = self.helper.id

        # Initialize variables
        roi, roi_pct, pos_price, cur_value, orig_value = (0, 0, 0, 0, 0)

        if self.pos[datas_num] != 0:
            last_trade = self._get_last_trade(datas_num=datas_num)
            orig_value = last_trade.cost if last_trade else 0
            pos_price = last_trade.price if last_trade else 0
            cur_value = self.pos[datas_num] * tick

            if self.pos[datas_num] < 0:
                cur_value *= -1
            if last_trade:
                if self.pos[datas_num] < 0:
                    roi = float(orig_value) - float(cur_value)
                else:
                    roi = float(cur_value) - float(orig_value)
                if orig_value != 0:
                    roi_pct = (roi / float(orig_value)) * 100
                    roi_pct = round(roi_pct, 2)

        params = vars(self.params).copy()
        params.pop("helper", None)
        params.pop("stop_signal", None)
        params = json.dumps(params, indent=4, sort_keys=True)

        is_live = "Yes" if __name__ == 'live_strategy' else "No"

        bot = {
            "bot_id": bot_id,
            "ex_id": datas.feed.ex_id,
            "str_id": self.p.str_id,
            "bot_name": self.helper.bot_name,
            "symbol": datas.symbol,
            "exchange": datas.feed.exchange_name,
            "tick": self.tick[datas_num],
            "cash": round(self.cash[datas_num], 2),
            "free_funds": self.totalfunds[datas_num],
            "position": self.pos[datas_num],
            "open price": pos_price,
            "open value": round(orig_value, 2),
            "value": round(cur_value, 2),
            "roi": round(roi, 3),
            "roi pct": roi_pct,
            "orders": "",
            "live": is_live,
            "strategy": self.p.cat_name,
            "base": datas.feed.base,
            "params": params
        }
        return bot

    def update_simulated_cash_account(self, datas_num: int) -> None:
        """
        The purpose of this method is to simulate live trading using Backtrader's broker instead of a real exchange.

        This method is run once, from nextstart. It picks up the last trade, and if it is not a closing trade,
        it registers a closing date with current data and opens a new Backtrader broker trade. This is useful in case of a bot reboot.

        Args:
            datas_num (int): The index of the data feed to update.
        """
        # Get the last dry trade from the database

        with Database() as dbase:
            last_trade = dbase.get_last_dry_trade(
                bot_id=self.helper.id,
                symbol=self.str_feed[datas_num].symbol,
                ex_id=self.str_feed[datas_num].feed.ex_id
            )

        # If the last trade is not a closing trade, continue

        try:
            if last_trade.closingtrade:
                return
        except AttributeError:
            return

        with cache.Cache() as mem:
            price = float(mem.get_price(
                symbol=self.str_feed[datas_num].symbol,
                exchange=self.str_feed[datas_num].feed.exchange_name
            ))

        value = price * float(last_trade.volume)
        fee = last_trade.fee if last_trade.fee else 0

        # If it's a long position
        if last_trade.side == "Buy":
            side = "Sell"
            roi = value - (float(last_trade.cost) + fee * 2)
        # If it's a short position
        elif last_trade.side == "Sell":
            side = "Buy"
            roi = float(last_trade.cost) - (value + fee * 2)

        trade = {
            "uid": self.helper.uid,
            "ex_id": self.str_feed[datas_num].feed.ex_id,
            "symbol": self.str_feed[datas_num].symbol,
            "side": side,
            "price": price,
            "volume": last_trade.volume,
            "cost": value,
            "fee": fee,
            "order_type": "Limit",
            "roi": roi,
            "roi_pct": (roi / last_trade.cost) * 100,
            "reason": "botreboot",
            "closingtrade": True
        }
        trade = TradeStruct.from_dict(trade)

        with Database() as dbase:
            dbase.save_dry_trade(bot_id=self.helper.id, trade=trade, reason='botreboot')
        cash = self.broker.get_cash()
        with Database() as dbase:
            pnl = float(dbase.get_dry_margin(bot_id=self.helper.id))
        self.broker.set_cash(cash+pnl)
