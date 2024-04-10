from multiprocessing import Manager
from contextlib import contextmanager
from setproctitle import setproctitle


class QueuePool:
    def __init__(self, procname: str = "unknown"):
        setproctitle("Fullon queue manager for: "+procname)
        self.manager = Manager()
        setproctitle("Fullon Daemon")

    @contextmanager
    def get_queue(self):
        """
        Context manager for safely getting and releasing a queue.
        """
        queue = None
        try:
            queue = self.manager.Queue()
            yield queue
        except ConnectionRefusedError:
            exit()
        finally:
            del queue  # Assuming the queue will be garbage collected
