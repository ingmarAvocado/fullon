from apify_client import ApifyClient
from libs import log, settings
import urllib.request
import urllib.error
import os
import concurrent.futures
from urllib.parse import urlparse, unquote
from libs.structs.crawler_post_struct import CrawlerPostStruct
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import numpy as np
from typing import Union, List

logger = log.fullon_logger(__name__)


class Crawler():
    """
    Uses apify to connect to twitter and download posts
    """

    def __init__(self):
        """
        init apify keys
        """
        self.token = settings.APIFY_TOKEN
        self.actor = settings.APIFY_ACTOR_TWITTER

    def preprocess_image(self, image_path) -> Image:
        """
        Lets preprocess teh image and improve it for OCR
        """
        img = Image.open(image_path)
        img = img.convert('L')  # Convert to grayscale
        img = img.resize((img.width * 2, img.height * 2))  # Resize to double the original size
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2)  # Increase contrast
        img = img.filter(ImageFilter.SHARPEN)  # Sharpen the image
        return img

    def image_ocr(self, image_path: str) -> str:
        """Returns OCR string extracted from image path

        Args:
            image_path (str): image path

        Returns:
            str: OCR string
        """
        try:
            img = self.preprocess_image(image_path=image_path)
            ocr_text = pytesseract.image_to_string(img)
            return ocr_text.replace("\n", " ").replace("|", "I")
        except Exception as e:
            logger.error(f"OCR processing error: {e}")
            return ""

    def download_media(self, url: str, name: str, ocr = False) -> str:
        """Download media from URL, save it, and return OCR text from the image.

        Args:
            url (str): URL to download from.
            name (str): Filename to save with, including the extension. The file will be saved under the directory specified by settings.IMAGE_DIR.

        Returns:
            str: OCR string extracted from the downloaded image.
        """
        try:
            os.makedirs(settings.IMAGE_DIR, exist_ok=True)
            file_path = os.path.join(settings.IMAGE_DIR, name)
            # Check if the file already exists
            if not os.path.isfile(file_path):
                # Download the file if it doesn't exist
                with open(file_path, 'wb') as f, urllib.request.urlopen(url) as response:
                    f.write(response.read())
                logger.debug(f"Downloaded media from {url} to {file_path}.")
            else:
                logger.debug(f"Media already exists: {file_path}, skipping download.")

            # Perform OCR on the downloaded or existing image
            if ocr:
                ocr_text = self.image_ocr(file_path)
                logger.debug(f"Performed OCR on {file_path}.")
                return ocr_text
        except urllib.error.HTTPError as err:
            logger.debug(f"Problem downloading/saving media from {url}: {err}")
        except Exception as e:
            logger.debug(f"Error during OCR processing for {file_path}: {e}")
        return ""

    def download_medias(self,
                        posts: list[CrawlerPostStruct],
                        ocr: bool = True,
                        max_simultaneous_downloads: int = 4) -> list[CrawlerPostStruct]:
        """
        Downloads media in parallel using ThreadPoolExecutor, for posts that have media, and updates the posts list
        with the new filename and OCR text.

        Args:
            posts (list[CrawlerPostStruct]): List containing CrawlerPostStruct objects representing download tasks.
            max_simultaneous_downloads (int): Maximum number of simultaneous downloads.

        Returns:
            list[CrawlerPostStruct]: Updated list of posts with `.media` and `.media_ocr` fields updated.
        """

        def get_filename_from_url(url, media_id):
            """Generate a filename from the media URL and ID, preserving the original extension."""
            parsed_url = urlparse(url)
            base_name = os.path.basename(unquote(parsed_url.path))
            _, ext = os.path.splitext(base_name)
            if not ext:
                ext = '.jpg'  # Default extension; adjust as needed.
            return f"{media_id}{ext}"

        def download_and_ocr(post,  ocr):
            """Download media, perform OCR, and update post."""
            filename = get_filename_from_url(post.media, str(post.remote_id))
            ocr_text = self.download_media(post.media, filename, ocr)
            # Update post fields
            post.media = filename  # Update .media with the new filename
            post.media_ocr = ocr_text  # Update .media_ocr with OCR text
            return post

        # Use ThreadPoolExecutor to download media and perform OCR in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_simultaneous_downloads) as executor:
            # Submit all posts with media for processing
            future_to_post = {executor.submit(download_and_ocr, post, ocr): post for post in posts if post.media}
            # Wait for all futures to complete
            for future in concurrent.futures.as_completed(future_to_post):
                try:
                    # This block intentionally left empty; updates are made in-place to post objects
                    pass
                except Exception as exc:
                    logger.error(f"Exception occurred: {exc}")

        return posts  # Return the updated list of posts
