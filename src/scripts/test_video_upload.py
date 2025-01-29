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


async def test_video_upload():
    handler = None
    try:
        # Initialize components with GUI visible
        handler = ActionHandler(headless=False)  # This will make the browser visible
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

        # Test video URLs - multiple formats for testing
        test_videos = [
            {
                "url": "https://storage.googleapis.com/createnow/media/41609cd3-84ed-4da5-80f8-82fae2b92438.mp4",
                "description": "MP4 video test"
            }
        ]
        
        test_message = "Testing video upload functionality! 🎥"
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

        # Test each video format
        for test_video in test_videos:
            try:
                logger.info(f"Testing: {test_video['description']}")
                logger.info(f"Attempting to send video: {test_video['url']}")
                
                # Send message with video
                success = await message_controller.send_message(
                    f"{test_message} - {test_video['description']}", 
                    media_url=test_video['url']
                )

                if success:
                    logger.info(f"Test video sent successfully: {test_video['description']}")
                else:
                    logger.error(f"Failed to send test video: {test_video['description']}")

                # Wait between tests
                await asyncio.sleep(10)  # Longer wait for video processing

            except Exception as e:
                logger.error(f"Error testing video {test_video['description']}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error in test: {e}")
        raise

    finally:
        # Clean up
        logger.info("Cleaning up...")
        try:
            # Remove temp directory if it exists
            temp_dir = Path("temp")
            if temp_dir.exists():
                for file in temp_dir.glob("*"):
                    try:
                        file.unlink()
                        logger.info(f"Removed temporary file: {file}")
                    except Exception as e:
                        logger.error(f"Error removing file {file}: {e}")
                temp_dir.rmdir()
                logger.info("Removed temp directory")
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
        asyncio.run(test_video_upload())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with error: {e}") 