from datetime import datetime
import requests
import os
import asyncio
from src.controllers.tweet_controller import TweetController
import json


class PostController:
    def __init__(self, handler, memory, create_agent, create_api):
        self.handler = handler
        self.memory = memory
        self.create_agent = create_agent
        self.create_api = create_api

        self.used_urls_file = "data/used_urls.json"
        self.used_urls = self._load_used_urls()

        self.tweet_controller = TweetController(self.handler)

    def _load_used_urls(self):
        """Load previously used posts from file"""
        try:
            if os.path.exists(self.used_urls_file):
                with open(self.used_urls_file, "r") as f:
                    data = json.load(f)
                    # Convert stored posts back into a dictionary with timestamps
                    loaded_urls = {
                        post["url"]: datetime.fromisoformat(post["timestamp"])
                        for post in data["posts"]
                    }
                    # Only keep posts from the last hour
                    current_time = datetime.now()
                    return {
                        url: timestamp
                        for url, timestamp in loaded_urls.items()
                        if (current_time - timestamp).total_seconds() < 3600
                    }
            return {}
        except Exception as e:
            print(f"Error loading used URLs: {e}")
            return {}

    async def _save_used_urls(self):
        """Save used posts with timestamps to file"""
        try:
            os.makedirs(os.path.dirname(self.used_urls_file), exist_ok=True)

            # Convert dictionary to list of posts with timestamps
            posts_list = [
                {"url": url, "timestamp": timestamp.isoformat()}
                for url, timestamp in self.used_urls.items()
            ]
            with open(self.used_urls_file, "w") as f:
                json.dump({"posts": posts_list}, f, indent=2)
        except Exception as e:
            print(f"Error saving used URLs: {e}")

    async def post_creation(self):
        """Main function to run hourly"""
        print(f"Running hourly task at {datetime.now()}")

        # Clean up old posts (older than 1 hour)
        current_time = datetime.now()
        self.used_urls = {
            url: timestamp
            for url, timestamp in self.used_urls.items()
            if (current_time - timestamp).total_seconds() < 3600
        }

        # Try up to 3 times to get a new creation
        for attempt in range(5):
            # Fetch random creation
            creation = await self.fetch_random_creation()
            if not creation:
                print("Failed to fetch creation")
                return

            # Check if we've already posted this creation in the last hour
            image_url = creation.get("link")
            if image_url in self.used_urls:
                last_posted = self.used_urls[image_url]
                minutes_since_post = (current_time - last_posted).total_seconds() / 60
                print(
                    f"Creation posted too recently ({minutes_since_post:.1f} minutes ago), trying another one (attempt {attempt + 1}/3)"
                )
                continue

            # Log the creation data (without sensitive info)
            print(
                f"Fetched creation - Prompt: {creation.get('prompt')}, Link: {creation.get('link')}, Creator: {creation.get('display_name')}"
            )

            # Validate required fields
            required_fields = ["prompt", "display_name", "link"]
            if not all(field in creation for field in required_fields):
                print(
                    f"Creation missing required fields. Received: {list(creation.keys())}"
                )
                continue

            # Check if content is safe
            if not await self.create_agent.is_trending_nsfw(creation["link"]):
                print("Content flagged as NSFW - skipping")
                continue

            # Generate tweet
            tweet_text = await self.create_agent.generate_tweet(creation)
            if not tweet_text:
                print("Failed to generate tweet text")
                continue

            # Post tweet
            success = await self.post_tweet(tweet_text, creation["link"])
            if success:
                # Add URL with current timestamp to used set and save
                self.used_urls[image_url] = current_time
                await self._save_used_urls()
                return

        print("Failed to find a suitable creation after 3 attempts")

    async def fetch_random_creation(self):
        """Fetch a random creation from the API"""
        try:
            headers = {
                "X-API-Key": os.getenv("TRENDING_API_KEY"),
                "Content-Type": "application/json",
            }
            response = requests.get(
                "http://localhost:3000/api/pull-random-liked-creation", headers=headers
            )
            if response.status_code != 200:
                print(f"API request failed with status code: {response.status_code}")
                return None

            data = response.json()
            return data.get("creation", {})  # Return the nested creation object

        except Exception as e:
            print(f"Error fetching creation: {e}")
            return None

    async def post_tweet(self, tweet_text, image_url):
        """Post the tweet using Selenium"""
        try:
            # Navigate to home
            self.handler.browser.navigate("https://twitter.com/home")
            await asyncio.sleep(3)

            # Use the existing tweet posting functionality with image
            tweet_controller = TweetController(self.handler)
            success = await tweet_controller.post_tweet(tweet_text, image_url)


            if success:
                print(f"Successfully posted tweet: {tweet_text}")
                print(f"With image: {image_url}")
                return True
            else:
                print("Failed to post tweet")
                return False

        except Exception as e:
            print(f"Error posting tweet: {e}")
            return False
