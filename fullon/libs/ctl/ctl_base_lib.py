"""
Comments
"""

import xmlrpc.client
from libs import settings


class CTL():
    """
    Launches RPC client
    """

    def __init__(self):
        self.RPC = xmlrpc.client.ServerProxy(f"http://{settings.XMLRPC_HOST}:{settings.XMLRPC_PORT}", allow_none=True)
