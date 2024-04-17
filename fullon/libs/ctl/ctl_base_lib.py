"""
Comments
"""

import xmlrpc.client
from libs import settings
from libs.settings_config import fullon_ctl_settings_loader


class CTL():
    """
    Launches RPC client
    """

    def __init__(self):
        self.RPC = xmlrpc.client.ServerProxy(f"http://{settings.XMLRPC_HOST}:{settings.XMLRPC_PORT}", allow_none=True)
