"""
Cache class for managing caching operations with Redis.
The Cache class provides functionality to interact with
a Redis cache server, including creating, updating,
and retrieving cache entries. It also includes utility
methods for testing the connection to the cache server,
preparing the cache, and filtering cache entries based
on timestamps and component types.
"""

from libs.caches import bot_cache as cache

'''
try:
    EXCHANGES_DIR = os.listdir('exchanges/')
except FileNotFoundError:
    EXCHANGES_DIR = os.listdir('fullon/exchanges/')
'''


class Cache(cache.Cache):
    pass
