"""
Process manager
"""

import time
import xmlrpc.client
from setproctitle import setproctitle
from libs import settings, cache, log
import json
from typing import List, Any

logger = log.fullon_logger(__name__)


class ProcessManager():
    """ description """

    def __init__(self):
        """ description """
        self.rpc = xmlrpc.client.ServerProxy(
            f'http://{settings.XMLRPC_HOST}:{settings.XMLRPC_PORT}')

    def get_top(self) -> List[Any]:
        """
        Get the top services.
        Returns:
            A list of top services.
        """
        with cache.Cache() as store:
            data = store.get_top()
        return [{k: v for k, v in d.items() if k != 'params'} for d in data]
