"""
description
"""
import sys
import time
import json
import redis
import arrow
from munch import DefaultMunch
from libs import settings, log


class cache:

    """description"""
    db_cache = None
    _conn = None
    _timeout = 10
    _process_types = ['tick', 'ohlcv', 'account', 'bot', 'order']
    _bot_fields = ['bot_id',
                   'ex_id',
                   'bot_name',
                   'symbol',
                   'exchange',
                   'tick',
                   'roi',
                   'funds',
                   'totfunds',
                   'pos',
                   'pos_price',
                   'roi_pct',
                   'orders',
                   'message',
                   'live',
                   'strategy',
                   'base',
                   'params',
                   'variables']
    _test = False

    def __init__(self, test=False):
        """description"""
        self._test = test
        self.__init_redis()
        self._bot_fields.sort()

    def __del__(self):
        """description"""
        try:
            del self._conn
        except AttributeError:
            pass

    def __init_redis(self):
        """description"""
        self._conn = None
        param = True
        if settings.CACHE_HOST in ["localhost", "127.0.0.1"]:
            param = False
        self._conn = redis.Redis(host=settings.CACHE_HOST,
                                 port=settings.CACHE_PORT,
                                 db=settings.CACHE_DB,
                                 password=settings.CACHE_PASSWORD,
                                 socket_timeout=settings.CACHE_TIMEOUT,
                                 decode_responses=param, ssl=param)
        if not self.test():
            sys.exit("Cant connect to cache server. Exiting...")

    def test(self):
        """description"""
        try:
            self._conn.ping()
            return True
        except redis.exceptions.ConnectionError as error:
            mesg = f"Error, cant ping redis server ({str(error)})"
            logger.error(mesg)
            return False

    def get_bot_status(self, bot_id=None):
        """description"""
        if bot_id:
            data = {"bot_id": self._conn.hget("bot_status", bot_id)}
        else:
            data = self._conn.hgetall("bot_status")
        rows = []
        for _, values in data.items():
            obj = DefaultMunch.fromDict(json.loads(values))
            rows.append(obj)
        return rows

    def get_mini_top(self):
        """descripton"""
        rows = []
        for component in self._process_types:
            data = self._conn.hgetall(component)
            num = len(data)
            try:
                data = json.loads(data.popitem()[1])
                data = {"type": component,
                        "count":  num,
                        "message": data['message'],
                        "timestamp": data['timestamp']}
                rows.append(DefaultMunch.fromDict(data))
            except KeyError:
                pass
        return rows

    def get_user_strategy_params(self, bot_id):
        """returns the user's startegy params"""
        try:
            data = json.loads(self._conn.hget("bot_status", bot_id))
            return data['params']
        except TypeError:
            pass

    def get_bot_vars(self, bot_id):
        """returns the user's startegy params"""
        try:
            data = json.loads(self._conn.hget("bot_status", bot_id))
            return data['variables']
        except TypeError:
            pass
