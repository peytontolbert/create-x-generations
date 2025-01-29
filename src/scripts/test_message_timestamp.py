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
from selenium.webdriver.common.action_chains import ActionChains

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def get_message_timestamp(message_element):
    """Extract timestamp from message element"""
    try:
        # Find time element within the message
        time_elements = message_element.find_elements(By.CSS_SELECTOR, "time")
        for time_elem in time_elements:
            datetime_attr = time_elem.get_attribute("datetime")
            display_time = time_elem.text
            
            if datetime_attr:
                message_time = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                return {
                    "datetime": message_time,
                    "display_time": display_time,
                    "raw_datetime": datetime_attr
                }
        return None
    except Exception as e:
        logger.error(f"Error getting message timestamp: {e}")
        return None

async def test_message_timestamps():
    handler = None
    try:
        # Initialize browser
        handler = ActionHandler(headless=False)
        
        # Ensure logged in
        logger.info("Ensuring logged in...")
        if not await handler.ensure_logged_in():
            logger.error("Failed to log in")
            return

        # Navigate to messages
        logger.info("Navigating to messages...")
        handler.browser.navigate("https://twitter.com/messages")
        await asyncio.sleep(3)

        # Get conversations using proven selectors
        conversation_selectors = [
            "[data-testid='conversation']",
            "[data-testid='cellInnerDiv']"
        ]

        conversations = []
        for selector in conversation_selectors:
            try:
                logger.info(f"Trying selector: {selector}")
                convs = WebDriverWait(handler.browser.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
                if convs:
                    conversations = convs[:5]  # Limit to first 5 conversations
                    logger.info(f"Found {len(convs)} conversations using selector: {selector}")
                    break
            except Exception as e:
                logger.error(f"Error with selector {selector}: {e}")
                continue

        if not conversations:
            logger.error("No conversations found")
            return

        # Process each conversation
        for i, conv in enumerate(conversations, 1):
            try:
                # Get handle
                handle = None
                spans = conv.find_elements(By.CSS_SELECTOR, "span.css-1jxf684.r-bcqeeo.r-1ttztb7.r-qvutc0.r-poiln3")
                for span in spans:
                    text = span.text.strip()
                    if text.startswith("@"):
                        handle = text
                        break

                # Get timestamp from conversation preview
                timestamp_data = await get_message_timestamp(conv)
                
                if timestamp_data:
                    logger.info(f"\nConversation {i} with {handle or 'Unknown'}:")
                    logger.info(f"Display time: {timestamp_data['display_time']}")
                    logger.info(f"Raw datetime: {timestamp_data['raw_datetime']}")
                    logger.info(f"Parsed datetime: {timestamp_data['datetime']}")
                    
                    # Calculate time difference
                    now = datetime.now().astimezone()
                    time_diff = now - timestamp_data['datetime']
                    logger.info(f"Time since message: {time_diff}")

                    # Click conversation to see detailed messages
                    actions = ActionChains(handler.browser.driver)
                    actions.move_to_element(conv)
                    actions.click()
                    actions.perform()
                    await asyncio.sleep(2)

                    # Get message cells
                    try:
                        message_cells = WebDriverWait(handler.browser.driver, 5).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-testid='cellInnerDiv']"))
                        )

                        if message_cells:
                            logger.info(f"Found {len(message_cells)} messages in conversation")
                            # Get last few messages
                            for msg in message_cells[-3:]:
                                msg_timestamp = await get_message_timestamp(msg)
                                if msg_timestamp:
                                    logger.info("\nMessage details:")
                                    logger.info(f"Display time: {msg_timestamp['display_time']}")
                                    logger.info(f"Raw datetime: {msg_timestamp['raw_datetime']}")
                                    logger.info(f"Parsed datetime: {msg_timestamp['datetime']}")
                        
                        # Return to conversation list
                        back_button = WebDriverWait(handler.browser.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='DM_Timeline_Back']"))
                        )
                        if back_button:
                            back_button.click()
                            await asyncio.sleep(2)
                    except Exception as e:
                        logger.error(f"Error getting message details: {e}")
                else:
                    logger.error(f"Could not get timestamp for conversation {i}")

            except Exception as e:
                logger.error(f"Error processing conversation {i}: {e}")
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
        asyncio.run(test_message_timestamps())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with error: {e}") 