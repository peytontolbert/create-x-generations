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
from services.utils import download_media

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_audio_upload():
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

        # Test audio URL
        test_audio = {
            "url": "https://storage.googleapis.com/createnow/media/ea77d656-f942-4919-bd07-1b117ba5ce04.mp3",
            "description": "Audio to video conversion test"
        }
        
        test_message = "Testing audio upload functionality! 🎵"
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

        try:
            
            logger.info(f"Testing: {test_audio['description']}")
            logger.info(f"Attempting to send audio as video: {test_audio['url']}")
            
            # Send message with converted video
            success = await message_controller.send_message(
                f"{test_message} - {test_audio['description']}", 
                media_url=test_audio['url']
            )

            if success:
                logger.info(f"Test audio-video sent successfully: {test_audio['description']}")
            else:
                logger.error(f"Failed to send test audio-video: {test_audio['description']}")

            # Wait after sending
            await asyncio.sleep(10)  # Longer wait for video processing

        except Exception as e:
            logger.error(f"Error testing audio upload {test_audio['description']}: {e}")

    except Exception as e:
        logger.error(f"Error in test: {e}")
        raise

    finally:
        # Wait a bit before cleanup to ensure file upload is complete
        await asyncio.sleep(5)
        
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
        asyncio.run(test_audio_upload())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with error: {e}") 