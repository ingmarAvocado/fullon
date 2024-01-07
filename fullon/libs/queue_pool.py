from multiprocessing import Manager
from contextlib import contextmanager


class QueuePool:
    def __init__(self):
        self.manager = Manager()

    @contextmanager
    def get_queue(self):
        """
        Context manager for safely getting and releasing a queue.
        """
        queue = self.manager.Queue()
        try:
            yield queue
        finally:
            del queue  # Assuming the queue will be garbage collected
