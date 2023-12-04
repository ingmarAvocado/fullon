#!/usr/bin/env python
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from backtrader import BrokerBase, Order
from backtrader.utils.py3 import queue
from backtrader.position import Position
from libs import log
from libs.btrader.fullonstore import FullonStore
from libs.structs.order_struct import OrderStruct
from backtrader import OrderBase
from typing import Optional

logger = log.fullon_logger(__name__)


class FullonOrder(OrderBase):
    def __init__(self, owner, data, fullon_order: OrderStruct):
        self.owner = owner
        self.data = data
        self.fullon_order = fullon_order
        self.executed_fills = []
        self.ordtype = self.Buy if fullon_order.side.lower() == 'buy' else self.Sell
        self.size = float(fullon_order.volume)
        super(FullonOrder, self).__init__()


class FullonBroker(BrokerBase):
    '''Broker implementation for CCXT cryptocurrency trading library.

    This class maps the orders/positions from CCXT to the
    internal API of ``backtrader``.
    '''

    order_types = {Order.Market: 'market',
                   Order.Limit: 'limit',
                   Order.Stop: 'stop-loss',
                   Order.StopLimit: 'stop-limit'}

    def __init__(self, feed, retries=5):
        super(FullonBroker, self).__init__()
        self.store = FullonStore(feed=feed, retries=retries)
        self.notifs = queue.Queue()  # holds orders which are notified
        self.startingcash = 0

    def _submit(self, owner, data, exectype, side, amount, price, plimit, command, params):
        params.pop('transmit', None)
        params.pop('parent', None)
        order_type = self.order_types.get(exectype)
        _order = {"ex_id": data.feed.ex_id,
                  "cat_ex_id": data.feed.cat_ex_id,
                  "exchange": data.feed.exchange_name,
                  "symbol": data.symbol,
                  "order_type": order_type,
                  "volume": amount,
                  "price": price,
                  "plimit": plimit,
                  "side": side,
                  "reason": 'signal',
                  "command": command,
                  "subcommand": "",
                  "leverage": owner.p.leverage,
                  "bot_id": "00000000-0000-0000-0000-000000000002"}
        _order = OrderStruct.from_dict(_order)
        _order = self.store.create_order(order=_order)
        if _order:
            order = FullonOrder(owner, data, _order)
            self.notify(order)
            return order
        return None

    def buy(
            self,
            owner,
            data,
            size,
            price=None,
            plimit=None,
            exectype=None,
            valid=None,
            tradeid=0,
            oco=None,
            trailamount=None,
            trailpercent=None,
            command=None,
            **kwargs):
        return self._submit(owner, data, exectype, 'Buy', size, price, plimit, command, kwargs)

    def sell(
            self,
            owner,
            data,
            size,
            price=None,
            plimit=None,
            exectype=None,
            valid=None,
            tradeid=0,
            oco=None,
            trailamount=None,
            trailpercent=None,
            command=None,
            **kwargs):
        return self._submit(owner, data, exectype, 'Sell', size, price, plimit, command, kwargs)

    def getcash(self):
        return self.store.get_cash()

    def getposition(self, data):
        size, price = self.store.get_position(data=data)
        return Position(size, price)

    def getvalue(self):
        return self.store.get_value()

    def get_symbol_value(self, symbol: str) -> Optional[float]:
        """
        returns the falue for the symbol
        """
        return self.store.get_symbol_value(symbol=symbol)

    def get_notification(self):
        try:
            return self.notifs.get(False)
        except queue.Empty:
            return None

    def notify(self, order):
        self.notifs.put(order)

    def cancel(self, order):
        return self.store.cancel_order(order=order)

    def get_orders_open(self):
        return self.store.fetch_open_orders()

    def get_min_entry(self, datas):
        return self.store.get_min_entry(ex_id=datas.feed.ex_id,
                                        symbol=datas.symbol)
