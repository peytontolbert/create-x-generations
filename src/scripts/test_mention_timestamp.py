import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add src directory to Python path
src_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(src_dir))

from services.action_handler import ActionHandler
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def get_tweet_timestamp(mention):
    """Extract timestamp from mention element"""
    try:
        # Find time element within the tweet
        time_elements = mention.find_elements(By.CSS_SELECTOR, "time")
        for time_elem in time_elements:
            datetime_attr = time_elem.get_attribute("datetime")
            display_time = time_elem.text
            
            if datetime_attr:
                tweet_time = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                return {
                    "datetime": tweet_time,
                    "display_time": display_time,
                    "raw_datetime": datetime_attr
                }
        return None
    except Exception as e:
        logger.error(f"Error getting tweet timestamp: {e}")
        return None

async def test_mention_timestamps():
    handler = None
    try:
        # Initialize browser
        handler = ActionHandler(headless=False)
        
        # Ensure logged in
        logger.info("Ensuring logged in...")
        if not await handler.ensure_logged_in():
            logger.error("Failed to log in")
            return

        # Navigate to mentions
        logger.info("Navigating to mentions...")
        handler.browser.navigate("https://twitter.com/notifications/mentions")
        await asyncio.sleep(3)

        # Get mentions using proven selectors from MentionController
        tweet_selectors = [
            "[data-testid='tweet']",
            "article[role='article']",
            "[data-testid='cellInnerDiv']"
        ]

        mentions = []
        for selector in tweet_selectors:
            try:
                logger.info(f"Trying selector: {selector}")
                tweets = WebDriverWait(handler.browser.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
                if tweets:
                    mentions = tweets
                    logger.info(f"Found {len(tweets)} mentions using selector: {selector}")
                    break
            except Exception as e:
                logger.error(f"Error with selector {selector}: {e}")
                continue

        if not mentions:
            logger.error("No mentions found")
            return

        # Process each mention
        for i, mention in enumerate(mentions[:5], 1):  # Process first 5 mentions
            try:
                # Get tweet text for context
                text_element = mention.find_element(By.CSS_SELECTOR, "[data-testid='tweetText']")
                tweet_text = text_element.text if text_element else "No text found"
                
                # Get timestamp
                timestamp_data = await get_tweet_timestamp(mention)
                
                if timestamp_data:
                    logger.info(f"\nMention {i}:")
                    logger.info(f"Text: {tweet_text[:100]}...")
                    logger.info(f"Display time: {timestamp_data['display_time']}")
                    logger.info(f"Raw datetime: {timestamp_data['raw_datetime']}")
                    logger.info(f"Parsed datetime: {timestamp_data['datetime']}")
                    
                    # Calculate time difference
                    now = datetime.now().astimezone()
                    time_diff = now - timestamp_data['datetime']
                    logger.info(f"Time since tweet: {time_diff}")
                else:
                    logger.error(f"Could not get timestamp for mention {i}")

            except Exception as e:
                logger.error(f"Error processing mention {i}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error in test: {e}")
        raise

    finally:
        # Clean up browser
        if handler:
            try:
                handler.cleanup()
                logger.info("Browser cleanup completed")
            except Exception as e:
                logger.error(f"Error during browser cleanup: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_mention_timestamps())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with error: {e}") 