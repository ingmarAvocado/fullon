from typing import Any, Dict, Callable, Optional
from multiprocessing import Process, Manager
from multiprocessing.queues import Queue
from queue import Empty  # Import Empty exception from queue module
from time import sleep
from setproctitle import setproctitle
import psycopg2
from libs import log, settings
from libs.models.bot_model import Database as MainDatabase
from libs.queue_pool import QueuePool
from enum import Enum

# Setup logging
logger = log.fullon_logger(__name__)
request_queue: Optional[Queue] = None
response_queue_pool: Optional[QueuePool] = QueuePool()
processes: Dict = {}
_started: bool = False
WORKERS = settings.DBWORKERS


class ControlSignals(Enum):
    STOP = "StopThisRun"


class WorkerError(Exception):
    """Custom error to be raised when an error occurs in the worker thread."""


def process_requests(num: int, request_queue: Queue, mngr: object) -> None:
    """
    Continuously listens for requests and processes them.
    It also puts the result into the response queue.

    Parameters:
        request_queue: The queue for incoming requests.
        int: woker #
        mngr: An instance of multiprocessing.Manager.
    """
    title = f"Fullon database queue #{num} for {settings.DBNAME}"
    setproctitle(title)
    dbase_instance = MainDatabase()
    while True:
        try:
            request = request_queue.get()
            if request == ControlSignals.STOP.value:
                logger.warning(f"Stopping worker {num}")
                break

            method_name, method_params, response_queue = request

            # Attempt to process the request with retries
            max_retries = 30
            for attempt in range(max_retries):
                try:
                    if not dbase_instance:
                        dbase_instance = MainDatabase()
                    method = getattr(dbase_instance, method_name)
                    result = method(**method_params)
                    response_queue.put(result)
                    break  # Break the loop if successful
                except psycopg2.OperationalError as db_error:
                    if attempt < max_retries - 1:  # Check if more retries are left
                        logger.warning(f"Database operation failed, retry {attempt + 1}/{max_retries}. Error: {db_error}")
                        sleep(1.5)  # Wait before retrying
                        if dbase_instance:
                            dbase_instance.endthis()  # Reset connection pool before retry
                            dbase_instance = None
                    else:
                        logger.error(f"Database operation failed after {max_retries} attempts. Error: {db_error}")
                        response_queue.put(None)  # Indicate failure to the requester
                        break
        except KeyboardInterrupt:
            logger.debug("KeyboardInterrupt received. Shutting down.")
            break
        except (BrokenPipeError, EOFError, ConnectionResetError) as error:
            #logger.warning(f"Connection-related error: {error}")
            break
        except TypeError as error:
            logger.error(f"Type error: {error}")
            response_queue.put(None)
    if dbase_instance:
        dbase_instance.endthis()
    mngr.shutdown()


def start():
    """
    Starts the request processing by initializing Queues and kicking off the separate process.
    """
    global request_queue, processes, _started, WORKERS
    setproctitle("Fullon OHLCV Launcher")
    if not _started:
        _started = True
        logger.info("Starting Database Queue Manager for %s", settings.DBNAME)
        mngr = Manager()
        request_queue = mngr.Queue()
        for num in range(0, WORKERS):
            processes[num] = Process(target=process_requests,  args=(num, request_queue,  mngr))
            processes[num].start()


def stop():
    """
    Stops the request processing by sending a STOP signal and joining the process.
    """
    global request_queue, response_queue_pool, processes, _started
    logger.info("Stopping Exchange Queue Manager for %s", settings.DBNAME)
    try:
        request_queue.put(ControlSignals.STOP.value)
        sleep(1)
    except FileNotFoundError:
        pass
    for num in processes.copy().keys():
        processes[num].join(timeout=1)
        if processes[num].is_alive():
            # logger.warning("Force terminating process for %s", settings.DBNAME)
            processes[num].terminate()
        del processes[num]
        request_queue = None
        response_queue_pool = QueuePool()
        _started = False


class Database:
    """
    Initializes a Database object with exchange and symbol information.

    Parameters:
        exchange: The name of the exchange.
        symbol: The trading symbol.
    """

    def __enter__(self):
        """Initialize or prepare the resources."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up the resources."""
        # Optionally, handle exceptions here, or just let it propagate
        if exc_type is not None:
            # Handle the exception (note: it will still propagate unless you return True)
            pass
        # Perform cleanup actions here if needed

    def __getattr__(self, attr: str) -> Callable[..., Any]:
        """
        Provides a generic method interface for undefined methods.

        Parameters:
            attr: The attribute (or method name) being accessed.

        Returns:
            A callable that forwards the method call to the worker process.
        """
        def default(**params: Dict[str, Any]) -> Any:
            return self._run_default(attr, params)
        return default

    def _run_default(self, attr: str, params: Dict[str, Any]) -> Any:
        """
        Forwards the method call to the separate process and waits for the result.

        Parameters:
            attr: The attribute (or method name) being accessed.
            params: The parameters to be passed to the method.

        Returns:
            The result from the worker process.

        Raises:
            WorkerError: If the database queue is not initialized.
        """
        global request_queue, response_queue_pool
        try:
            with response_queue_pool.get_queue() as response_queue:
                if not request_queue:
                    raise WorkerError("Database queue not initialized")
                request_queue.put((attr, params, response_queue))
                try:
                    result = response_queue.get(timeout=25)
                except (EOFError, Empty, KeyboardInterrupt):
                    return
                if isinstance(result, tuple) and result[0] == ControlSignals.STOP.value:
                    raise WorkerError(f"Error in worker process: {result[1]}")
                return result
        except RuntimeError:
            pass
