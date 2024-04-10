"""
Cache class for managing caching operations with Redis.
The Cache class provides functionality to interact with
a Redis cache server, including creating, updating,
and retrieving cache entries. It also includes utility
methods for testing the connection to the cache server,
preparing the cache, and filtering cache entries based
on timestamps and component types.
"""

import json
from libs import log
from libs.database import Database
from libs.caches import bot_cache as cache
from typing import List


logger = log.fullon_logger(__name__)


class Cache(cache.Cache):
    """
    A class for managing caching operations with Redis.
    Attributes:
    """

    def get_crawling_list(self, site) -> List[str]:
        """
        Fetch a list of crawl sites from Redis cache or PostgreSQL.
        If the data is not in Redis cache, it will be fetched from PostgreSQL and cached in Redis.

        Returns:
            List[Tuple[str, str]]: A list of site and account tuples.
        """
        # Adjusted Redis key to include site for unique key per site
        redis_key = f'crawler_list:{site}'
        crawlers = []  # Initialize an empty list to hold the crawler data

        # Check if the data is in Redis cache
        if self.conn.exists(redis_key):
            # Data is in Redis, fetch and decode it
            crawlers_json = self.conn.get(redis_key)
            if crawlers_json:
                crawlers = json.loads(crawlers_json)
        else:
            # Data is not in Redis, fetch from the database
            with Database() as dbase:  # Replace with your actual database connection handling
                crawlers = dbase.get_crawling_list(site=site)  # Fetch the data from PostgreSQL
                # Assuming rows are fetched as a list of tuples
                self.conn.set(redis_key, json.dumps(crawlers))
                self.conn.expire(redis_key, 24 * 60 * 60)  # Set expiry for 24 hours
        return crawlers

    def get_crawling_sites(self) -> List[str]:
        """
        Fetch a list of crawl sites from Redis cache or PostgreSQL.
        If the data is not in Redis cache, it will be fetched from PostgreSQL and cached in Redis.

        Returns:
            List[Tuple[str, str]]: A list of site and account tuples.
        """
        # Adjusted Redis key to include site for unique key per site
        redis_key = f'crawler_sites'
        crawlers = []  # Initialize an empty list to hold the crawler data

        # Check if the data is in Redis cache
        if self.conn.exists(redis_key):
            # Data is in Redis, fetch and decode it
            crawlers_json = self.conn.get(redis_key)
            if crawlers_json:
                crawlers = json.loads(crawlers_json)
        else:
            # Data is not in Redis, fetch from the database
            with Database() as dbase:  # Replace with your actual database connection handling
                crawlers = dbase.get_crawler_sites(all=True)  # Fetch the data from PostgreSQL
                # Assuming rows are fetched as a list of tuples
                self.conn.set(redis_key, json.dumps(crawlers))
                self.conn.expire(redis_key, 24 * 60 * 60)  # Set expiry for 24 hours
        return crawlers
