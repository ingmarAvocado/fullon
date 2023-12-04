from __future__ import unicode_literals, print_function
import pytest
from libs.database_ohlcv import Database
import datetime
from multiprocessing import Process


def test_get_latest_timestamp():
    with Database(exchange='kraken', symbol='BTC/USD') as dbase:
        ts = dbase.get_latest_timestamp()
        assert isinstance(ts, datetime.datetime)

    def execute():
        with Database(exchange='kraken', symbol='BTC/USD') as dbase:
            res = dbase.get_latest_timestamp()
            return res

    procs = {}
    for num in range(0, 8):
        process = Process(target=execute)
        process.start()
        procs[num] = process

    for num in procs.copy().keys():
        procs[num].join(timeout=4)


def test_test():
    with Database(exchange='kraken', symbol='BTC/USD') as dbase:
        ts = dbase.get_oldest_timestamp()
        assert isinstance(ts, datetime.datetime)

    def execute():
        with Database(exchange='kraken', symbol='BTC/USD') as dbase:
            res = dbase.get_oldest_timestamp()
            return res

    procs = {}
    for num in range(0, 8):
        process = Process(target=execute)
        process.start()
        procs[num] = process

    for num in procs.copy().keys():
        procs[num].join(timeout=4)
