from selenium import webdriver
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchFrameException
import time
import json
import logging
import os # Add os import
from dotenv import load_dotenv # Add load_dotenv import

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class CoinglassScraperError(Exception):
    """Custom exception for scraper errors."""
    pass


class CoinglassScraper:
    """
    A scraper for capturing TradingView chart snapshots from Coinglass.
    """
    BASE_URL = "https://www.coinglass.com/tv/"
    CLIPBOARD_WAIT_TIMEOUT = 10  # seconds to wait for iframe/elements
    MAX_CLIPBOARD_ATTEMPTS = 5
    CLIPBOARD_RETRY_INTERVAL = 1  # seconds between attempts
    ACTION_DELAY = 0.5 # Small delay for actions

    def __init__(self, headless=True, window_size="1920,1080"):
        self.headless = headless
        self.window_size = window_size
        self.driver = None
        self.wait = None

    def _setup_driver(self):
        """Configures and initializes the Chrome WebDriver."""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--force-dark-mode')
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument(f"--window-size={self.window_size}")

        prefs = {
            "profile.content_settings.exceptions.clipboard": {
                "[*.]coinglass.com,*": {"setting": 1}  # Allow clipboard access
            }
        }
        chrome_options.add_experimental_option("prefs", prefs)

        try:
            # Replace local Chrome driver with Bright Data Remote driver
            command_executor_url = os.environ.get('BRIGHTDATA_COMMAND_EXECUTOR')
            if not command_executor_url:
                logging.error("BRIGHTDATA_COMMAND_EXECUTOR environment variable not set.")
                raise CoinglassScraperError("BRIGHTDATA_COMMAND_EXECUTOR environment variable not set.")

            self.driver = webdriver.Remote(
                command_executor=command_executor_url,
                options=chrome_options # Pass options here
            )
            # self.driver = webdriver.Chrome(options=chrome_options) # Remove old local driver init
            self.wait = WebDriverWait(self.driver, self.CLIPBOARD_WAIT_TIMEOUT)
            logging.info("Remote WebDriver initialized successfully via Bright Data.")
        except WebDriverException as e:
            logging.error(f"Failed to initialize WebDriver: {e}")
            raise CoinglassScraperError("WebDriver initialization failed") from e

    def _navigate_to_page(self, ticker):
        """Navigates to the specific Coinglass ticker page."""
        url = f"{self.BASE_URL}{ticker}"
        logging.info(f"Navigating to {url}")
        try:
            self.driver.get(url)
        except WebDriverException as e:
            logging.error(f"Failed to navigate to {url}: {e}")
            raise CoinglassScraperError(f"Navigation to {url} failed") from e

    def _find_and_switch_to_iframe(self):
        """Finds the TradingView iframe and switches context to it."""
        try:
            iframe = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[id^='tradingview_']"))
            )
            logging.info("TradingView iframe found.")
            # Click iframe first to potentially help focus
            ActionChains(self.driver).move_to_element(iframe).click().perform()
            time.sleep(self.ACTION_DELAY) # Short pause after click
            self.driver.switch_to.frame(iframe)
            logging.info("Switched to TradingView iframe.")
            return iframe # Return iframe element for potential later use
        except TimeoutException:
            logging.error("Timeout waiting for TradingView iframe.")
            raise CoinglassScraperError("TradingView iframe not found")
        except NoSuchFrameException as e:
             logging.error(f"Error switching to iframe: {e}")
             raise CoinglassScraperError("Could not switch to TradingView iframe") from e
        except WebDriverException as e:
            logging.error(f"WebDriver error interacting with iframe: {e}")
            raise CoinglassScraperError("Error interacting with TradingView iframe") from e

    def _trigger_copy_action(self):
        """Sends the Alt+S key combination to trigger the copy action."""
        logging.info("Sending Alt+S key combination...")
        try:
            ActionChains(self.driver).key_down(Keys.ALT).send_keys('s').key_up(Keys.ALT).perform()
            logging.info("Alt+S sent.")
            # Wait a moment for the copy action to potentially complete
            time.sleep(2) # Keep original sleep as clipboard action might take time
        except WebDriverException as e:
            logging.error(f"Failed to send Alt+S keys: {e}")
            raise CoinglassScraperError("Failed to send Alt+S key combination") from e

    def _read_clipboard_with_retry(self, iframe_element):
        """Attempts to read clipboard content via JS with retries."""
        clipboard_content = None
        for attempt in range(self.MAX_CLIPBOARD_ATTEMPTS):
            logging.info(f'Attempting to get clipboard content (attempt {attempt + 1}/{self.MAX_CLIPBOARD_ATTEMPTS})...')
            try:
                # 1. Switch back to default content
                self.driver.switch_to.default_content()
                time.sleep(self.ACTION_DELAY)

                # 2. Click iframe to ensure focus before interaction
                ActionChains(self.driver).move_to_element(iframe_element).click().perform()
                time.sleep(self.ACTION_DELAY)

                # 3. Switch into the iframe
                self.driver.switch_to.frame(iframe_element)
                time.sleep(self.ACTION_DELAY)

                # 4. Trigger copy action (Alt+S) inside the iframe
                self._trigger_copy_action()

                # 5. Switch back to default content to run JS for clipboard read
                self.driver.switch_to.default_content()
                time.sleep(self.ACTION_DELAY) # Give browser time to switch context

                # 6. Attempt to read clipboard
                logging.info("Attempting to read remote clipboard via JavaScript...")
                # Re-focusing potentially needed before reading clipboard
                ActionChains(self.driver).move_to_element(iframe_element).click().perform()
                time.sleep(self.ACTION_DELAY)
                self.driver.switch_to.frame(iframe_element) # Switch back IN to potentially execute JS in correct context
                clipboard_content = self.driver.execute_script("return navigator.clipboard.readText();")
                logging.info(f'Clipboard content via JS: {"[empty]" if not clipboard_content else "[content received]"}')
                self.driver.switch_to.default_content() # Switch back out

                if clipboard_content and clipboard_content.strip():
                    logging.info("Remote clipboard content retrieved via JS.")
                    return clipboard_content
                else:
                    logging.warning("Remote clipboard empty or JS returned no content.")

            except WebDriverException as js_err:
                logging.warning(f"Error interacting or reading remote clipboard via JavaScript: {js_err}")
                try:
                    # Ensure we are in default content after error
                    self.driver.switch_to.default_content()
                except WebDriverException:
                    logging.error("Failed to switch to default content during error handling.")
                    pass # Continue retry loop if possible

            if attempt < self.MAX_CLIPBOARD_ATTEMPTS - 1:
                 logging.info(f"Clipboard empty/no content yet, waiting {self.CLIPBOARD_RETRY_INTERVAL}s before retrying...")
                 time.sleep(self.CLIPBOARD_RETRY_INTERVAL)

        logging.error("Failed to get clipboard content after multiple attempts.")
        raise CoinglassScraperError("Failed to get clipboard content after multiple attempts")

    def _convert_coinglass_response(self, response_string):
        """Parses the JSON response from clipboard and extracts the image URL."""
        try:
            response = json.loads(response_string)
            if response.get("success") and "imageId" in response.get("data", {}):
                image_id = response["data"]["imageId"]
                image_url = f"https://cdn.coinglasscdn.com/snapshot/{image_id}.png"
                logging.info(f"Successfully extracted image URL: {image_url}")
                return image_url
            else:
                logging.warning(f"Clipboard JSON response did not contain success/imageId: {response_string}")
                return response_string # Return original if format unexpected
        except json.JSONDecodeError:
            logging.warning(f"Clipboard content was not valid JSON: {response_string}")
            return response_string # Return original if not JSON
        except Exception as e:
            logging.error(f"Error processing clipboard response: {e}")
            return response_string # Return original on other errors

    def get_tradingview_image_url(self, ticker='Binance_BTCUSDT'):
        """
        Main method to orchestrate the scraping process and return the image URL.
        """
        if not self.driver:
             self._setup_driver()

        try:
            self._navigate_to_page(ticker)
            iframe_element = self._find_and_switch_to_iframe()
            # Initial switch back to default content before retry loop
            self.driver.switch_to.default_content()
            time.sleep(self.ACTION_DELAY)

            clipboard_data = self._read_clipboard_with_retry(iframe_element)
            image_url = self._convert_coinglass_response(clipboard_data)
            return image_url

        except CoinglassScraperError as e:
            logging.error(f"Scraping failed: {e}")
            return None # Or re-raise if preferred
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}", exc_info=True)
            # Ensure we switch back to default content in case of unexpected error
            try:
                 if self.driver: self.driver.switch_to.default_content()
            except WebDriverException:
                 pass
            return None # Or re-raise
        # No finally block needed here for driver quit if using __enter__/__exit__

    def close(self):
        """Closes the WebDriver."""
        if self.driver:
            logging.info("Quitting browser...")
            try:
                self.driver.quit()
                logging.info("Browser quit successfully.")
                self.driver = None
            except WebDriverException as e:
                logging.error(f"Error quitting WebDriver: {e}")

    # Context manager support
    def __enter__(self):
        self._setup_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Example Usage:
if __name__ == "__main__":
    ticker_to_capture = "Binance_BTCUSDT"
    image_url = None

    # Using the context manager
    try:
        with CoinglassScraper(headless=True) as scraper:
            image_url = scraper.get_tradingview_image_url(ticker_to_capture)
    except CoinglassScraperError as e:
        logging.error(f"Failed to get image URL for {ticker_to_capture}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during scraping: {e}", exc_info=True)


    if image_url:
        print(f'Successfully retrieved Image URL for {ticker_to_capture}:')
        print(image_url)
    else:
        print(f"Failed to retrieve image URL for {ticker_to_capture}.")