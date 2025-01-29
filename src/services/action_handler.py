import logging
import asyncio
import os
import time
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv
from urllib.parse import urlparse
from src.controllers.browser_controller import BrowserController
from selenium.webdriver.common.action_chains import ActionChains

logger = logging.getLogger(__name__)


class ActionHandler:
    """Main handler for Twitter/X platform interactions.

    This class serves as the central coordinator for all platform interactions,
    delegating specific tasks to specialized controllers.
    """

    def __init__(
        self, headless: bool = False, retry_attempts: int = 3, timeout: int = 10
    ):
        """Initialize the action handler with configurable parameters.

        Args:
            headless: Whether to run browser in headless mode
            retry_attempts: Number of retry attempts for operations
            timeout: Default timeout for web operations in seconds
        """
        # Core configuration
        self.retry_attempts = retry_attempts
        self.timeout = timeout
        self.is_logged_in = False

        # Initialize browser
        self.browser = BrowserController(
            window_width=1200, window_height=800, headless=headless
        )

        # Load environment variables
        load_dotenv()

        # Create data directory if it doesn't exist
        Path("data").mkdir(exist_ok=True)

    async def retry_operation(
        self, operation, *args, custom_retry_count=None, **kwargs
    ):
        """Retry an operation with exponential backoff.

        Args:
            operation: Async function to retry
            custom_retry_count: Optional custom retry count
            *args, **kwargs: Arguments to pass to operation

        Returns:
            Result of the operation or None if all retries failed
        """
        retries = custom_retry_count or self.retry_attempts
        for attempt in range(retries):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                if attempt == retries - 1:
                    logger.error(f"Operation failed after {retries} attempts: {e}")
                    return None
                wait_time = min(2**attempt, 30)  # Exponential backoff capped at 30s
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}"
                )
                await asyncio.sleep(wait_time)

    async def ensure_logged_in(self) -> bool:
        """Ensure user is logged in with retry mechanism."""
        return await self.retry_operation(self._ensure_logged_in_impl)

    async def _ensure_logged_in_impl(self) -> bool:
        """Implementation of login check and process."""
        if self.is_logged_in:
            return True

        # First check if we're already logged in by checking current URL
        current_url = self.browser.driver.current_url
        if "twitter.com/home" in current_url or "x.com/home" in current_url:
            logger.info("Already logged in")
            self.is_logged_in = True
            return True

        # Navigate to home to check login status
        self.browser.navigate("https://twitter.com/home")
        await asyncio.sleep(2)
        
        # Check if we got redirected to login page
        current_url = self.browser.driver.current_url
        if not ("login" in current_url):
            logger.info("Already logged in")
            self.is_logged_in = True
            return True

        # If we're not logged in, proceed with manual login
        logger.info("Starting manual login process")
        self.browser.navigate("https://x.com/login")
        await asyncio.sleep(2)

        # Find and fill username field
        username_selectors = [
            (By.NAME, "text"),
            (By.CSS_SELECTOR, "input[name='text']"),
            (By.XPATH, "//input[@autocomplete='username']"),
        ]

        username_input = None
        for by, selector in username_selectors:
            try:
                username_input = WebDriverWait(self.browser.driver, 5).until(
                    EC.presence_of_element_located((by, selector))
                )
                break
            except TimeoutException:
                continue

        if not username_input:
            logger.error("Could not find username field")
            return False

        username_input.clear()
        username_input.send_keys(os.getenv("X_USERNAME"))
        await asyncio.sleep(1)

        # Click Next button
        next_button_selectors = [
            "//span[text()='Next']",
            "//div[@role='button']//span[contains(text(), 'Next')]",
            "//div[contains(@class, 'css-18t94o4')]//span[contains(text(), 'Next')]",
        ]

        next_button = None
        for selector in next_button_selectors:
            try:
                next_button = WebDriverWait(self.browser.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                break
            except TimeoutException:
                continue

        if not next_button:
            logger.error("Could not find Next button")
            return False

        next_button.click()
        await asyncio.sleep(2)

        # Find and fill password field
        password_selectors = [
            (By.NAME, "password"),
            (By.CSS_SELECTOR, "input[name='password']"),
            (By.XPATH, "//input[@type='password']"),
        ]

        password_input = None
        for by, selector in password_selectors:
            try:
                password_input = WebDriverWait(self.browser.driver, 5).until(
                    EC.presence_of_element_located((by, selector))
                )
                break
            except TimeoutException:
                continue

        if not password_input:
            logger.error("Could not find password field")
            return False

        password_input.clear()
        password_input.send_keys(os.getenv("X_PASSWORD"))
        await asyncio.sleep(1)

        # Click login button
        login_button_selectors = [
            "//span[text()='Log in']",
            "//div[@role='button']//span[contains(text(), 'Log in')]",
            "//div[contains(@class, 'css-18t94o4')]//span[contains(text(), 'Log in')]",
        ]

        login_button = None
        for selector in login_button_selectors:
            try:
                login_button = WebDriverWait(self.browser.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                break
            except TimeoutException:
                continue

        if not login_button:
            logger.error("Could not find Login button")
            return False

        login_button.click()
        await asyncio.sleep(5)

        # Check for login errors
        try:
            error_message = self.browser.driver.find_element(
                By.XPATH, "//span[contains(text(), 'Wrong password')]"
            )
            if error_message:
                logger.error("Login failed: Wrong password")
                return False
        except NoSuchElementException:
            pass

        # Verify successful login
        try:
            WebDriverWait(self.browser.driver, self.timeout).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[data-testid='SideNav_AccountSwitcher_Button']")
                )
            )
            self.is_logged_in = True
            logger.info("Manual login successful")
            return True
        except:
            logger.error("Login verification failed")
            return False

    async def handle_notifications(self):
        """Handle any notifications that appear, like 'Got it!' popups."""
        try:
            notification_selectors = [
                "//span[text()='Got it!']/ancestor::div[@role='button']",
                "//div[@role='button']//span[contains(text(), 'Got it')]",
                "//span[text()='Got it!']",
                "[data-testid='toast']",
            ]

            for selector in notification_selectors:
                try:
                    button = WebDriverWait(self.browser.driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    button.click()
                    await asyncio.sleep(0.5)
                    return True
                except:
                    continue

            return False
        except Exception as e:
            logger.debug(f"No notifications found: {e}")
            return False

    def cleanup(self):
        """Clean up resources."""
        try:
            if self.browser:
                self.browser.cleanup()
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def __del__(self):
        """Cleanup when the object is destroyed."""
        self.cleanup()
