from multiprocessing import Manager
from contextlib import contextmanager
import time

MAX_QUEUES = 50  # Maximum number of queues allowed in the pool
RETRIES = 60


class QueuePool:
    def __init__(self):
        self.allocated_queues = {}
        self.counter = 0

    @contextmanager
    def get_queue(self, retries=RETRIES):
        """
        Context manager for safely getting and releasing a queue.
        """
        if self.counter >= MAX_QUEUES:
            time.sleep(1)
            retries -= 1
            if retries > 0:
                return self.get_queue(retries=retries)
            raise RuntimeError("Maximum queue limit reached")

        new_queue = Manager().Queue()
        self.allocated_queues[self.counter] = new_queue
        self.counter += 1

        try:
            yield new_queue  # yield the queue for use within the 'with' block
        finally:
            self.release_queue()  # release the queue when exiting the 'with' block

    def release_queue(self):
        """
        Release the last queue that was allocated.
        """
        if self.counter > 0:
            self.counter -= 1
            del self.allocated_queues[self.counter]
