"""
description
"""
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals)

import backtrader as bt
import arrow
from libs import log
from libs.strategy import strategy
from typing import Optional

logger = log.fullon_logger(__name__)


class Strategy(strategy.Strategy):
    """ description """

    def __init__(self):
        """ description """
        super().__init__()
        self.exectype = bt.Order.Market
        self.dry_run = False
        self.last_trading_date = None

    def nextstart(self):
        """prepare the startegy"""
        super().nextstart()
        if not self.indicators_df.empty:
            self.indicators_df.dropna(inplace=True)
        else:
            self.set_indicators_df()
        self._state_variables()
        self.local_nextstart()
        self.last_trading_date = arrow.get(
            self.datas[0].last_date).shift(minutes=-1)
        return None

    def next(self):
        """ description """
        self.status = "looping"
        self._set_indicators()
        if self.anypos == 0:
            self.local_next()
        else:
            if not self._check_end_simul():
                self.risk_management()
            self._end_next()
        return

    def _set_indicators(self):
        self._state_variables()
        self.set_indicators()
        self.get_entry_signal()

    def _check_end_simul(self) -> bool:
        """
        Checks wether this is last loop and if it is, it closes positions
        """
        if self.curtime[0] >= self.last_trading_date:
            for pos_num in range(0, len(self.datas)):
                try:
                    if self.pos[pos_num]:
                        self.close_position(reason="loop end", feed=pos_num)
                except KeyError:
                    pass
            return True
        return False

    def place_order(self, signal, entry, otype=None, datas=None, reason=None):
        """ description """
        self.order_placed = True
        if otype is None:
            otype = self.exectype
        datas = self.datas[0] if not datas else datas
        if signal == "Buy":
            return self.buy(datas, exectype=otype, size=entry)
        if signal == "Sell":
            return self.sell(datas, exectype=otype, size=entry)
        return None

    def notify_order(self, order):
        """ description """
        if order.status == 7:
            logger.error(
                "Trying to buy more than can be afforded, check your entry")
            self.stop()
            raise ValueError("Cant continue without funds")

    def notify_trade(self, trade):
        """ description """
        datas_num = int(trade.data._name)
        trade.price = self.tick[datas_num]
        if trade.status == 1:
            if trade.size > 0:
                last_side = 'Buy'
            else:
                last_side = 'Sell'
        else:
            last_side = self.helper.simulresults[self.p.str_id][datas_num][-1]['side']
            if last_side == 'Buy':
                last_side = 'Sell'
            else:
                last_side = 'Buy'

        timestamp = self.datas[0].datetime.datetime(0)
        last_ref = -1
        if len(self.helper.simulresults[self.p.str_id][datas_num]) > 0:
            last_ref = self.helper.simulresults[self.p.str_id][datas_num][-1]['ref']
        if last_ref == trade.ref:  # This is a closing trade
            amount = abs(self.helper.simulresults[self.p.str_id][datas_num][-1]['amount'])
            last_comm = self.helper.simulresults[self.p.str_id][datas_num][-1]['fee']
            trade.commission = trade.commission - last_comm
            prev_cost = self.helper.simulresults[self.p.str_id][datas_num][-1]['cost']
            cost = trade.price * amount

            if last_side == "Buy":  # closing a short
                trade.pnlcomm = prev_cost - cost - trade.commission
            else:  # closing a long
                trade.pnlcomm = cost - prev_cost - trade.commission

            cash = self.helper.simulresults[self.p.str_id][datas_num][-1]['cash'] + \
                prev_cost + trade.pnlcomm
            assets = cash # we need to use this variable, as we also use cash variable
            self.broker.cash = cash
            roi_pct = round(trade.pnlcomm / prev_cost * 100, 2)
        else:
            if trade.size < 0:
                amount = trade.size * -1
                cost = trade.value * -1
                cash = self.cash[datas_num] - cost
            else:
                amount = trade.size
                cash = self.cash[datas_num] - trade.value
                cost = trade.value
            self.broker.cash = cash
            assets = self.cash[datas_num] - trade.commission
            trade.pnlcomm = 0
            roi_pct = 0

        closing = False if trade.justopened else True
        r = {
            "ref": trade.ref,
            "timestamp": timestamp,
            "side": last_side,
            "price": trade.price,
            "amount": amount,
            "cost": cost,
            "roi": trade.pnlcomm,
            "roi_pct": roi_pct,
            "fee": trade.commission,
            "cash": cash,
            "assets": assets,
            "reason": self.lastclose[datas_num]}
        r.update(vars(self.indicators))
        self.helper.simulresults[self.p.str_id][datas_num].append(r)
