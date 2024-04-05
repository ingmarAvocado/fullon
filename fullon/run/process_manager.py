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

    def check_services(self, stop_event):
        """
        Initiates a separate thread to periodically check if services need to be restarted.
        """
        def task(stop_event):
            while not stop_event.is_set():
                self._check_ohlcv_services()
                self._check_global_errors()
                for _ in range(int(CHECK_INTERVAL)):
                    if stop_event.is_set():
                        break
                    time.sleep(0.5)
        setproctitle("Fullon process checker")
        logger.info("Strating process monitor")
        task(stop_event)

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
        if failures:
            logger.info(f"Restarting all services")
            self.rpc.services('services', 'restart')

    def _check_ohlcv_services(self):
        """
        Checks the status of OHLCV fetching services and restarts them if necessary.
        """
        with cache.Cache() as store:
            processes = store.get_top(comp='ohlcv')
        now = arrow.utcnow().timestamp()
        counters = defaultdict(int)
        threads = defaultdict(int)
        restart = False
        exchange = None

        for proc in processes:
            ts1 = arrow.get(proc['timestamp']).timestamp()
            exchange = proc['key'].split(":")[0]
            threads[exchange] += 1
            if now - ts1 > LOGIC_RESTART_INTERVAL:
                counters[exchange] += 1

        for exchange, totals in threads.items():
            if totals == counters[exchange] and totals >= 1:
                restart = True
        if restart:
            logger.info(f"Restarting all services")
            self.rpc.services('services', 'restart')
