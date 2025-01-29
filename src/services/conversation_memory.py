import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)


class ConversationMemory:
    def __init__(self):
        self.data_dir = Path("data/conversations")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.memory = {}
        self.tweets = []  # Add tweet storage
        self.tweet_history_file = Path(
            "data/tweet_history.json"
        )  # Use existing tweet history file
        self.replied_mentions = self.load_replied_mentions()
        self.load_all_conversations()
        self.load_tweets()  # Load tweet history

    def load_all_conversations(self):
        """Load all conversation files from disk"""
        try:
            for file in self.data_dir.glob("*.json"):
                handle = file.stem  # filename without extension
                with open(file, "r", encoding="utf-8") as f:
                    self.memory[handle] = json.load(f)
                    logger.info(f"Loaded memory for {handle}")
        except Exception as e:
            logger.error(f"Error loading conversations: {e}")

    def save_conversation(self, handle: str):
        """Save a specific conversation to disk"""
        try:
            if handle in self.memory:
                file_path = self.data_dir / f"{handle}.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(self.memory[handle], f, indent=2)
                logger.info(f"Saved memory for {handle}")
        except Exception as e:
            logger.error(f"Error saving conversation for {handle}: {e}")

    def save_all_conversations(self):
        """Save all conversations to disk"""
        for handle in self.memory:
            self.save_conversation(handle)

    def get_conversation(self, handle: str):
        """Get or create conversation memory for a handle"""
        if handle not in self.memory:
            self.memory[handle] = {
                "dms": [],
                "mentions": [],
                "last_interaction": None,
                "metadata": {
                    "first_seen": datetime.now().isoformat(),
                    "total_interactions": 0,
                },
            }
        return self.memory[handle]

    def add_dm(self, handle: str, message: dict):
        """Add a DM to memory"""
        conv = self.get_conversation(handle)
        message["type"] = "dm"
        conv["dms"].append(message)
        conv["last_interaction"] = datetime.now().isoformat()
        conv["metadata"]["total_interactions"] += 1
        self.save_conversation(handle)

    def add_mention(self, handle: str, mention_data: dict):
        """Add a mention to the conversation memory"""
        try:
            # Get or create conversation for this handle
            conversation = self.get_conversation(handle)
            if not conversation:
                conversation = {
                    "handle": handle,
                    "dms": [],
                    "mentions": [],
                    "last_interaction": None,
                    "total_interactions": 0,
                }

            # Add mention to mentions list
            mentions = conversation.get("mentions", [])
            mentions.append(mention_data)
            conversation["mentions"] = mentions

            # Update interaction metadata
            conversation["last_interaction"] = datetime.now().isoformat()
            conversation["total_interactions"] += 1

            # Save conversation data
            self.save_conversation(handle)

        except Exception as e:
            logger.error(f"Error adding mention: {e}")

    def get_recent_context(self, handle: str, limit: int = 5) -> List[Dict]:
        """Get recent context for a handle."""
        if handle == "tweets":
            return [tweet["text"] for tweet in self.tweets[-limit:]]

        # Original conversation context logic
        try:
            messages = self.memory.get(handle, [])
            if not messages:
                return []

            # Sort by timestamp, handling None values
            def get_timestamp(msg):
                ts = msg.get("timestamp")
                if ts is None:
                    return ""
                return str(ts)

            messages.sort(key=get_timestamp)
            return messages[-limit:]

        except Exception as e:
            logger.error(f"Error getting context for {handle}: {e}")
            return []

    def get_dm_history(self, handle: str, limit: int = None):
        """Get DM history for a handle"""
        conv = self.get_conversation(handle)
        messages = conv["dms"]
        return messages[-limit:] if limit else messages

    def get_mention_history(self, handle: str, limit: int = None):
        """Get mention history for a handle"""
        conv = self.get_conversation(handle)
        mentions = conv["mentions"]
        return mentions[-limit:] if limit else mentions

    def get_all_handles(self):
        """Get list of all handles in memory"""
        return list(self.memory.keys())

    def get_metadata(self, handle: str):
        """Get metadata for a handle"""
        conv = self.get_conversation(handle)
        return conv["metadata"]

    def update_metadata(self, handle: str, key: str, value):
        """Update metadata for a handle"""
        conv = self.get_conversation(handle)
        conv["metadata"][key] = value
        self.save_conversation(handle)

    def get_dms(self, handle: str, limit: Optional[int] = None) -> List[Dict]:
        """Get DMs for a handle, optionally limited to the most recent n messages"""
        if handle not in self.memory:
            return []
        dms = self.memory[handle]["dms"]
        if limit:
            return dms[-limit:]
        return dms

    def get_mentions(self, handle: str, limit: Optional[int] = None) -> List[Dict]:
        """Get mentions for a handle, optionally limited to the most recent n messages"""
        if handle not in self.memory:
            return []
        mentions = self.memory[handle]["mentions"]
        if limit:
            return mentions[-limit:]
        return mentions

    def get_all_conversations(self, handle: str) -> Dict[str, List[Dict]]:
        """Get all conversations (DMs and mentions) for a handle"""
        if handle not in self.memory:
            return {"dms": [], "mentions": []}
        return self.memory[handle]

    def clear_memory(self, handle: str = None):
        """Clear memory for a specific handle or all handles"""
        if handle:
            if handle in self.memory:
                self.memory[handle] = {"dms": [], "mentions": []}
                self.save_conversation(handle)
        else:
            self.memory = {}
            # Remove all json files
            for file in self.data_dir.glob("*.json"):
                file.unlink()

    def has_replied_to_mention(self, handle: str, tweet_id: str) -> bool:
        """Check if we've already replied to a specific mention"""
        try:
            # Get conversation data for this handle
            conversation = self.get_conversation(handle)
            if not conversation:
                return False

            # Check mentions for this tweet ID
            mentions = conversation.get("mentions", [])
            for mention in mentions:
                if mention.get("tweet_id") == tweet_id and mention.get(
                    "is_reply", False
                ):
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking replied mentions: {e}")
            return False

    def has_replied_to_tweet(self, tweet_id):
        """Check if we've already replied to a tweet"""
        return tweet_id in self.replied_mentions

    def add_tweet_reply(self, tweet_id):
        """Mark a tweet as replied to"""
        self.replied_mentions.add(tweet_id)
        self.save_replied_mentions()

    def load_replied_mentions(self):
        """Load previously replied mentions"""
        try:
            with open("data/replied_mentions.json", "r") as f:
                return set(json.load(f))
        except:
            return set()

    def save_replied_mentions(self):
        """Save replied mentions"""
        with open("data/replied_mentions.json", "w") as f:
            json.dump(list(self.replied_mentions), f)

    def load_tweets(self):
        """Load tweet history from file."""
        try:
            if self.tweet_history_file.exists():
                with open(self.tweet_history_file, "r") as f:
                    data = json.load(f)
                    # Convert the existing format to our memory format
                    self.tweets = [
                        {
                            "text": tweet,
                            "timestamp": data.get("last_tweet_time"),
                            "is_from_us": True,
                        }
                        for tweet in data.get("tweet_history", [])
                    ]
            else:
                self.tweets = []
        except Exception as e:
            logger.error(f"Error loading tweets: {e}")
            self.tweets = []

    def save_tweets(self):
        """Save tweet history to file."""
        try:
            self.tweet_history_file.parent.mkdir(parents=True, exist_ok=True)
            # Convert our memory format back to the existing format
            with open(self.tweet_history_file, "r") as f:
                existing_data = json.load(f)

            existing_data["tweet_history"] = [tweet["text"] for tweet in self.tweets]
            if self.tweets:
                existing_data["last_tweet_time"] = self.tweets[-1]["timestamp"]

            with open(self.tweet_history_file, "w") as f:
                json.dump(existing_data, f)
        except Exception as e:
            logger.error(f"Error saving tweets: {e}")

    def add_message(self, handle: str, message: Dict):
        """Add a message to memory."""
        if handle == "tweets":
            # Handle tweets differently
            self.tweets.append(message)
            if len(self.tweets) > 10:  # Keep last 10 tweets
                self.tweets = self.tweets[-10:]
            self.save_tweets()
        else:
            # Handle regular conversations as before
            conv = self.get_conversation(handle)
            if "type" in message and message["type"] == "dm":
                self.add_dm(handle, message)
            else:
                self.add_mention(handle, message)
