from typing import Any, Dict, Optional
from multiprocessing import Process, Manager, Event
from multiprocessing.queues import Queue
from time import sleep
from setproctitle import setproctitle
from libs import log
from enum import Enum
from libs.bot import Bot  # import your Bot class
from libs.queue_pool import QueuePool

# Setup logging
logger = log.fullon_logger(__name__)
request_queue: Optional[Queue] = None
response_queue_pool = QueuePool()
process: Optional[Process] = None
stop_signals: Dict[int, Any] = {}
_started: bool = False


class ControlSignals(Enum):
    STOP = "StopThisRun"


class BotLauncher():

    def __init__(self):
        self.processes: Dict[int, Process] = {}
        self.stop_signals: Dict[int, Any] = {}

    def stop_all(self):
        """
        stops all bots and launchers
        """
        for bot in list(self.processes.keys()):
            self.stop_bot(bot_id=bot)

    def start_bot(self, bot_id: int) -> bool:
        stop_signal = Event()
        mainbot = Bot(bot_id=bot_id)
        if mainbot.id:
            process = Process(target=mainbot.run_loop, args=(stop_signal,))
            process.start()
            self.processes[bot_id] = process
            self.stop_signals[bot_id] = stop_signal
            return True
        else:
            logger.warning(f"Bot with id {bot_id} could not be created")
            return False

    def stop_bot(self, bot_id: int) -> bool:
        """
        Stops the specified bot.

        Args:
            bot_id (int): The id of the bot to stop
        """
        if bot_id in self.stop_signals:
            self.stop_signals[bot_id].set()
            process = self.processes.get(bot_id, None)
            if process:
                process.join(2)
                if process.is_alive():
                    logger.warning(f"Bot {bot_id} didn't stop in time, forcefully terminating...")
                    process.terminate()
                    process.join(5)
            del self.stop_signals[bot_id]
            del self.processes[bot_id]
            return True
        else:
            logger.info(f"No running bot found for bot_id {bot_id}")
            return False

    def is_running(self, bot_id: int) -> bool:
        """
        Checks if a bot with a given id is running.

        Args:
            bot_id (int): The id of the bot to check.

        Returns:
            bool: True if the bot is running, False otherwise.
        """
        process = self.processes.get(bot_id, None)
        return process.is_alive() if process else False

    def get_bots(self):
        return self.processes.keys()


def process_requests(request_queue: Queue,  mngr: object):
    setproctitle(f"Fullon Bot Launcher")
    launcher = BotLauncher()
    while True:
        try:
            cmd, bot_id, response_queue = request_queue.get()
            res = None
            match cmd:
                case 'start':
                    res = launcher.start_bot(bot_id=bot_id)
                case ControlSignals.STOP.value:
                    launcher.stop_all()
                    mngr.shutdown()
                    return
                case 'ping':
                    res = launcher.is_running(bot_id=bot_id)
                case 'stop':
                    res = launcher.stop_bot(bot_id=bot_id)
                case 'stop_all':
                    res = launcher.stop_all()
                case 'get_bots':
                    res = launcher.get_bots()
                case _:
                    logger.debug("Uknown command")
                    res = None
            response_queue.put(res)
        except KeyboardInterrupt:
            #logger.warning("KeyboardInterrupt received. Shutting down.")
            mngr.shutdown()
            return
        except (BrokenPipeError, EOFError, ConnectionResetError, FileNotFoundError) as error:
            #logger.error(f"Connection-related error: {error}")
            mngr.shutdown()
            return
        except TypeError as error:
            logger.error(f"Type error: {error}")
            response_queue.put(None)


def start():
    global _started, request_queue, process
    setproctitle("Fullon Launcher Bot Queue")
    if not _started:
        _started = True
        logger.info("Starting Bot launcher queue")
        mngr = Manager()
        request_queue = mngr.Queue()
        process = Process(target=process_requests,
                          args=(request_queue, mngr))
        process.start()
        setproctitle(f"Fullon Daemon")


def stop():
    global _started, request_queue, response_queue_pool, process
    if _started:
        logger.info("Stopping Bot laucher queue")
        try:
            with response_queue_pool.get_queue() as response_queue:
                request_queue.put((ControlSignals.STOP.value, '', response_queue))
            sleep(1)
        except FileNotFoundError:
            pass
        if process:
            process.join(timeout=1)
            if process.is_alive():
                logger.warning("Force terminating Bot Manager")
                process.terminate()
        request_queue = None
        response_queue_pool = None
        process = None
        _started = False


class Launcher():

    def start(self, bot_id: int) -> bool:
        """
        Start a bot instance identified by its bot_id.

        Args:
            bot_id (int): Unique identifier for the bot.

        Returns:
            bool: True if bot started successfully, otherwise False.
        """
        global request_queue, response_queue_pool

        try:
            with response_queue_pool.get_queue() as response_queue:
                if not self.ping(bot_id=bot_id):
                    request_queue.put(('start', bot_id, response_queue))
                    res = response_queue.get()
                    logger.info("Bot %s started", bot_id)
                    return res
        except Exception as e:
            logger.error(f"Failed to start bot {bot_id}: {e}")
        logger.info("Can't start Bot")
        return False

    def stop(self, bot_id: int) -> bool:
        """
        Stop a bot instance identified by its bot_id.

        Args:
            bot_id (int): Unique identifier for the bot.

        Returns:
            bool: True if bot stopped successfully, otherwise False.
        """
        global request_queue, response_queue_pool
        try:
            with response_queue_pool.get_queue() as response_queue:
                if request_queue:
                    request_queue.put(('stop', bot_id, response_queue))
                    res = response_queue.get()
                    if res:
                        logger.info("bot id stopped: %s", bot_id)
                        return True
        except Exception as e:
            logger.error(f"Failed to stop bot {bot_id}: {e}")

        return False

    def ping(self, bot_id: int) -> bool:
        """
        Ping a bot instance to check its status.

        Args:
            bot_id (int): Unique identifier for the bot.

        Returns:
            bool: True if bot is alive, otherwise False.
        """
        global request_queue, response_queue_pool
        try:
            with response_queue_pool.get_queue() as response_queue:
                if request_queue:
                    request_queue.put(('ping', bot_id, response_queue))
                    return response_queue.get()
        except Exception as e:
            logger.error(f"Failed to ping bot {bot_id}: {e}")

        return False

    def stop_all(self):
        """
        Stop all active bot instances.
        """
        global request_queue, response_queue_pool
        try:
            with response_queue_pool.get_queue() as response_queue:
                if request_queue:
                    request_queue.put(('stop_all', '', response_queue))
                    response_queue.get()
                    logger.warning("All bots stopped")
        except Exception as e:
            logger.error(f"Failed to stop all bots: {e}")

    def get_bots(self) -> list:
        """
        Retrieve a list of all active bot instances.

        Returns:
            list: List of active bots.
        """
        global request_queue, response_queue_pool
        try:
            with response_queue_pool.get_queue() as response_queue:
                if request_queue:
                    request_queue.put(('get_bots', '', response_queue))
                    res = response_queue.get()
                    return res
        except Exception as e:
            logger.error(f"Failed to get list of bots: {e}")

        return []
