from typing import Any, Dict, Callable, Optional
from multiprocessing import Process, Manager
from multiprocessing.queues import Queue
from time import sleep
from setproctitle import setproctitle
import psycopg2
from libs import log, settings
from libs.models.ohlcv_model import Database as DatabaseOHLCV
from libs.queue_pool import QueuePool
from enum import Enum

# Setup logging
logger = log.fullon_logger(__name__)
request_queue: Optional[Queue] = None
response_queue_pool: Optional[QueuePool] = None
processes: Dict[int, Process] = {}
_started: bool = False


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
        num: int worker #
        mngr: An instance of multiprocessing.Manager.
    """
    setproctitle(f"Fullon database worker #{num} for OHLCV")
    dbase_instance = None
    while True:
        try:
            request = request_queue.get()
            if request == ControlSignals.STOP.value:
                logger.warning(f"Stopping ohlcv worker {num}")
                break
            exchange, symbol, method_name, method_params, response_queue = request
            max_retries = 30
            for attempt in range(max_retries):
                try:
                    if not dbase_instance:
                        dbase_instance = DatabaseOHLCV(exchange=exchange, symbol=symbol)
                    else:
                        dbase_instance.reset_params(exchange=exchange, symbol=symbol)
                    method = getattr(dbase_instance, method_name)
                    result = method(**method_params)
                    response_queue.put(result)
                    break  # Break the loop if successful
                except psycopg2.OperationalError as db_error:
                    if attempt < max_retries - 1:  # Check if more retries are left
                        msg = f"OHLCV database operation failed, retry {attempt + 1}/{max_retries}. Error: {db_error}"
                        logger.warning(msg)
                        sleep(1.5)  # Wait before retrying
                        if dbase_instance:
                            dbase_instance.endthis()  # Reset connection pool before retry
                            dbase_instance = None
                    else:
                        msg = f"OHLCVd atabase operation failed after {max_retries} attempts. Error: {db_error}"
                        logger.error(msg)
                        response_queue.put(None)  # Indicate failure to the requester
                        break
                except psycopg2.errors.SyntaxError:
                    msg = f"Error in method{method_name} with params {method_params}"
                    logger.error(msg)
        except KeyboardInterrupt:
            #logger.error("KeyboardInterrupt received. Shutting down.")
            break
        except (BrokenPipeError, EOFError, ConnectionResetError) as error:
            #logger.error(f"Connection-related error: {error}")
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
    global request_queue, response_queue_pool, process, _started, response_queue_pool
    if not response_queue_pool:
        response_queue_pool = QueuePool(procname="Database Ohlcv")
    if not _started:
        _started = True
        logger.info(f"Starting Database Queue Manager for OHCLV")
        mngr = Manager()
        request_queue = mngr.Queue()
        for num in range(0, settings.DBWORKERS_OHLCV):
            processes[num] = Process(target=process_requests, args=(num, request_queue, mngr))
            processes[num].start()


def stop():
    """
    Stops the request processing by sending a STOP signal and joining the process.
    """
    global request_queue, response_queue_pool, process, _started
    if _started:
        logger.info(f"Stopping Exchange Queue Manager for 'OHLCV")
        try:
            request_queue.put(ControlSignals.STOP.value)
        except FileNotFoundError:
            pass
        for num, process in processes.copy().items():
            process.join(timeout=0.1)
            if process.is_alive():
                logger.debug(f"Force terminating process for 'OHLCV'")
                process.terminate()
            del processes[num]
        request_queue = None
        response_queue_pool = None
        process = {}
        _started = False


class Database:
    """
    Initializes a Database object with exchange and symbol information.

    Parameters:
        exchange: The name of the exchange.
        symbol: The trading symbol.
    """

    def __init__(self, exchange: str, symbol: str):
        """ Docstring this """
        self.exchange = exchange
        self.symbol = symbol

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
            # print("OHLCV DB QUEUE", request_queue.qsize(), len(processes))
            with response_queue_pool.get_queue() as response_queue:
                if not request_queue:
                    raise WorkerError("Database queue not initialized")

                request_queue.put((self.exchange, self.symbol, attr, params, response_queue))
                result = response_queue.get()  # Missing line in original code

                if isinstance(result, tuple) and result[0] == ControlSignals.STOP.value:
                    raise WorkerError(f"Error in worker process: {result[1]}")
                return result
        except (EOFError, AttributeError) as error:
            error = str(error)
            if 'EOFerror' in error:
                pass
            elif 'AttributeError' in error and 'get_queue' in error:
                pass
            else:
                
                print("SOOOMMEE ERROR")
                raise
