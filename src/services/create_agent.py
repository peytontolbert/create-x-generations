import os
import logging
import json
from typing import Dict, Tuple
from swarms import Agent
from swarm_models import OpenAIChat, GPT4VisionAPI
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class CreateAgent:
    def __init__(self):
        """Initialize the Create agents for various tasks."""
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        # Initialize all agents
        self.setup_agents()

    def setup_agents(self):
        """Initialize all specialized agents."""
        # Request classifier agent
        self.classifier_agent = Agent(
            agent_name="request-classifier",
            system_prompt="""You are an AI agent specialized in classifying user messages.
            Determine if a message is requesting AI image generation.
            Respond with only 'true' or 'false'.
            Examples of generation requests:
            - "Can you create an image of..."
            - "Generate a picture of..."
            - "Make me an illustration of..."
            - "Design a scene with..."
            """,
            llm=OpenAIChat(
                openai_api_key=self.api_key,
                model_name="gpt-4o",
                temperature=0.3,
            ),
            max_loops=1,
        )

        # Prompt enhancer agent
        self.prompt_agent = Agent(
            agent_name="prompt-enhancer",
            system_prompt="""You are an AI agent specialized in enhancing content generation prompts.
            Clean the prompt by removing unnecessary words or symbols from the user's actual prompt.
            Format: Return only the clean prompt, no explanations.""",
            llm=OpenAIChat(
                openai_api_key=self.api_key,
                model_name="gpt-4o",
                temperature=0.7,
            ),
            max_loops=1,
        )

        # Response generator agent
        self.response_agent = Agent(
            agent_name="response-generator",
            system_prompt="""You are a friendly AI assistant who crafts engaging responses for users.
            Create two messages:
            1. A nice message about their generation (the image will be added to the message)
            2. A follow-up message encouraging them to share their creation (a link will be added after the message)
            
            Format your response as JSON:
            {
                "confirmation": "a nice message about their generation",
                "share_prompt": "check out and share your creation!"
            }
            
            Keep messages casual and enthusiastic. Use emojis appropriately.""",
            llm=OpenAIChat(
                openai_api_key=self.api_key,
                model_name="gpt-4o",
                temperature=0.7,
            ),
            max_loops=1,
        )

        # NSFW detector agent
        self.nsfw_agent = Agent(
            agent_name="nsfw-detector",
            system_prompt="""You are an AI agent specialized in detecting NSFW content in prompts.
            Analyze the given prompt and respond with only 'SAFE' or 'UNSAFE'.
            Be conservative - if in doubt, mark as UNSAFE.
            Consider both explicit content and subtle implications.""",
            llm=OpenAIChat(
                openai_api_key=self.api_key,
                model_name="gpt-4o",
                temperature=0.3,
            ),
            max_loops=1,
        )

        self.trending_nsfw_agent = Agent(
            agent_name="nsfw-detector",
            system_prompt="You are an AI agent specialized in detecting NSFW content in images. Analyze the given image and respond with 'SAFE' or 'UNSAFE'.",
            llm=GPT4VisionAPI(
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                model_name="gpt-4o",
                temperature=0.3,
            ),
            max_loops=1,
        )
        self.tweet_agent = Agent(
            agent_name="tweet-generator",
            system_prompt="""You are a social media expert who creates engaging tweets about digital creations. 
            Include relevant hashtags and create excitement about the artwork. Keep tweets under 100 characters. 
            Always include the creator's handle if available. The tweet will be posted with an image attached.""",
            llm=GPT4VisionAPI(
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                model_name="gpt-4o",
                temperature=0.7,
            ),
            max_loops=1,
        )

        # Add new engagement agent
        self.engagement_agent = Agent(
            agent_name="engagement-agent",
            system_prompt="""You are an enthusiastic and helpful AI assistant focused on engaging users with our AI design generation platform.

Your role is to craft personalized, engaging responses that:
1. Acknowledge their message
2. Explain that you're an AI assistant specializing in generating unique designs
3. Encourage them to try the platform with a specific example based on their interests/message
4. Guide them on how to start (connect X account + example generation prompt)

Keep responses:
- Friendly and enthusiastic
- Short (2-3 sentences max per point)
- Include relevant emojis
- End with a clear call-to-action

Example structure:
"[Acknowledge their message]! 👋

I'm an AI assistant that helps create amazing AI generated content! ✨

[Personalized example based on their interests] - I could help you generate something like that!

To get started:
1️⃣ Connect your X account on our platform
2️⃣ Try a prompt like '[contextual example prompt]'

Can't wait to see what we create together! 🎨"

Format: Return only the response message, no explanations.""",
            llm=OpenAIChat(
                openai_api_key=self.api_key,
                model_name="gpt-4o",
                temperature=0.7,
            ),
            max_loops=1,
        )

    async def is_generation_request(self, message: str) -> bool:
        """Determine if a message is requesting generation."""
        try:
            print(message)
            response = await self.classifier_agent.run_concurrent(message)
            print(response)
            return response.lower() == "true"
        except Exception as e:
            logger.error(f"Error classifying message: {e}")
            return False

    async def enhance_prompt(self, prompt: str) -> str:
        """Enhance the generation prompt."""
        try:
            enhanced = await self.prompt_agent.run_concurrent(prompt)
            return enhanced.strip()
        except Exception as e:
            logger.error(f"Error enhancing prompt: {e}")
            return prompt

    async def is_safe_prompt(self, prompt: str) -> bool:
        """Check if the prompt is safe for generation."""
        try:
            response = await self.nsfw_agent.run_concurrent(prompt)

            # Normalize and validate response
            response = str(response).strip().upper()
            if response not in ["SAFE", "UNSAFE"]:
                logger.error(f"Invalid safety check response: {response}")
                return False
            if response == "SAFE":
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Error checking prompt safety: {e}")
            return False

    async def generate_responses(self, generation_result: Dict) -> Tuple[str, str]:
        """Generate confirmation and share prompt messages."""
        try:
            # Add validation for generation result
            if not generation_result:
                logger.error("Empty generation result")
                return None, None

            if not generation_result.get("success"):
                logger.error(
                    f"Generation failed: {generation_result.get('error', 'Unknown error')}"
                )
                return None, None

            # Prepare context for response generation
            context = {"prompt": generation_result.get("prompt", "")}

            response = await self.response_agent.run_concurrent(str(context))

            try:
                # Method 1: Try direct eval of response
                messages = eval(response)
                if (
                    isinstance(messages, dict)
                    and "confirmation" in messages
                    and "share_prompt" in messages
                ):
                    return messages["confirmation"], messages["share_prompt"]

            except Exception as e:
                logger.warning(f"Failed to parse response with eval: {e}")

                try:
                    # Method 2: Look for ```json block
                    if "```json" in response:
                        json_text = response.split("```json")[1].split("```")[0].strip()
                        messages = json.loads(json_text)
                        if (
                            isinstance(messages, dict)
                            and "confirmation" in messages
                            and "share_prompt" in messages
                        ):
                            return messages["confirmation"], messages["share_prompt"]

                except Exception as e:
                    logger.warning(f"Failed to parse JSON block: {e}")

                    try:
                        # Method 3: Direct JSON parse of whole response
                        messages = json.loads(response)
                        if (
                            isinstance(messages, dict)
                            and "confirmation" in messages
                            and "share_prompt" in messages
                        ):
                            return messages["confirmation"], messages["share_prompt"]

                    except Exception as e:
                        logger.warning(f"Failed to parse response as JSON: {e}")

                        # Method 4: Look for quoted strings with confirmation/share_prompt
                        try:
                            import re

                            confirmation_match = re.search(
                                r'"confirmation":\s*"([^"]+)"', response
                            )
                            share_match = re.search(
                                r'"share_prompt":\s*"([^"]+)"', response
                            )

                            if confirmation_match and share_match:
                                return confirmation_match.group(1), share_match.group(1)

                        except Exception as e:
                            logger.warning(f"Failed to extract with regex: {e}")

            # Fallback messages if all parsing methods fail
            logger.warning("Using fallback messages")
            confirmation = (
                f"I've created your design! 🎨\n\n" f"Prompt: {context['prompt']}"
            )
            share_prompt = (
                f"Use this link to share your creation: {context['share_url']} 🌟"
            )
            return confirmation, share_prompt

        except Exception as e:
            logger.error(f"Error generating responses: {e}")
            return None, None

    async def generate_engagement_response(self, message: str) -> str:
        """Generate an engaging response for non-generation messages."""
        try:
            response = await self.engagement_agent.run_concurrent(message)
            return response.strip()
        except Exception as e:
            logger.error(f"Error generating engagement response: {e}")
            # Return a fallback message if something goes wrong
            return (
                "Hi there! 👋 I'm an AI assistant that helps create amazing designs!\n\n"
                "To get started:\n"
                "1️⃣ Connect your X account on our platform\n"
                "2️⃣ Try a prompt like 'Generate a sunset over mountains'\n\n"
                "Can't wait to see what we create together! ✨"
            )

    async def generate_tweet(self, creation_data):
        """Generate a tweet using the Swarms agent"""
        prompt = f"""
        Generate an engaging tweet for this creation:
        Prompt: {creation_data.get('prompt')}
        Creator: {creation_data.get('display_name')}
        
        The image will be automatically attached to the tweet, so you don't need to include the URL in the tweet text.
        Focus on creating engaging text that complements the visual content.
        """

        return self.tweet_agent.run(task=prompt, img=creation_data.get("link"))

    async def is_trending_nsfw(self, image_url: str) -> bool:

        result = self.trending_nsfw_agent.run(
            task=f"Analyze this image for NSFW content. Reply TRUE or FALSE:",
            img=image_url,
        )
        print(result)
        return result.lower() == "true"
