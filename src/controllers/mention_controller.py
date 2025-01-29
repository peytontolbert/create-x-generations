import logging
import asyncio
import random
from datetime import datetime
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
import os
import requests
from pathlib import Path

logger = logging.getLogger(__name__)


class MentionController:
    def __init__(self, handler, memory, create_api, create_agent):
        self.handler = handler
        self.memory = memory
        self.create_api = create_api
        self.create_agent = create_agent
        self.logger = logging.getLogger(__name__)

    async def process_mentions(self):
        """Process mentions using tweet IDs as unique identifiers"""
        try:
            self.logger.info("\nProcessing mentions")

            # Navigate to mentions
            await self.navigate_to_mentions()

            # Get all mention tweets
            mentions = await self.get_mentions()
            if not mentions:
                self.logger.info("No mentions found")
                return True

            self.logger.info(f"Found {len(mentions)} mentions")

            # Process each mention
            for mention in mentions:
                try:
                    # Get tweet ID and handle from the element
                    tweet_id = await self.get_tweet_id(mention)
                    handle = await self.get_handle_from_mention(mention)

                    if not tweet_id or not handle:
                        self.logger.debug("Could not get tweet ID or handle, skipping")
                        continue

                    # Skip if we already replied to this tweet
                    if self.memory.has_replied_to_tweet(tweet_id):
                        self.logger.info(
                            f"Already replied to tweet {tweet_id} from {handle}"
                        )
                        continue

                    # Get tweet text
                    tweet_text = await self.get_tweet_text(mention)
                    if not tweet_text:
                        continue

                    self.logger.info(
                        f"Processing mention from {handle}: {tweet_text[:50]}..."
                    )

                    # Generate and send reply
                    try:
                        # Check if interaction is a generation request
                        is_request = await self.create_agent.is_generation_request(
                            tweet_text
                        )

                        if is_request:
                            # Check if prompt is safe
                            is_safe = await self.create_agent.is_safe_prompt(tweet_text)

                            if is_safe:
                                # Generate content
                                prompt = await self.create_agent.enhance_prompt(
                                    tweet_text
                                )
                                generation_result = await self.create_api.generate(
                                    prompt=prompt, username=handle.replace("@", "")
                                )

                                if generation_result.get("success"):
                                    # Generate response messages
                                    confirmation, _ = (
                                        await self.create_agent.generate_responses(
                                            generation_result
                                        )
                                    )
                                    if confirmation:
                                        self.logger.info(
                                            f"Generated reply: {confirmation[:50]}..."
                                        )
                                        full_reply = f"{confirmation}\n\n{generation_result.get('share_url')}"
                                        if await self.reply_to_tweet(
                                            mention=mention,
                                            reply=full_reply,
                                            img=generation_result.get("link"),
                                        ):
                                            self.logger.info("Successfully sent reply")
                                            self.memory.add_tweet_reply(tweet_id)
                                            # Store in memory
                                            self.memory.add_mention(
                                                handle,
                                                {
                                                    "tweet_id": tweet_id,
                                                    "text": tweet_text,
                                                    "reply": full_reply,
                                                    "timestamp": time.time(),
                                                    "is_from_us": False,
                                                },
                                            )
                                        else:
                                            self.logger.error("Failed to send reply")
                                    else:
                                        self.logger.error(
                                            "Failed to generate response messages"
                                        )
                            elif (
                                generation_result.get("error")
                                == "X account not found or not linked"
                            ):
                                # Get engagement response for unlinked account
                                engagement_response = await self.create_agent.generate_engagement_response(
                                    tweet_text
                                )
                                if engagement_response:
                                    if await self.reply_to_tweet(
                                        mention, engagement_response
                                    ):
                                        self.logger.info(
                                            "Successfully sent engagement reply"
                                        )
                                        self.memory.add_tweet_reply(tweet_id)
                                        # Store in memory
                                        self.memory.add_mention(
                                            handle,
                                            {
                                                "tweet_id": tweet_id,
                                                "text": tweet_text,
                                                "reply": engagement_response,
                                                "timestamp": time.time(),
                                                "is_from_us": False,
                                            },
                                        )
                            else:
                                self.logger.error("Failed to generate content")

                    except Exception as e:
                        self.logger.error(
                            f"Error generating/sending response: {str(e)}"
                        )

                except Exception as e:
                    self.logger.error(f"Error processing mention: {str(e)}")
                    continue

            return True

        except Exception as e:
            self.logger.error(f"Error processing mentions: {str(e)}")
            return False

    async def get_tweet_id(self, mention):
        """Extract tweet ID from mention element"""
        try:
            links = mention.find_elements(By.CSS_SELECTOR, "a[href*='status']")
            for link in links:
                href = link.get_attribute("href")
                if href and "status" in href:
                    return href.split("status/")[1].split("?")[0]
            return None
        except Exception as e:
            self.logger.error(f"Error getting tweet ID: {e}")
            return None

    async def get_tweet_text(self, mention):
        """Extract tweet text from mention element"""
        try:
            text_element = await self.find_element_in_element(
                mention, "[data-testid='tweetText']"
            )
            if text_element:
                return text_element.text
            return None
        except Exception as e:
            self.logger.error(f"Error getting tweet text: {e}")
            return None

    async def navigate_to_mentions(self):
        """Navigate to the mentions page"""
        try:
            self.handler.browser.navigate("https://twitter.com/notifications/mentions")
            await asyncio.sleep(3)
            return True
        except Exception as e:
            self.logger.error(f"Error navigating to mentions: {e}")
            return False

    async def get_mentions(self):
        """Get all mentions"""
        try:
            tweet_selectors = [
                "[data-testid='tweet']",
                "article[role='article']",
                "[data-testid='cellInnerDiv']",
            ]

            mentions = []
            for selector in tweet_selectors:
                try:
                    self.logger.info(f"Trying selector: {selector}")
                    tweets = WebDriverWait(self.handler.browser.driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                    )
                    if tweets:
                        mentions = tweets
                        self.logger.info(
                            f"Found {len(tweets)} mentions using selector: {selector}"
                        )
                        break
                except Exception as e:
                    self.logger.error(f"Error with selector {selector}: {e}")
                    continue

            return mentions
        except Exception as e:
            self.logger.error(f"Error getting mentions: {e}")
            return []

    async def reply_to_tweet(self, mention, reply, img=None):
        """Reply to a tweet by typing out characters"""
        try:
            # Find reply button
            reply_button = None
            reply_selectors = [
                "[data-testid='reply']",
                "[aria-label*='Reply']",
                "[role='button'][aria-label*='Reply']",
            ]

            for selector in reply_selectors:
                buttons = mention.find_elements(By.CSS_SELECTOR, selector)
                for button in buttons:
                    if button.is_displayed() and button.is_enabled():
                        reply_button = button
                        break
                if reply_button:
                    break

            if not reply_button:
                self.logger.error("Could not find reply button")
                return False

            # Click reply button
            try:
                # Scroll into view
                self.handler.browser.driver.execute_script(
                    "arguments[0].scrollIntoView(true);", reply_button
                )
                await asyncio.sleep(1)

                # Click with JavaScript
                self.handler.browser.driver.execute_script(
                    "arguments[0].click();", reply_button
                )
                await asyncio.sleep(1)

                # Find tweet input box
                input_box = WebDriverWait(self.handler.browser.driver, 5).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "div[data-testid='tweetTextarea_0'][role='textbox']",
                        )
                    )
                )

                # Click the input box
                actions = ActionChains(self.handler.browser.driver)
                actions.move_to_element(input_box)
                actions.click()
                actions.perform()
                await asyncio.sleep(1)

                # Type out the reply character by character
                for char in reply:
                    actions = ActionChains(self.handler.browser.driver)
                    actions.send_keys(char)
                    actions.perform()
                    await asyncio.sleep(random.uniform(0.03, 0.1))
                await asyncio.sleep(1)  # Wait a moment after typing

                # If we have an image, upload it first
                if img:
                    try:
                        # Download image
                        local_path = await self.download_image(img)
                        if not local_path:
                            self.logger.error("Failed to download image")
                            return False

                        # Find file input
                        file_input = await self.wait_and_find_element(
                            "input[type='file'][data-testid='fileInput']", timeout=10
                        )

                        if not file_input:
                            self.logger.error("Could not find file input")
                            return False

                        # Upload image
                        absolute_path = os.path.abspath(local_path)
                        self.logger.info(f"Uploading image from {absolute_path}")
                        file_input.send_keys(absolute_path)

                        # Wait for upload and verify preview
                        try:
                            await self.wait_and_find_element(
                                "[data-testid='attachments']", timeout=10
                            )
                            self.logger.info("Image preview confirmed")
                        except Exception as e:
                            self.logger.error(
                                f"Image preview not found after upload: {e}"
                            )
                            return False

                    except Exception as e:
                        self.logger.error(f"Error uploading image: {e}")
                        return False
                await asyncio.sleep(1)

                # Find post button using WebDriverWait
                post_button = None
                post_selectors = [
                    "button[data-testid='tweetButton']",  # Changed to button instead of div
                    "button[role='button'][data-testid='tweetButton']",
                    "div[data-testid='tweetButton']",
                    "div[role='button'][data-testid='tweetButton']",
                ]

                for selector in post_selectors:
                    try:
                        post_button = WebDriverWait(
                            self.handler.browser.driver, 5
                        ).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                        if post_button:
                            self.logger.info(
                                f"Found post button with selector: {selector}"
                            )
                            break
                    except:
                        continue

                if not post_button:
                    self.logger.error("Could not find post button")
                    return False

                # Click post button
                self.handler.browser.driver.execute_script(
                    "arguments[0].click();", post_button
                )
                await asyncio.sleep(2)

                # Verify reply was sent by checking if textarea is gone
                try:
                    WebDriverWait(self.handler.browser.driver, 3).until_not(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0']")
                        )
                    )
                    self.logger.info("Reply sent successfully")
                    return True
                except:
                    self.logger.error(
                        "Reply may not have been sent - textarea still present"
                    )
                    return False

            except Exception as e:
                self.logger.error(f"Error sending reply: {e}")
                return False

        except Exception as e:
            self.logger.error(f"Error in reply_to_tweet: {e}")
            return False

    async def get_handle_from_mention(self, mention_element):
        """Extract handle from mention element"""
        try:
            handle_element = await self.find_element_in_element(
                mention_element, "[data-testid='User-Name']"
            )
            if handle_element:
                handle_text = handle_element.text
                # Extract handle from text (usually in format "Name @handle")
                if "@" in handle_text:
                    return "@" + handle_text.split("@")[1].split()[0]
            return None
        except Exception as e:
            self.logger.error(f"Error getting handle: {e}")
            return None

    async def find_element_in_element(self, parent_element, selector, timeout=5):
        """Find an element within another element using a CSS selector"""
        try:
            # First check if element exists directly
            elements = parent_element.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                return elements[0]

            # If not found immediately, wait and try again
            start_time = time.time()
            while time.time() - start_time < timeout:
                elements = parent_element.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    return elements[0]
                await asyncio.sleep(0.5)

            return None

        except Exception as e:
            self.logger.error(f"Error finding element with selector {selector}: {e}")
            return None

    async def wait_and_find_elements(self, selector, timeout=5):
        """Wait for and find all elements matching a CSS selector"""
        try:
            elements = WebDriverWait(self.handler.browser.driver, timeout).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
            )
            return elements
        except Exception as e:
            self.logger.error(f"Error finding elements with selector {selector}: {e}")
            return []

    async def wait_and_find_element(self, selector, timeout=5):
        """Wait for and find an element matching a CSS selector"""
        try:
            element = WebDriverWait(self.handler.browser.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return element
        except Exception as e:
            self.logger.error(f"Error finding element with selector {selector}: {e}")
            return None

    async def load_replied_mentions(self):
        """Load previously replied mentions"""
        try:
            with open("data/replied_mentions.json", "r") as f:
                return set(json.load(f))
        except:
            return set()

    async def save_replied_mentions(self, mentions):
        """Save replied mentions"""
        with open("data/replied_mentions.json", "w") as f:
            json.dump(list(mentions), f)

    async def download_image(self, image_url: str) -> str:
        """Download image from URL and return local path."""
        try:
            # Create temp directory if it doesn't exist
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)

            # Generate temporary file path
            temp_path = temp_dir / f"temp_{int(time.time())}.jpg"

            # Download image
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()

            # Save image
            with open(temp_path, "wb") as f:
                f.write(response.content)

            self.logger.info(f"Image downloaded to {temp_path}")
            return str(temp_path)

        except Exception as e:
            self.logger.error(f"Error downloading image: {e}")
            return None
