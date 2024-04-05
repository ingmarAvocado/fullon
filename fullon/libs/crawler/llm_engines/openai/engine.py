from openai import OpenAI, AuthenticationError, NotFoundError, BadRequestError, APIConnectionError
from libs import log, settings
from libs.structs.crawler_post_struct import CrawlerPostStruct
from typing import Optional, List
import time
import base64
import requests
import json

logger = log.fullon_logger(__name__)

ENGINE = 'gpt-3.5-turbo-0125'
VISION_ENGINE = 'gpt-4-1106-vision-preview'

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
        setups Engine class
        """
        self.client = OpenAI(api_key=settings.GRANDESMODELOS1)

    def start(self):
        """
        Starts an Assistant
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

    def _analyze_image(self, file: str) -> str:
        """
        Uses openAI vision to analyze an image and get feedback

        """
        # Function to encode the image
        def encode_image(file):
            file = settings.IMAGE_DIR+"/"+file
            try:
                with open(file, "rb") as image_file:
                    return base64.b64encode(image_file.read()).decode('utf-8')
            except FileNotFoundError:
                return ""

        # Getting the base64 string
        base64_image = encode_image(file=file)
        if not base64_image:
            msg = f"Could not find image file: {file}"
            logger.error(file)
            return ''

        headers = {
          "Content-Type": "application/json",
          "Authorization": f"Bearer {KEY}"
        }

        payload = {
          "model": "gpt-4-vision-preview",
          "messages": [
            {
              "role": "user",
              "content": [
                {
                  "type": "text",
                  "text": "Describe this image in the context of market analysis, we are looking to see if its bullish or bearish"
                },
                {
                  "type": "image_url",
                  "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                  }
                }
              ]
            }
          ],
          "max_tokens": 300
        }

        response = requests.post("https://api.openai.com/v1/chat/completions",
                                 headers=headers, json=payload)
        response = response.json()
        return response['choices'][0]['message']['content']

    def _load_thread(self, account_id: int) -> Optional[object]:
        """
        checks if a thread has been created for an account id, if it has it loads that one
        if it hasnt, it creates a new thread

        Args:
            account_id (int):

        Return:
            Optional object returns object if found None if not and cannot create

        """
        thread_id = None
        file_paths = ['txt_dbs/account_threads.txt', 'fullon/text_dbs/account_threads.txt']
        file_found_path = ''

        # Try to find the existing thread_id from the file in known directories
        for path in file_paths:
            try:
                with open(path, 'r') as file:
                    for line in file:
                        _account_id, _thread_id = line.strip().split(',')
                        if int(_account_id) == account_id:
                            thread_id = _thread_id
                            file_found_path = path  # Remember where we found the file
                            break
            except FileNotFoundError:
                continue  # Try the next path if the file wasn't found
            if thread_id:  # Exit the loop early if we found the thread_id
                break

        # Load or create the thread based on whether a thread_id was found
        if thread_id:
            thread = self.client.beta.threads.retrieve(thread_id)
        else:
            thread = self.client.beta.threads.create()
            # Decide where to save the new entry based on whether we found the file earlier
            save_path = file_found_path if file_found_path else file_paths[0]  # Default to the first path if the file wasn't found
            with open(save_path, 'a') as file:
                file.write(f"{account_id},{thread.id}\n")
        return thread

    def score_post(self, post: CrawlerPostStruct) -> str:
        """
        receives a post and tryes to get a score from openai assistant

        Args:
            post (CrawlerPostStruct): a Post to score

        returns:
            str: Score of the post
        """

        if not self.assistant:
            self.start()
        thread = self._load_thread(account_id=post.account_id)
        if thread:
            post_dict = {'post_text': post.content, 'includes_image': 'no'}
            if post.media:
                image_description = self._analyze_image(file=post.media)
                post_dict['includes_image'] = 'yes'
                post_dict['image_description'] = image_description
            _ = self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=json.dumps(post_dict),
            )

            run = self.client.beta.threads.runs.create(
                            thread_id=thread.id,
                            assistant_id=self.assistant.id
                    )
            run = self.wait_on_run(run, thread)
            message = self.client.beta.threads.messages.list(thread_id=thread.id)
            try:
                if message:
                    return json.loads(message.data[0].content[0].text.value)['score']
            except (TypeError, KeyError):
                logger.error("Did not get a json score from engine")
                return ''
        else:
            logger.error("Could not score post")
        return ''

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
            self.assistant = self.client.beta.assistants.create(
                name=name,
                instructions=instructions,
                model=ENGINE,
            )
            if self.assistant:
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
        except APIConnectionError:
            logger.error("Error connecting to the API")
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

    def get_engines(self):
        """
        Gets available openai enginles
        """
        return self.client.models.list()
