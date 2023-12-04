"""
Comments
"""

from tabulate import tabulate
from libs import log
from libs.ctl.ctl_symbols_lib import CTL
from clint.textui import colored
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from typing import Optional, Tuple

logger = log.fullon_logger(__name__)


class CTL(CTL):
    """
    The CTL class is responsible for managing symbol-related functionalities,
    such as listing symbols.
    """

    def get_ticks_list(self) -> list:
        """
        Retrieves a paginated list of strategies.

        Parameters:
            page (int): The current page number. Defaults to 1.
            page_size (int): The number of records to return per page. Defaults to 10.

        Returns:
            list: A list of strategies for the current page.
        """
        args = {}
        ticks: list = self.RPC.tickers('list', args)
        return ticks
