"""
This class manages user accounts from exchanges.
Gets the trades, account totals, etc.
"""
import threading
import arrow
from libs.structs.position_struct import PositionStruct
from libs import log
from libs.cache import Cache
from libs.database import Database
from typing import List, Optional
import time

logger = log.fullon_logger(__name__)


class Reg:
    """ helper class"""
    def __init__(self):
        """ description """

    def __del__(self):
        """ description """

    def value(self):
        """ description """


class BotStatusManager:
    """ main account class"""

    started: bool = False
    _bot_blocked: dict = {}

    def __init__(self):
        """ description """
        # logger.info("Initializing Bot Status Manager")
        self.stop_signal: threading.Event = threading.Event()
        self.thread_lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None
        self.monitor_thread: threading.Thread
        self.monitor_thread_signal: threading.Event = threading.Event()
        self.started = False

    def __del__(self):
        self.stop()

    def stop_all(self):
        """
        redicted to stop
        """
        self.stop()

    def stop(self) -> None:
        """
        Stops the tick data collection loop for the specified exchange.
        """
        self.stop_signal.set()
        self.monitor_thread_signal.set()
        with self.thread_lock:
            if self.thread:
                self.thread.join()
        self.started = False

    def run_loop(self) -> None:
        """
        Starts the background thread for processing positions.
        """
        logger.info("Starting Bot Status Manager")
        self.started = True
        self.thread = threading.Thread(target=self._process_positions_loop)
        self.thread.daemon = True
        self.thread.start()
        self.monitor_thread = threading.Thread(target=self.relaunch)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def _process_positions_loop(self) -> None:
        """
        Continuously processes positions in a loop, executed on a separate thread.
        """
        with Cache() as store:
            store.new_process(tipe='bot_status_service',
                              key='service',
                              params={},
                              message='started')
        while not self.stop_signal.is_set():
            with self.thread_lock:
                self._process_positions()
                with Cache() as store:
                    store.update_process(tipe="bot_status_service",
                                         key='service',
                                         message="Updated")
            for _ in range(10):
                if self.stop_signal.is_set():
                    break
                time.sleep(1)

    def _process_positions(self) -> None:
        """
        Processes positions to find and block or unblock as necessary.
        """
        with Cache() as store:
            positions = store.get_all_positions()
        for position in positions:
            self._find_and_block_position(position=position)
        self._unblock_unnecessary(positions=positions)

    def _unblock_unnecessary(self, positions: List[PositionStruct]) -> None:
        """
        Unblocks exchanges and symbols that are not currently in active positions.

        This function checks the list of currently blocked exchanges and symbols against
        the active positions. If a blocked exchange or symbol is not present in the active positions,
        it is unblocked.

        Args:
            positions (List[PositionStruct]): A list of active positions.

        Returns:
            None
        """
        # Retrieve the list of current blocks
        with Cache() as store:
            blocks: List[dict] = store.get_blocks()

        # Set of active (ex_id, symbol) pairs for quick lookup
        active_positions = {(position.ex_id, position.symbol) for position in positions}

        # Unblocking exchanges and symbols not in active positions
        for block in blocks:
            if (block['ex_id'], block['symbol']) not in active_positions:
                # so maybe we don't have a position but we are about to have one.
                # easiest is with a new tmp key that stats when opening positions
                with Cache() as store:
                    if not store.is_opening_position(ex_id=block['ex_id'],
                                                     symbol=block['symbol']):
                        store.unblock_exchange(ex_id=block['ex_id'],
                                               symbol=block['symbol'])
                        key = f"{block['ex_id']}:{block['symbol']}"
                        self._bot_blocked[key] = False

    def _find_and_block_position(self, position: PositionStruct) -> None:
        """
        Checks and blocks an exchange and symbol pair based on a given position.

        This method reviews the last actions for a given position's symbol and exchange ID. If it finds
        a corresponding action with the same volume, it blocks the exchange for that specific bot. If no
        matching action is found, it blocks the exchange with a default bot ID.

        Args:
            position (PositionStruct): The position based on which the blocking is to be evaluated.

        Returns:
            None
        """
        key = f"{position.ex_id}:{position.symbol}"
        with Database() as dbase:
            logs = dbase.get_last_actions(symbol=position.symbol, ex_id=position.ex_id)

        blocked = False
        for log in logs:
            if str(log.position) == str(position.volume):
                blocked = True
                with Cache() as store:
                    blocked_by = store.is_blocked(ex_id=position.ex_id, symbol=position.symbol)
                    if not blocked_by or str(blocked_by) != str(log.bot_id):
                        logger.warning("Blocking exchange '%s' symbol '%s' due to matching log.", position.ex_id, position.symbol)
                        store.block_exchange(ex_id=position.ex_id, symbol=position.symbol, bot_id=log.bot_id)
                        break
        if not blocked:
            if not self._bot_blocked.get(key, False):
                logger.warning("Position detected without a corresponding bot log. Blocking with default bot ID.")
            #  If no corresponding log found, block with a default bot ID                
            with Cache() as store:
                self._bot_blocked[key] = True
                store.block_exchange(ex_id=position.ex_id, symbol=position.symbol, bot_id=0)

    def relaunch(self):
        """
        launches deamon if dead
        """
        while not self.monitor_thread_signal.is_set():
            if not self.thread.is_alive():
                self.run_loop()
            for _ in range(10):
                if self.monitor_thread_signal.is_set():
                    break
                time.sleep(1)