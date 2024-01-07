from typing import Any, Dict, Callable, Optional
from multiprocessing import Process, Manager, Queue, Lock
from queue import Empty
from libs.cache import Cache
from libs.exchange_methods import ExchangeMethods
from libs import log, settings, database
from libs.structs.exchange_struct import ExchangeStruct
from libs.queue_pool import QueuePool
from time import sleep
from run import user_manager
from setproctitle import setproctitle

logger = log.fullon_logger(__name__)


request_queues: Dict = {}
processes: Dict = {}

SENTINEL: Dict = {}
NOQUEUE_POOL: Dict = {}
lock = Lock()


response_queue_pool = QueuePool()


class WorkerError(Exception):
    """Custom error to be raised when an error occurs in the worker thread."""


def stop_exchange(exchange_pool):
    uids = list(exchange_pool.keys())
    for uid in uids:
        del exchange_pool[uid]
        sleep(1)


def process_requests(request_queue: Queue, exchange: str, mngr: object) -> None:
    """
    Process requests in a separate thread.

    Args:
        request_queue (Queue): Queue for incoming requests.
        mngr (object): The manager object for resource management.
    """
    exchange_pool = {}
    setproctitle(f"Fullon queue for {exchange}")
    try:
        while True:
            request = request_queue.get()
            if request == "StopThisRun":
                break
            try:
                exchange, uid, params, method_name, method_params, response_queue = request
            except TypeError:
                break

            if uid not in exchange_pool:
                exchange_pool[uid] = ExchangeMethods(exchange=exchange, params=params)

            try:
                class_method = getattr(exchange_pool[uid], method_name)
                result = class_method(**method_params)
            except AttributeError as error:
                logger.error(f"Error processing a method, doesn't exist? ({str(error)}) ")
                result = None

            response_queue.put(result)

            if method_name not in exchange_pool[uid].no_sleep():
                logger.debug(f"Sleeping for: {method_name}")
                sleep(exchange_pool[uid].get_sleep())

    except KeyboardInterrupt:
        pass
    finally:
        stop_exchange(exchange_pool)
        mngr.shutdown()


def start(exchange: str) -> None:
    """Start the process for processing requests."""
    global request_queues, processes
    logger.info(f"Starting Exchange Queue Manager for {exchange}")
    mngr = Manager()
    request_queues[exchange] = mngr.Queue()
    processes[exchange] = Process(
        target=process_requests,
        args=(request_queues[exchange], exchange, mngr))
    processes[exchange].start()


def stop(exchange: str) -> None:
    """Stop the process for processing requests."""
    global response_queue_pool, request_queues, processes
    try:
        logger.info(f"Stopping Exchange Queue Manager for {exchange}")
        request_queues[exchange].put('StopThisRun')
        sleep(1)
        processes[exchange].join(timeout=1)
        del processes[exchange]
    except (KeyboardInterrupt, BrokenPipeError, KeyError):
        pass


def stop_all():
    """
    """
    global response_queue_pool
    with Cache() as store:
        exchanges = store.get_cat_exchanges()
    for exchange in exchanges:
        stop(exchange['name'])
    response_queue_pool = None


def start_all():
    """
    """
    setproctitle("Fullon Exchange Queue Launcher")
    with Cache() as store:
        exchanges = store.get_cat_exchanges()
    for exchange in exchanges:
        start(exchange['name'])


class Exchange:
    def __init__(self,
                 exchange: str,
                 params: Optional[ExchangeStruct] = None,
                 dry_run: bool = False):
        """
        Initialize the Exchange object.

        Args:
            exchange (str): Exchange name.
            params (Dict[str, Any], optional): Parameters for the exchange. Defaults to {}.
            dry_run (bool, optional): If True, enables dry run mode. Defaults to False.
        """
        self.dry_run = dry_run
        self.exchange = exchange
        self.params = params if params else self._get_params()
        self.uid = self.params.uid
        self.ex_id = self.params.ex_id

    def __del__(self):
        global NOQUEUE_POOL
        if self.exchange in NOQUEUE_POOL:
            del NOQUEUE_POOL[self.exchange]

    @staticmethod
    def _get_params():
        """
        Gets exchange params from test user, normally should be for testing
        """
        user = user_manager.UserManager()
        UID = user.get_user_id(mail=settings.ADMIN_MAIL)
        if UID:
            with database.Database() as dbase:
                try:
                    params = dbase.get_exchange(user_id=UID)[0]
                except IndexError:
                    params = []
        else:
            params = ExchangeStruct()
        return params

    def __getattr__(self, attr: str) -> Callable[..., Any]:
        """
        Provide a default implementation for any missing methods.

        Args:
            attr (str): Attribute name (method name).

        Returns:
            Callable[..., Any]: Default implementation of the missing method.
        """

        def default(**params: Dict[str, Any]) -> Any:
            try:
                return self._run_default(attr, params)
            except (KeyboardInterrupt, EOFError):
                return None
            '''
            except RuntimeError as error:
                logger.error("Can't release queue %s", str(error))
                return None
            '''

        return default

    def _run_default(self, attr: str, params: Dict[str, Any], timeout=360) -> Any:
        """
        Run the default implementation of a missing method.

        Args:
            attr (str): Attribute name (method name).
            params (Dict[str, Any]): Parameters for the missing method.
            timeout (int): Timeout for waiting for the worker to respond.

        Returns:
            Any: Result of the method execution.
        """
        global request_queues, response_queue_pool  # Consider avoiding global variables
        result = None
        with response_queue_pool.get_queue() as response_queue:
            try:
                # Place a request in the queue for the worker to process.
                request_queues[self.exchange].put(
                    (self.exchange, self.uid, self.params, attr, params, response_queue)
                )
            except KeyError as error:
                # Handle a missing queue for this exchange.
                raise WorkerError(f"Exchange queue for {self.exchange} not available or broken.")

            try:
                # Wait for the worker to process the request and get the result.
                result = response_queue.get(timeout=timeout)
            except Empty:
                logger.error("Worker timed out.")
                return None
            finally:
                if isinstance(result, tuple) and result[0] == SENTINEL:
                    # Handle any errors raised by the worker.
                    raise WorkerError(f"Error in worker process: {result[1]}")

        return result
