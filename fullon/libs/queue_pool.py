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
        queue = None
        try:
            queue = self.manager.Queue()
            yield queue
        except ConnectionRefusedError:
            exit()
        finally:
            del queue  # Assuming the queue will be garbage collected
