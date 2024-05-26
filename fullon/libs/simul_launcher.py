from typing import Any, Dict, Optional
from multiprocessing import Process, Manager, Queue
from setproctitle import setproctitle
from libs import log
from libs.bot import Bot  # import your Bot class

# Setup logging
logger = log.fullon_logger(__name__)
WORKERS = 6


class FullonSimulator:

    def __init__(self):
        self.request_queue: Optional[Queue] = None
        self.processes: Dict[int, Process] = {}
        self.started = False

    @staticmethod
    def process_requests(request_queue: Queue):
        setproctitle(f"Fullon simulator server")
        while True:
            try:
                bot_id, leverage, fee, periods, visual, event, noise, feeds, warm_up, test_params, response_queue = request_queue.get()
                bot = Bot(bot_id=bot_id, bars=periods)
                results = bot.run_simul_loop(visual=visual, event=event,
                                             feeds=feeds, warm_up=warm_up,
                                             test_params=test_params,
                                             noise=noise, leverage=leverage, fee=fee)
                del bot
                response_queue.put(results)
            except KeyboardInterrupt:
                #response_queue.put(None)
                return
            except (BrokenPipeError, EOFError, ConnectionResetError, FileNotFoundError) as error:
                print(error)
                #response_queue.put(None)
                return
            except TypeError as error:
                raise
                logger.error(f"Type error: {error}")

    def start(self):
        global WORKERS
        if not self.started:
            mngr = Manager()
            self.request_queue = mngr.Queue()
            for num in range(0, WORKERS):
                self.processes[num] = Process(target=self.process_requests, args=(self.request_queue,))
                self.processes[num].start()
            self.started = True

    def stop(self):
        for _, process in self.processes.items():
            process.terminate()
        self.request_queue = None
        self.processes = {}
        self.started = False

    def new_queue(self):
        """
        responds with a multiprocess queue
        """
        mngr = Manager()
        return mngr.Queue()

    def get_request_queue(self):
        return self.request_queue


simulator = FullonSimulator()
