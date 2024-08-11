"""
Process Manager
"""
import time
import xmlrpc.client
from setproctitle import setproctitle
from libs import settings, cache, log
from typing import List, Dict, Optional
import arrow
from collections import defaultdict
import threading


logger = log.fullon_logger(__name__)

CHECK_INTERVAL = 30  # Seconds
LOGIC_RESTART_INTERVAL = 60*5  # Seconds
# LOGIC_RESTART_INTERVAL = 1  # Seconds, equivalent to 5 minutes
TICKER_DELAY = 120
OHLCV_DELAY = 120


class ProcessManager:
    """
    Manages and monitors the state of various services, ensuring they are running optimally.
    It interfaces with services through XML-RPC and utilizes a cache for storing service data.
    """

    def __init__(self):
        """
        Initializes the ProcessManager with an XML-RPC server proxy and prepares threading components.
        """
        self.rpc = xmlrpc.client.ServerProxy(f'http://{settings.XMLRPC_HOST}:{settings.XMLRPC_PORT}')
        self.services_thread: Optional[threading.Thread] = None

    def __del__(self):
        """
        Ensures that resources are cleaned up when the instance is being destroyed.
        """
        self.stop()

    def stop(self):
        """
        Signals the monitoring thread to stop and waits for it to join back.
        """
        if self.services_thread and self.services_thread.is_alive():
            self.services_thread.join(timeout=1)  # Wait for the thread to finish with a timeout

    def get_top(self) -> List[Dict]:
        """
        Retrieves the top services from the cache, excluding their 'params'.

        Returns:
            List[Dict]: A list of dictionaries representing top services with their attributes, excluding 'params'.
        """
        with cache.Cache() as store:
            data = store.get_top()
        return [{k: v for k, v in d.items() if k != 'params'} for d in data]

    def check_services(self, stop_event, test: bool = False):
        """
        Initiates a separate thread to periodically check if services need to be restarted.
        """
        def task(stop_event, test):
            while not stop_event.is_set():
                logger.debug("Checking services to see if they are alive")
                service_errors: dict = self.check_tickers()
                service_errors.update(self.check_accounts())
                service_errors.update(self.check_ohlcv())
                global_errors: list = self._check_global_errors()
                self._restart_services(service_errors=service_errors,
                                       global_errors=global_errors)
                if test:
                    break
                for _ in range(int(CHECK_INTERVAL)):
                    if stop_event.is_set():
                        break
                    time.sleep(0.5)
        setproctitle("Fullon process checker")
        logger.info("Strating process monitor")
        count = 0
        while not stop_event.is_set():
            response = 'No response'
            try:
                response = self.rpc.rpc_test()
                if "fullon" in str(response):
                    logger.info("Connected to RPC server")
                    task(stop_event, test)

            except ConnectionRefusedError:
                logger.warning("Can't connect to RPC server, trying again.")
                time.sleep(10)
            count += 1
            if count == 20:
                logger.error("Can't connect to rpc server for some reason")
                break
            if test:
                break

    def _restart_services(self, service_errors: dict, global_errors: list):
        """
        Restart services for exchanges that have encountered errors.
        :param service_errors: Dictionary of service errors, where keys are service names and values are exchanges
        :param global_errors: List of global errors (not used in this function)
        :return: None
        """
        if service_errors:
            # List of basic services (not used in this function, consider removing if unnecessary)
            basic_services = ['tick_service', 'tickers', 'ohlcv']
            # Create a set of unique exchanges that need service restart
            restart_set = set()
            for exchanges in service_errors.values():
                # Check if exchanges is a list (multiple exchanges) or a single exchange
                if isinstance(exchanges, list):
                    restart_set.update(exchanges)
                else:
                    restart_set.add(exchanges)
            # Restart services for each exchange in the set
            for exchange in restart_set:
                logger.warning(f"Restarting services for exchange {exchange}")
                self.rpc.restart_exchange(exchange)
        return None

    def _check_global_errors(self):
        """
        Checks cache queue to see if there was an error

        """
        failures = []
        with cache.Cache() as store:
            while True:
                failure = store.pop_global_error()
                if not failure:
                    break
                failures.append(failure)
        return failures
        if failures:
            logger.info(f"Restarting all services")
            try:
                self.rpc.services('services', 'restart')
            except ConnectionRefusedError:
                logger.error("Can't connect to RPC server")
                time.sleep(1)
            except xmlrpc.client.Fault:
                logger.error("XMLRPC couldnt iterate response")
        return failers

    def check_accounts(self) -> Dict:
        """
        Checks the status  of api account fetchers
        """
        return {}

    def check_ohlcv(self) -> Dict:
        """
        Checks the status of api ohlcv fetchers
        """
        keys = []
        with cache.Cache() as store:
            statuses = store.get_all_trade_statuses()
        for exchange, timestamp in statuses.items():
            timestamp = arrow.get(timestamp)
            if (arrow.utcnow() - timestamp).total_seconds() > OHLCV_DELAY:
                key = exchange.split(":")[-1]
                keys.append(key)
            keys = list(set(keys))
        return {'ohlcv': keys}

    def check_tickers(self) -> Dict:
        """
        Check the status of OHLCV fetching services and identify issues.

        Returns:
            A dictionary of errors, where keys are error types and values
            are dictionaries containing error details.
        """
        errors: Dict[str, List] = {'tick_service': [], 'ticker': []}
        with cache.Cache() as store:
            crawlers = store.get_tick_crawlers()
        for exchange, params in crawlers.items():
            errors = self._check_tick_service(exchange=exchange, params=params,  errors=errors)
            errors = self._check_tickers(exchange=exchange, errors=errors)
        for error in list(errors.keys()):
            if len(errors[error]) == 0:
                del errors[error]
        return errors

    def _check_tick_service(self, exchange: str,  params: Dict,  errors: Dict) -> Dict:
        """Check if the tick service is running within the expected timeframe."""
        try:
            timestamp = arrow.get(params['timestamp']).timestamp()
            if arrow.utcnow().timestamp() - timestamp > TICKER_DELAY:  # 5 minutes
                errors['tick_service'].append(exchange)
        except (KeyError, ValueError):
            errors['tick_service'].append(exchange)
        return errors

    def _check_tickers(self, exchange: str,  errors: Dict) -> Dict:
        """Check if tickers are being updated within the expected timeframe."""
        with cache.Cache() as store:
            tickers = store.get_tickers(exchange=exchange)
        if not tickers:
            return errors
        most_recent = max(
            (arrow.get(tick.time) for tick in tickers),
            default=arrow.get(0)
        )
        if (arrow.utcnow() - most_recent).total_seconds() > TICKER_DELAY:  # 2 minutes
            errors['ticker'].append(exchange)
        return errors
