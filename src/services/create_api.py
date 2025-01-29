import os
import logging
import aiohttp
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class CreateAPI:
    def __init__(self):
        """Initialize the Create API service."""
        load_dotenv()
        self.api_key = os.getenv("GENERATION_API_KEY")
        self.api_url = "http://localhost:3000/api/generate-external-api"


        if not self.api_key:
            logger.error("X_API_KEY not found in environment variables")
            raise ValueError("X_API_KEY not found in environment variables")

    async def generate(self, prompt: str, username: str) -> dict:
        """
        Generate content using the Create API.

        Args:
            prompt (str): The generation prompt
            username (str): The X/Twitter username

        Returns:
            dict: The API response containing generation details
        """
        try:
            # Prepare request data
            request_data = {"prompt": prompt, "x_username": username}
            print(request_data)
            logger.info(f"\nSending generation request:")
            logger.info(f"Prompt: {prompt}")
            logger.info(f"Username: {username}")
            logger.info(f"API URL: {self.api_url}")
            logger.info(f"Headers: X-API-Key: {'*' * len(self.api_key)}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=request_data,
                    headers={
                        "X-API-Key": self.api_key,
                        "Content-Type": "application/json",
                    },
                ) as response:
                    logger.info(f"Response Status: {response.status}")
                    logger.info(f"Response Headers: {response.headers}")

                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Response Data: {data}")
                        logger.info("Generation successful!")
                        return {
                            "success": True,
                            "link": data.get("link"),
                            "share_url": data.get("share_url"),
                            "id": data.get("id"),
                            "media_type": data.get("media_type"),
                            "prompt": data.get("prompt"),
                        }
                    else:
                        error_text = await response.text()
                        logger.info(f"Full Error Response: {error_text}")
                        logger.error(f"API request failed: {error_text}")
                        return {"success": False, "error": error_text}

        except aiohttp.ClientError as e:
            logger.error(f"Connection error: {e}")
            return {"success": False, "error": f"Connection error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def format_reply(self, generation_result: dict) -> str:
        """
        Format a reply message with generation results.

        Args:
            generation_result (dict): The result from generate()

        Returns:
            str: Formatted reply message
        """
        if not generation_result.get("success"):
            return "Sorry, I encountered an error while generating your request. Please try again later."

        reply = "I've created your design! 🎨\n\n"

        if generation_result.get("link"):
            reply += f"📱 Download: {generation_result['link']}\n"

        if generation_result.get("share_url"):
            reply += f"🌐 View online: {generation_result['share_url']}"

        return reply
