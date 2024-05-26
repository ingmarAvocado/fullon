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
        self.open_trade_indicators: dict = {}

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
            self.str_feed[0].last_date).shift(minutes=-1)
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
            for pos_num in range(0, len(self.str_feed)):
                try:
                    if self.pos[pos_num]:
                        self.close_position(reason="loop end", feed=pos_num)
                except KeyError:
                    pass
            return True
        return False

    def notify_order(self, order):
        """ description """
        if order.status == 7:
            if self.totalfunds[0] < 100:
                logger.error("Something happen and ran out of funds for trade")
                raise ValueError("Cant continue without funds")

    def notify_trade(self, trade):
        """ description """
        datas_num = int(trade.data._name)
        if trade.isopen:
            self.open_trade_indicators = vars(self.indicators).copy()
            self.open_trade_indicators['assets'] = self.broker.getvalue()
            return

        last_cost = None  # This will store the cost of the last modifying trade

        for num, t in enumerate(trade.history):
            side = 'Buy' if t.event.size > 0 else 'Sell'
            current_cost = t.status.value if t.status.size != 0 else last_cost  # Use last non-zero cost

            _trade = {
                "num": trade.ref,
                "seq": num,
                "timestamp": bt.num2date(t.status.dt),
                "side": side,
                "event_price": t.event.price,
                "avg_price": t.status.price,
                "event_size": t.event.size,
                "avg_size": t.status.size,
                "cost": current_cost,
                "pnl": t.status.pnl,
                "pnlfee": t.status.pnlcomm,
                "roi": 0,
                "fee": t.event.commission,
                "assets": self.broker.getvalue() if t.status.size == 0 else None,
                "reason": self.lastclose[datas_num] if t.status.size == 0 else None
            }

            # Calculate ROI using the last modifying trade's cost
            if last_cost and num > 0:  # Ensure there was a modifying cost and it's not the first event
                # Adjust ROI calculation for short positions
                if last_cost > 0:  # Long position
                    _trade['roi'] = (t.status.pnlcomm / last_cost) * 100 if last_cost else 0
                else:  # Short position
                    _trade['roi'] = (t.status.pnlcomm / abs(last_cost)) * 100 if last_cost else 0

            # Update last cost for next calculation if this event modifies the size
            if t.status.size != 0:
                last_cost = current_cost

            # Append the trade information to simulation results
            self.helper.simulresults[self.p.str_id][datas_num].append(_trade)
