#!/usr/bin/env python
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from backtrader.brokers import BackBroker
from libs import log
from libs.btrader.fullonstore import FullonStore
from typing import Optional

logger = log.fullon_logger(__name__)


class BaseBroker(BackBroker):
    '''Broker implementation for CCXT cryptocurrency trading library.

    This class maps the orders/positions from CCXT to the
    internal API of ``backtrader``.
    '''

    def get_symbol_value(self, symbol: str) -> Optional[float]:
        """
        returns the falue for the symbol
        """
        store = FullonStore(feed=0, retries=1)
        return store.get_symbol_value(symbol=symbol)
