"""
Cache class for managing caching operations with Redis.
The Cache class provides functionality to interact with
a Redis cache server, including creating, updating,
and retrieving cache entries. It also includes utility
methods for testing the connection to the cache server,
preparing the cache, and filtering cache entries based
on timestamps and component types.
"""

from libs.caches import crawler_cache


class Cache(crawler_cache.Cache):
    pass
