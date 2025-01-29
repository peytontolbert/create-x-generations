import asyncio
import logging
import sys
from pathlib import Path
import os

# Add src directory to Python path
src_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(src_dir))

from services.action_handler import ActionHandler
from controllers.message_controller import MessageController
from services.conversation_memory import ConversationMemory
from selenium.webdriver.common.action_chains import ActionChains

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_image_upload():
    handler = None
    try:
        # Initialize components
        handler = ActionHandler(headless=False)  # Set headless=False to see the browser
        memory = ConversationMemory()

        # Create message controller
        message_controller = MessageController(handler, memory, None, None)

        # Ensure logged in
        logger.info("Ensuring logged in...")
        if not await handler.ensure_logged_in():
            logger.error("Failed to log in")
            return

        # Navigate to messages
        logger.info("Navigating to messages...")
        handler.browser.navigate("https://twitter.com/messages")
        await asyncio.sleep(3)

        # Test image URL - replace with a real image URL for testing
        test_image_url = "https://storage.googleapis.com/createnow/media/58f2ba6c-29a5-4d31-ba46-9154ec903757.webp"
        test_message = "Testing image upload functionality! 🖼️"
        test_handle = "@PeytonAGI"

        # Get conversations
        logger.info("Getting conversations...")
        conversations = await message_controller.get_conversations()

        if test_handle not in conversations:
            logger.error(f"Test handle {test_handle} not found in conversations")
            return

        # Click on the conversation
        logger.info(f"Opening conversation with {test_handle}...")
        conv_element = conversations[test_handle]
        actions = ActionChains(handler.browser.driver)
        actions.move_to_element(conv_element)
        actions.click()
        actions.perform()
        await asyncio.sleep(2)

        # Send message with image
        logger.info("Sending test message with image...")
        success = await message_controller.send_message(
            test_message, image_url=test_image_url
        )

        if success:
            logger.info("Test message with image sent successfully!")
        else:
            logger.error("Failed to send test message with image")

        # Wait a bit to see the result
        await asyncio.sleep(5)

    except Exception as e:
        logger.error(f"Error in test: {e}")
        raise  # Re-raise the exception to see the full traceback

    finally:
        # Clean up
        logger.info("Cleaning up...")
        try:
            # Remove temp directory if it exists
            temp_dir = Path("temp")
            if temp_dir.exists():
                for file in temp_dir.glob("*"):
                    file.unlink()
                temp_dir.rmdir()
        except Exception as e:
            logger.error(f"Error cleaning up temp directory: {e}")

        # Clean up browser
        if handler:
            try:
                handler.cleanup()
                logger.info("Browser cleanup completed")
            except Exception as e:
                logger.error(f"Error during browser cleanup: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(test_image_upload())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
