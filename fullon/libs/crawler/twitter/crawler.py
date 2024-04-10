from apify_client import ApifyClient
from libs.crawler.apify.crawler import Crawler as rootCrawler
from libs.structs.crawler_post_struct import CrawlerPostStruct
from libs import log
import arrow

logger = log.fullon_logger(__name__)


class Crawler(rootCrawler):
    """
    Uses apify to connect to twitter and download posts
    """

    def get_posts(self, accounts: list, last: dict) -> list[CrawlerPostStruct]:
        """
        Retrieves a list of posts from specified Twitter accounts using the ApifyClient. 
        The method dynamically constructs search terms to fetch posts since a given timestamp, 
        with special handling for the 'CryptoDonAlt' account to fetch posts from the last three days 
        if no timestamp is provided for this account. Posts are fetched using Apify's actor and dataset services, 
        and each post's data is parsed and converted into CrawlerPostStruct instances.

        Args:
            accounts (list): A list of Twitter account usernames (str) from which to retrieve posts.
            last (dict): A dictionary mapping account usernames (str) to their corresponding last fetched post 
                         timestamps (str) in ISO 8601 format. If an account's last fetched timestamp is not 
                         provided, a default timestamp is used based on specific logic for 'CryptoDonAlt' or 
                         other accounts.

        Returns:
            list[CrawlerPostStruct]: A list of CrawlerPostStruct objects representing the retrieved posts. 
                                     Each CrawlerPostStruct object contains detailed information about a post, 
                                     including account, account_id, remote_id, site, content, timestamp, media, 
                                     and engagement metrics (views, likes, reposts, replies, followers), along 
                                     with flags indicating if a post is a reply and/or a self-reply.

        Raises:
            KeyError: If the 'last' dictionary does not contain an expected key for a given account, a KeyError 
                      might be caught, leading to a fallback timestamp being used. Other KeyErrors might occur 
                      during the parsing of post data from the Apify dataset.
        """
        search_terms = []
        for account in accounts:
            try:
                _last = arrow.get(last[account]).shift(seconds=1)
            except KeyError:
                _last = arrow.utcnow().floor('day').shift(days=-5)
            _last = _last.format("YYYY-MM-DD_HH:mm:ss_ZZZ")
            _until = arrow.utcnow().format("YYYY-MM-DD_HH:mm:ss_ZZZ")
            search_terms.append(f'from:{account} since:{_last} until:{_until}')
        client = ApifyClient(self.token)
        run_input = {
              "customMapFunction": "(object) => { return {...object} }",
              "includeSearchTerms": False,
              "maxItems": 5000,
              "minimumFavorites": 0,
              "minimumReplies": 0,
              "minimumRetweets": 0,
              "onlyImage": False,
              "onlyQuote": False,
              "onlyTwitterBlue": False,
              "onlyVerifiedUsers":  False,
              "onlyVideo": False,
              "searchTerms": search_terms,
              "sort": "Latest"
            }
        client.actor(self.actor).call(run_input=run_input)
        runs = client.actor(self.actor).runs()
        latest_run = runs.list().items[-1]
        posts = []
        downloads = []
        #for item in client.actor(self.actor).last_run().dataset().iterate_items():
        for item in client.dataset(latest_run["defaultDatasetId"]).iterate_items():
            try:
                timestamp = arrow.get(item['createdAt'], 'ddd MMM DD HH:mm:ss Z YYYY').format("YYYY-MM-DD HH:mm:ss.SSS")
                try:
                    media = item['extendedEntities']['media'][0]['media_url_https']
                    downloads.append({'id': int(item['id']), 'media': media})
                except KeyError:
                    media = ''
                self_reply = False
                is_reply = False
                reply_to = None
                author_id = int(item['author']['id'])
                try:
                    is_reply = bool(item['isReply'])
                    reply_to = int(item['inReplyToId'])
                    if author_id == int(item['entities']['user_mentions'][0]['id_str']):
                        self_reply = True
                except (KeyError, IndexError):
                    pass

                post = CrawlerPostStruct(
                    account=item['author']['userName'],
                    account_id=author_id,
                    remote_id=int(item['id']),
                    site='twitter',
                    content=item['text'],
                    timestamp=timestamp,
                    media=media,
                    media_ocr="",
                    urls="",
                    is_reply=is_reply,
                    reply_to=reply_to,
                    self_reply=self_reply,
                    views=item['viewCount'],
                    likes=item['likeCount'],
                    reposts=item['retweetCount'],
                    replies=item['replyCount'],
                    followers=item['author']['followers']
                )
                post.calculate_pre_score()
                posts.append(post)
            except KeyError as error:
                logger.error("Error parsing a post. missing a Key ", str(error))
        return posts
