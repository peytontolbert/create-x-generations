from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
from PIL import Image, ImageDraw, ImageFont
import os
import json
import pickle
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class BrowserController:
    def __init__(
        self,
        window_width=1200,
        window_height=800,
        headless=False,
        audio_output_device=None,
    ):
        """Initialize browser controller.

        Args:
            window_width: Browser window width
            window_height: Browser window height
            headless: Whether to run in headless mode
        """
        self.window_width = window_width
        self.window_height = window_height
        self.headless = headless
        self.driver = self._setup_driver()

        # Configure viewport dimensions
        self.viewport_width = self.driver.execute_script("return window.innerWidth")
        self.viewport_height = self.driver.execute_script("return window.innerHeight")

        # Adjust window size
        width_diff = window_width - self.viewport_width
        height_diff = window_height - self.viewport_height
        self.driver.set_window_size(
            window_width + width_diff, window_height + height_diff
        )

        self.screenshot_width = 1008
        self.screenshot_height = 1008

        self.actions = ActionChains(self.driver)
        self.last_mouse_position = None

        logger.info(
            f"Initialized browser with viewport dimensions: {self.viewport_width}x{self.viewport_height}"
        )

    def _setup_driver(self):
        """Set up and configure the Edge webdriver for Docker environment."""
        options = Options()

        # Required for running in Docker
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--remote-debugging-port=9222")

        # Additional options for stability in Docker
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")

        # Configure user data directory
        user_data_dir = os.path.abspath("browser_data")
        options.add_argument(f"user-data-dir={user_data_dir}")

        # Configure logging
        options.add_argument("--enable-logging")
        options.add_argument("--v=1")

        # Audio configurations (if needed)
        options.add_argument("--use-fake-ui-for-media-stream")
        options.add_argument("--use-fake-device-for-media-stream")

        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
        }
        options.add_experimental_option("prefs", prefs)

        try:
            driver = webdriver.Edge(options=options)
            driver.set_window_size(self.window_width, self.window_height)
            return driver
        except Exception as e:
            logger.error(f"Failed to initialize webdriver: {e}")
            raise

    def navigate(self, url: str):
        """Navigate to a URL."""
        self.driver.get(url)
        logger.info(f"Navigated to {url}")
        time.sleep(2)  # Wait for the page to load

    def locate_element_by_text(self, text, element_type="link"):
        """
        Locate an element by text and return its center coordinates.
        """
        try:
            element = None
            if element_type == "link":
                element = self.driver.find_element(By.LINK_TEXT, text)
            elif element_type == "input":
                # Try different strategies for input fields
                selectors = [
                    f"//input[@placeholder='{text}']",
                    f"//input[@name='{text}']",
                    f"//input[@type='{text}']",
                    f"//label[contains(text(), '{text}')]//following::input[1]",
                    f"//div[contains(text(), '{text}')]//following::input[1]",
                ]
                for selector in selectors:
                    try:
                        element = self.driver.find_element(By.XPATH, selector)
                        break
                    except:
                        continue
            elif element_type == "button":
                # Try different strategies for buttons
                selectors = [
                    f"//button[contains(text(), '{text}')]",
                    f"//button[@type='{text}']",
                    f"//div[contains(@class, 'button') and contains(text(), '{text}')]",
                    f"//*[contains(@class, 'button') and contains(text(), '{text}')]",
                ]
                for selector in selectors:
                    try:
                        element = self.driver.find_element(By.XPATH, selector)
                        break
                    except:
                        continue

            if element:
                location = element.location
                size = element.size
                center_x = location["x"] + (size["width"] / 2)
                center_y = location["y"] + (size["height"] / 2)
                logger.info(
                    f"Located {element_type} element '{text}' at ({center_x}, {center_y})"
                )
                return element, (center_x, center_y)
            else:
                logger.warning(
                    f"Could not locate {element_type} element with text '{text}'"
                )
                return None, (None, None)

        except Exception as e:
            logger.error(f"Error locating {element_type} element '{text}': {e}")
            return None, (None, None)

    def click_element(self, element):
        """Click on a web element."""
        try:
            element.click()
            logger.info("Clicked element successfully")
            return True
        except Exception as e:
            logger.error(f"Error clicking element: {e}")
            return False

    def type_text(self, element, text):
        """Type text into an element."""
        try:
            element.clear()
            element.send_keys(text)
            logger.info(f"Typed text into element")
            return True
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return False

    def cleanup(self):
        """Clean up browser resources."""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("Browser closed successfully")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    def __del__(self):
        """Ensure cleanup on object destruction."""
        self.cleanup()
