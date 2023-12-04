"""
CTL library wrap
"""

import xmlrpc.client
from libs import settings
from libs.ctl.ctl_bot_lib import CTL


class CTL(CTL):
    """
    Launches RPC client
    """
