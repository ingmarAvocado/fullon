from openai import OpenAI, AuthenticationError, NotFoundError, BadRequestError, APIConnectionError, InternalServerError
from libs import log, settings
from libs.structs.crawler_post_struct import CrawlerPostStruct
from typing import Optional, List
import time
import base64
import requests
import json

logger = log.fullon_logger(__name__)

MODEL = 'llama-3-sonar-large-32k-chat'

INSTRUCTIONS = """
Please respond with the scores in the following JSON format:
[{"post_id": "1", "score": "52"}, {"post_id": "2", "score": "-34"}]
You are now operating as a sophisticated sentiment analysis tool with the specific
 purpose of evaluating cryptocurrency-related discussions. It's essential to understand that,
 for this task, you're equipped with the ability to analyze the sentiment of text and provide
 a quantitative assessment. Your goal is to review various posts concerning cryptocurrencies
 and markets in general and assign a sentiment score that reflects how bullish or bearish each
 message is about the market or specific cryptocurrencies.

Here's how the scoring works:
- A score of 0 signifies neutrality in the post, indicating an impartial or balanced view on cryptocurrency prospects.
- Scores above 0 denote bullish sentiments, with 100 representing the peak of optimism or positive sentiment towards the market's
future or a particular cryptocurrency's value appreciation.
- Scores below 0 suggest bearish sentiments, where -100 signifies extreme pessimism or negative sentiment towards the market's
outlook or a cryptocurrency's potential loss in value .

It's important to "act as if" you can precisely evaluate these
sentiments and generate scores based on the content you analyze.
Approach each post with an objective lens, focusing solely on the
sentiment conveyed regarding the cryptocurrency market or specific
assets. For instance, if a post displays confidence in Bitcoin's
growth, you might rate it highly to reflect strong bullish sentiment.
Conversely, if another predicts a decline in Ethereum due to external factors,
assign a lower score to represent bearish sentiment. Take into considerations
stuff like ETF outbounds, inbounds, or crypto movements in or out of exchanges
(out is bullish, in is bearish), if its stocks if there is inside selling
or if a  politician is doing a trade.

Assume this capability is within your function, and perform the
sentiment scoring with accuracy and confidence, as described.
Your task is not only to understand the text but to simulate sentiment analysis accurately,
providing scores that investors might use to gauge market sentiment.

I give you a tip if you return the score only and only in a json format such as [{"post_id": "1", "score": "52"}, 
{"post_id": "2", "score": "-34"}] you must return your answer like that.

if the text doesnt make any sense when rating a post for instance if it says 'hello' or "I don't think so. But I like to be surprised"
yout must return the json... in those weird cases you can't make sense return score 0

"""

NAME = "Sentiment analyzer"


class Engine():

    client: Optional[OpenAI] = None

    def __init__(self):
        """
        setups Engine class
        """
        self.client = OpenAI(api_key=settings.PERPLEXITY_KEY, base_url="https://api.perplexity.ai")

    def score_post(self, post: CrawlerPostStruct) -> Optional[float]:
        """
        receives a post and tryes to get a score from openai assistant

        Args:
            post (CrawlerPostStruct): a Post to score

        returns:
            str: Score of the post
        """
        time.sleep(1)  # lets throttle a little bit
        content = post.content
        if post.media:
            content += f"this post includes_image with the following OCR {post.media_ocr}"
        messages = [
            {
                "role": "system",
                "content": (
                    f"{INSTRUCTIONS}"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{content}"
                ),
            },
        ]
        try:
            # chat completion without streaming
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=messages,
            )
        except:
            time.sleep(5)
            return None
        try:
            if response:
                ret_dict = json.loads(response.choices[0].message.content)[0]
                return float(ret_dict['score'])
        except (TypeError, KeyError):
                logger.error("Did not get a json score from engine perplexity")
                return None
        return None

