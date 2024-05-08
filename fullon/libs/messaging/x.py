"""
Simple class posts message on twitter
"""
import tweepy
from libs import settings, log
from typing import Optional

logger = log.fullon_logger(__name__)


class Messenger():
    """ main class definition"""
    _client: object
    _clientv1: object
    _reset: bool

    def __init__(self):
        """
        Init method. Instantiates tweepy

        Args:
            reset:Bool Will download data again and save it as pickle
        """
        auth = tweepy.OAuth1UserHandler(settings.X_API_KEY, settings.X_API_SECRET)
        auth.set_access_token(
            settings.X_ACCESS_TOKEN,
            settings.X_ACCESS_SECRET,
        )
        self._clientv1 = tweepy.API(auth)
        self._client = tweepy.Client(
                            consumer_key=settings.X_API_KEY,
                            consumer_secret=settings.X_API_SECRET,
                            access_token=settings.X_ACCESS_TOKEN,
                            access_token_secret=settings.X_ACCESS_SECRET)

    def get_user_name(self, uid: int):
        """ Gets a user handle from an id

        Args:
            uid: twiiter user account id, int

        Returns:
            strings containing handle
        """
        try:
            result = self._client.get_user(id=uid, user_auth=True)
        except tweepy.errors.Unauthorized:
            logger.error("Not authorized")
            return
        except tweepy.errors.TooManyRequests:
            logger.error("Too many requests, try later")
            return
        except tweepy.errors.BadRequest:
            logger.error("Value of paramenter uid (%s) not valid", uid)
            return
        try:
            return result.data.username
        except AttributeError:
            return


    def get_me(self):
        """ Gets a user handle from an id

        Args:
            uid: twiiter user account id, int

        Returns:
            strings containing handle
        """
        try:
            result = self._client.get_me()
        except tweepy.errors.Unauthorized:
            logger.error("Not authorized")
            return
        except tweepy.errors.TooManyRequests:
            logger.error("Too many requests, try later")
            return
        except tweepy.errors.BadRequest:
            logger.error("Value of paramenter uid (%s) not valid", uid)
            return
        try:
            return result.data.username
        except AttributeError:
            return

    def get_user_id(self, username: str) -> str:
        """
        Gets a user id from a handle

        Args:
            username:  twitter user handle

        Returns:
            strings containing handle
        """
        try:
            result = self._client.get_user(username=username, user_auth=True)
        except tweepy.errors.Unauthorized:
            logger.error("Not authorized")
            return ''
        except tweepy.errors.TooManyRequests:
            logger.error("Too many requests, try later")
            return ''
        except tweepy.errors.BadRequest:
            logger.error("Value of paramenter username (%s) not valid",
                          username)
            return ''
        try:
            return result.data.id
        except AttributeError:
            return ''

    def post(self, post: str, media_path: str = '') -> Optional[int]:
        """
        Publish a post

        Args:
            post: Content of the tweet
            media_path: String with path of media to upload

        Returns:
            int: Twitt id else None
        """
        try:
            # Attempt to publish the tweet
            if media_path:
                media_id = self.upload_media(media_path=media_path)
                response = self._client.create_tweet(text=post, media_ids=[media_id])
            else:
                response = self._client.create_tweet(text=post)
            if response:
                logger.info(f"Tweet posted successfully: {response.data}")
                return response[0]['id']
        except tweepy.errors.Forbidden as e:
            # Handles cases where the operation is forbidden, like tweet duplication
            logger.error(f"Failed to post tweet due to permission issue: {e}")
        except tweepy.errors.TooManyRequests as e:
            # Handle rate limit scenarios
            logger.error("Too many requests sent. Please wait and try again later.")
        except tweepy.errors.TwitterServerError as e:
            # Handle server errors from Twitter
            logger.error("Twitter server error occurred.")
        except Exception as e:
            # General exception for any other errors
            logger.error(f"An error occurred: {e}")
        return

    def upload_media(self, media_path: str):
        """
        """
        media = self._clientv1.media_upload(filename=media_path)
        return media.media_id

    def delete_post(self, post_id: str) -> bool:
        """
        Publish a post

        Args:
            post: Content of the tweet

        Returns:
            bool: True if the tweet was posted successfully, False otherwise
        """
        try:
            # Attempt to publish the tweet
            response = self._client.delete_tweet(post_id)
            if response:
                logger.info(f"Tweet deleted successfully: {response.data}")
                return True
        except tweepy.errors.Forbidden as e:
            # Handles cases where the operation is forbidden, like tweet duplication
            logger.error(f"Failed to post tweet due to permission issue: {e}")
        except tweepy.errors.TooManyRequests as e:
            # Handle rate limit scenarios
            logger.error("Too many requests sent. Please wait and try again later.")
        except tweepy.errors.TwitterServerError as e:
            # Handle server errors from Twitter
            logger.error("Twitter server error occurred.")
        except Exception as e:
            raise
            # General exception for any other errors
            logger.error(f"An error occurred: {e}")
        return False