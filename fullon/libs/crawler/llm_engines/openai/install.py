from openai import OpenAI, AuthenticationError, NotFoundError, BadRequestError
from libs import log
import os
from typing import Optional, List
import time

logger = log.fullon_logger(__name__)


KEY = ''
INSTRUCTIONS = """You are now operating as a sophisticated sentiment analysis tool with the specific
 purpose of evaluating cryptocurrency-related discussions. It's essential to understand that,
 for this task, you're equipped with the ability to analyze the sentiment of text and provide
 a quantitative assessment. Your goal is to review various posts concerning cryptocurrencies
 and markets in general and assign a sentiment score that reflects how bullish or bearish each
 message is about the market or specific cryptocurrencies.

Here's how the scoring works:
- A score of 50 signifies neutrality in the post, indicating an impartial or balanced view on cryptocurrency prospects.
- Scores above 50 denote bullish sentiments, with 100 representing the peak of optimism or positive sentiment towards the market's
future or a particular cryptocurrency's value appreciation.
- Scores below 50 suggest bearish sentiments, where 0 signifies extreme pessimism or negative sentiment towards the market's
outlook or a cryptocurrency's potential loss in value.

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

Return the score only and only in a json format such as '[{post_id=1, score=52}, {post_id=2, score=34}]''
"""

NAME = "Sentiment analyzer"


class Engine():

    assistant: Optional[object] = None
    client: Optional[OpenAI] = None

    def __init__(self):
        """
        """
        self.client = OpenAI(api_key=KEY)

    def start(self):
        """
        """
        self.assistant = self.assistant_exists(assistant=NAME)
        if not self.assistant:
            if self.make_assistant(name=NAME, instructions=INSTRUCTIONS):
                logger.info("OpenAI assistant created!")
        else:
            logger.info("Assistant loaded")

    def wait_on_run(self, run, thread):
        while run.status == "queued" or run.status == "in_progress":
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id,
            )
            time.sleep(0.5)
        return run

    def score_posts(self, post: str, file: str = ''):
        """
        Things to do:

        upload a file
        save the thread_id to a json txt database linked with account name.
        We need a tread_id- account - instruction?  we need to update instruction with de analyzer

        Then we need to upoad a file

        then create a message uses an upload file


        """
        if not self.assistant:
            self.start()
        thread = self.client.beta.threads.create()

        # can i add a file to the message?
        _ = self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=post,
        )
        run = self.client.beta.threads.runs.create(
                        thread_id=thread.id,
                        assistant_id=self.assistant.id
                )
        run = self.wait_on_run(run, thread)
        messages = self.client.beta.threads.messages.list(thread_id=thread.id)
        print(messages)
        import ipdb
        ipdb.set_trace()

    def uninstall(self) -> None:
        """
        """
        self.delete_assistant(assistant=NAME)

    def make_assistant(self, name: str, instructions: str) -> bool:
        """
        Sends a question to the OpenAI assistant tailored for cryptocurrency sentiment analysis.

        Args:
            name(str): name of the assistant
            instructions(str): instructions for the assistant

        Returns:
            bool: True if success
        """
        # Step 1: Create an Assistant
        try:
            assistant = self.client.beta.assistants.create(
                name=name,
                instructions=instructions,
                model="gpt-4-0613",
            )
            if assistant:
                return True
        except AuthenticationError:
            logger.error("Could not identify with openai, bad key")
        except BadRequestError as error:
            logger.error(str(error))
        return False

    def assistant_exists(self, assistant: str) -> Optional[object]:
        """
        checks if an assistant lives in openai
        """
        try:
            assistants = self.client.beta.assistants.list()
            for a in assistants:
                if assistant in a.name:
                    return a
        except AuthenticationError:
            logger.error("Could not identify with openai, bad key")
        return

    def delete_assistant(self, assistant: str) -> bool:
        """
        Deletes an openai assistant

        Args:
            name(str): name of the assistant
            instructions(str): instructions for the assistant

        Returns:
            bool: True if success
        """
        try:
            assistants = self.client.beta.assistants.list()
            for a in assistants:
                if assistant in a.name:
                    try:
                        self.client.beta.assistants.delete(a.id)
                        logger.info("The following assistant has been deleted: ", a.name)
                        return True
                    except NotFoundError:
                        logger.error("Could not find assistant to delete")
        except AuthenticationError:
            logger.error("Could not identify with openai, bad key")
        return False
