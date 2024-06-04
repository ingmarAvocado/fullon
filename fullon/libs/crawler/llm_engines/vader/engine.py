from libs import log, settings
from libs.structs.crawler_post_struct import CrawlerPostStruct
from typing import Optional, List
import time
import base64
import requests
import json
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = log.fullon_logger(__name__)


class Engine():

    def __init__(self):
        """
        setups Engine class
        """
        self._analyzer = SentimentIntensityAnalyzer()

    def score_post(self, post: CrawlerPostStruct) -> float:
        """
        receives a post and tryes to get a score from openai assistant

        Args:
            post (CrawlerPostStruct): a Post to score

        returns:
            str: Score of the post
        """
        content = post.content
        
        #if 'btc' in content.lower() or 'bitcoin' in content.lower():
        analytic = self._analyzer.polarity_scores(content)
        #else:
        #    return 0

        neu = analytic['neu']
        neg = analytic['neg']
        pos = analytic['pos']
        comp = analytic['compound']
        return comp*100
        '''
        if neu > neg and neu > pos:
            return 0
        elif neg > pos and neg > neu:
            return abs(comp)*100*-1
        elif pos > neg and pos > neu:
            return comp*100
        '''
