import asyncio
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.services.action_handler import ActionHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def scan_usernames():
    """Scan messages for usernames using different methods"""
    handler = ActionHandler()

    try:
        # Login
        if not await handler.ensure_logged_in():
            logger.error("Failed to login")
            return

        # Navigate to messages
        logger.info("\nNavigating to messages...")
        handler.browser.navigate("https://twitter.com/messages")
        await asyncio.sleep(3)

        # Get conversation elements
        logger.info("\nLooking for conversation elements...")
        conversations = WebDriverWait(handler.browser.driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "[data-testid='cellInnerDiv']")
            )
        )

        logger.info(f"Found {len(conversations)} conversation elements")

        # Try different methods to find usernames
        for i, conv in enumerate(conversations[:10], 1):
            logger.info(f"\n--- Conversation {i} ---")

            # Method 1: Direct username span
            try:
                username_spans = conv.find_elements(
                    By.CSS_SELECTOR,
                    "span.css-1jxf684.r-bcqeeo.r-1ttztb7.r-qvutc0.r-poiln3",
                )
                for span in username_spans:
                    text = span.text.strip()
                    html = span.get_attribute("outerHTML")
                    logger.info(f"Username span text: {text}")
                    logger.info(f"HTML: {html}")
            except Exception as e:
                logger.error(f"Error with username spans: {e}")

            # Method 2: Parent elements
            try:
                parent_divs = conv.find_elements(By.CSS_SELECTOR, "div[dir='ltr']")
                for div in parent_divs:
                    text = div.text.strip()
                    if text.startswith("@"):
                        logger.info(f"Parent div text: {text}")
                        html = div.get_attribute("outerHTML")
                        logger.info(f"HTML: {html}")
            except Exception as e:
                logger.error(f"Error with parent divs: {e}")

            # Method 3: All spans with potential usernames
            try:
                spans = conv.find_elements(By.CSS_SELECTOR, "span")
                for span in spans:
                    text = span.text.strip()
                    if text.startswith("@"):
                        classes = span.get_attribute("class")
                        html = span.get_attribute("outerHTML")
                        logger.info(f"General span text: {text}")
                        logger.info(f"Classes: {classes}")
                        logger.info(f"HTML: {html}")
            except Exception as e:
                logger.error(f"Error with general spans: {e}")

    except Exception as e:
        logger.error(f"Error in scan script: {e}")
    finally:
        # Cleanup
        handler.cleanup()


if __name__ == "__main__":
    asyncio.run(scan_usernames())
