#!/usr/bin/python3
"""
Runs fullon_daemon
"""
#from signal import signal, SIGINT
from threading import Thread
from libs import log, settings
from libs.settings_config import fullon_settings_loader  # pylint: disable=unused-import
from libs.exchange import start_all
from setproctitle import setproctitle
import time

logger = log.fullon_logger(__name__)
thread: Thread

start_all()
setproctitle("fullon test")
time.sleep(10000)
