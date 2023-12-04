from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from typing import List, Optional
from libs import settings
from libs.order_methods import OrderMethods
from libs.caches.orders_cache import Cache
from libs.structs.order_struct import OrderStruct


class FullonStore(object):
    '''API provider for CCXT feed and broker classes.'''

    def __init__(self, feed, retries: int = 1):
        '''Initializes the FullonStore with a retry count.'''
        self.retries = retries
        self.feed = feed

    def get_symbol_value(self, symbol: str) -> Optional[float]:
        """
        gets the pair current value

        params

        symbol: str - name of the symbol

        Returns

        float:  value of the symbol
        """
        result = None
        with Cache() as store:
            result = store.get_price(symbol=symbol)
        return result

    def get_cash(self) -> float:
        '''Retrieves the available cash for the given data.

        Returns:
            float: The available cash for the given data.
        '''
        base = self.feed.ex_base if str(self.feed.ex_base) != "" else self.feed.base
        cash = 0.0
        with Cache() as store:
            balance = store.get_full_account(exchange=self.feed.ex_id,
                                             currency=base)
            if balance:
                cash = balance['free']
        return cash

    def get_position(self, data) -> tuple:
        '''Retrieves the position for the given data.

        Returns:
            tuple: The position of the given data.
        '''
        if '/' in data.symbol:
            currency = data.symbol.split('/')[0]
        else:
            currency = data.symbol
        with Cache() as store:
            position = store.get_position(ex_id=data.feed.ex_id,
                                          symbol=data.symbol)
        return position.volume, position.price

    def get_value(self) -> float:
        '''Retrieves the value for all the positions

        Returns:
            float: The sum of the costs of all positions
        '''
        base = self.feed.ex_base if str(self.feed.ex_base) != "" else self.feed.base
        value = 0
        with Cache() as store:
            balance = store.get_full_account(exchange=self.feed.ex_id,
                                             currency=base)
            if balance:
                value = balance['total']
        return value

    def create_order(self, order: OrderStruct) -> Optional[OrderStruct]:
        '''Creates an order.

        Args:
            order: The order to be created.

        Returns:
            dict: A dictionary containing the order id, symbol, side and volume.
            None: If the order creation fails.
        '''
        om = OrderMethods()
        order = om.new_order(order=order)
        if order.order_id and 'error' not in order.status:
            return order
        return None

    def cancel_order(self, order: OrderStruct) -> bool:
        '''Cancels an order.

        Args:
            order: The order to be cancelled.

        Returns:
            bool: True if the cancellation is successful, False otherwise.
        '''
        om = OrderMethods()
        if om.cancel_order(oid=order.order_id, ex_id=order.ex_id):
            return True
        return False

    def get_min_entry(self, ex_id: str, symbol: str) -> float:
        ''' Gets the min entry for a symbol in the exchange

        Args:
            symbol: symbol for min order size

        Returns:
        '''
        om = OrderMethods()
        size = om.get_minimum_order(ex_id=ex_id, symbol=symbol)
        return size

    def fetch_open_orders(self) -> List[OrderStruct]:
        '''Fetches open orders for the given exchange id.

        Returns:
            list[OrderStruct]: A list of open orders for the given exchange id.
        '''
        with Cache() as store:
            _orders = store.get_orders(ex_id=self.feed.ex_id)
        orders = []
        for order in _orders:
            if 'pending' in order.status:
                orders.append(order)
        return orders

    def round_down(self, currency, futures, size):
        # checks if what remains is very little. less that 1.5 USD.
        # this is because trading spot, sometimes leaves decimals. that are untradable.
        if futures:
            return size
        mincost = 1.5
        if 'USD' in currency:
            with Cache() as store:
                price = store.get_price(
                    symbol=order.symbol,
                    exchange=self.helper.exchange)
        else:
            symbol = currency + "/" + settings.STABLECOIN
            with Cache() as store:
                price = self.helper.cache.get_price(symbol=symbol,
                                                    exchange=self.helper.exchange)

        cost = float(size) * float(price)

        if cost < 0:
            cost = cost * -1

        if cost < mincost:  # less than 1.5 usd in value
            return 0
        else:
            return size

