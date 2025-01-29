import asyncio
import logging
from dotenv import load_dotenv
from src.services.conversation_memory import ConversationMemory
from src.services.create_agent import CreateAgent
from src.services.create_api import CreateAPI
from src.services.action_handler import ActionHandler
from src.controllers.message_controller import MessageController
from src.controllers.mention_controller import MentionController
from src.controllers.post_controller import PostController
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


class MainController:
    def __init__(self):
        # Load environment variables
        load_dotenv()

        # Initialize shared memory
        self.memory = ConversationMemory()

        # Initialize services
        self.create_agent = CreateAgent()
        self.create_api = CreateAPI()

        # Initialize action handler
        self.action_handler = ActionHandler()

        # Initialize controllers with simplified parameters
        self.message_controller = MessageController(
            self.action_handler,
            memory=self.memory,
            create_agent=self.create_agent,
            create_api=self.create_api,
        )
        self.mention_controller = MentionController(
            self.action_handler,
            memory=self.memory,
            create_agent=self.create_agent,
            create_api=self.create_api,
        )
        self.post_controller = PostController(
            self.action_handler,
            memory=self.memory,
            create_agent=self.create_agent,
            create_api=self.create_api,
        )

        # Control flags
        self.running = False

    async def run(self):
        """Main run loop."""
        self.running = True
        try:

            if not await self.action_handler.ensure_logged_in():
                logger.error("Failed to log in")
                return

            while self.running:
                try:
                    logger.info("\nStarting new processing cycle")
                    logger.info("=" * 50)
                    await self.post_controller.post_creation()
                    # Process message requests
                    logger.info("\nChecking message requests...")
                    await self.message_controller.process_message_requests()
                    await asyncio.sleep(2)

                    # Process DMs
                    logger.info("\nProcessing DMs...")
                    await self.message_controller.process_dms()
                    await asyncio.sleep(2)

                    # Process mentions
                    logger.info("\nProcessing mentions...")
                    await self.mention_controller.process_mentions()
                    # Save memory state
                    self.memory.save_all_conversations()

                    logger.info("\nCompleted processing cycle")
                    logger.info("=" * 50)

                    # Sleep between cycles
                    await asyncio.sleep(8)

                except Exception as e:
                    logger.error(f"Error in processing cycle: {e}")
                    await asyncio.sleep(30)
                    continue

        except KeyboardInterrupt:
            logger.info("Shutting down gracefully...")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        try:
            self.running = False
            if hasattr(self, "action_handler"):
                self.action_handler.cleanup()
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
