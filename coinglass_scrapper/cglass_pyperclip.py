from selenium import webdriver
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.chrome.options import Options
import time
import subprocess
import re
import platform
import json
from tkinter import Tk
import pyperclip
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

def capture_tradingview_screenshot(ticker='NONE'):
    chrome_options = Options()
    chrome_options.add_argument('--headless') # Keep headless commented for debugging if needed
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--force-dark-mode')
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--window-size=1280,720")
    
    driver = webdriver.Chrome(options=chrome_options)
    clipboard_content = None 
    try:
        url = "https://www.coinglass.com/tv/" + str(ticker)
        driver.get(url)

        wait = WebDriverWait(driver, 10)
        iframe = wait.until(
            EC.presence_of_element_located(("css selector", "iframe[id^='tradingview_']"))
        )
        print('iframe:', iframe)
        
        # This inner try/finally structure handles the core logic and ensures cleanup
        try:
            ActionChains(driver).move_to_element(iframe).click().perform()
            print("Clicked iframe element.")
            driver.switch_to.frame(iframe)
            print("Switched to iframe.")
            time.sleep(2) # Allow time for iframe to potentially load/settle

            pyperclip.copy('')
            print("Clipboard cleared before attempt.")

            driver.switch_to.default_content()

            max_attempts = 5 
            wait_interval = 1 
            for attempt in range(max_attempts):
                print(f'Attempting to get clipboard content (attempt {attempt + 1}/{max_attempts})...')

                ActionChains(driver).move_to_element(iframe).click().perform()
                # print("Clicked iframe element.") # Repetitive log
                driver.switch_to.frame(iframe)
                # print("Switched to iframe.") # Repetitive log
                time.sleep(0.5) 

                print("Sending Alt+S...")
                ActionChains(driver).key_down(Keys.ALT).key_down('s').key_up(Keys.ALT).key_up('s').perform()
                print("Alt+S sent.")
                time.sleep(2) # Wait for screenshot action to potentially populate clipboard

                driver.switch_to.default_content()
                time.sleep(0.5) 

                try:
                    clipboard_content = pyperclip.paste()
                    print('Clipboard content check:', clipboard_content)
                    if clipboard_content and clipboard_content.strip() != '':
                        print("Clipboard content retrieved.") 
                        break
                except Exception as clip_err:
                    print(f"Clipboard access error: {clip_err}")
                    # Continue loop even if there's a temporary access issue

                print("Clipboard empty/no content yet, retrying...")
                time.sleep(wait_interval)

            if clipboard_content and clipboard_content.strip() != '':
                return clipboard_content
            else:
                # Attempt to save a screenshot for debugging failure
                try:
                    debug_screenshot_path = f"debug_screenshot_fail_{int(time.time())}.png"
                    driver.save_screenshot(debug_screenshot_path)
                    print(f"Saved debug screenshot to {debug_screenshot_path}")
                except Exception as screenshot_err:
                    print(f"Failed to save debug screenshot on failure: {screenshot_err}")
                
                print("Failed to get clipboard content after multiple attempts.")
                raise Exception("Failed to get clipboard content after multiple attempts")
                
        # This except block catches errors during the main interaction phase (clicking, sending keys, etc.)
        except Exception as interaction_err:
            print(f"Interaction Error: {str(interaction_err)}")
            # Attempt to save a screenshot for debugging the error
            try:
                debug_screenshot_path = f"debug_screenshot_error_{int(time.time())}.png"
                driver.save_screenshot(debug_screenshot_path)
                print(f"Saved debug screenshot to {debug_screenshot_path}")
            except Exception as screenshot_err:
                print(f"Failed to save debug screenshot during error handling: {screenshot_err}")
            
            # Attempt to switch back to default content before quitting in finally
            try:
                if driver: 
                    driver.switch_to.default_content()
            except Exception as switch_err:
                print(f"Error switching back to default content during error handling: {switch_err}")
            # Let the finally block handle quitting and clipboard clearing
            return None 
        finally:
            # This finally block ensures cleanup happens after the inner try/except
            print("Entering inner finally block for cleanup...")
            # Clipboard clearing and browser quitting are handled by the outer finally block
            pass # No specific action needed here now, outer finally handles it

    # This except block catches errors during initial setup (e.g., driver init, navigation, finding iframe)
    except Exception as setup_err:
        print(f"Setup Error: {str(setup_err)}")
        # Attempt screenshot if driver exists
        if 'driver' in locals() and driver:
            try:
                debug_screenshot_path = f"debug_screenshot_setup_error_{int(time.time())}.png"
                driver.save_screenshot(debug_screenshot_path)
                print(f"Saved debug screenshot to {debug_screenshot_path}")
            except Exception as screenshot_err:
                print(f"Failed to save debug screenshot during setup error handling: {screenshot_err}")
        # Let the finally block handle potential driver quitting and clipboard clearing
        return None 
    finally:
        # This outer finally block ensures clipboard is always cleared and browser is always quit
        print("Entering outer finally block for cleanup...")
        try:
            pyperclip.copy('')
            print("Clipboard cleared in outer finally.")
        except Exception as clip_clear_err:
            print(f"Error clearing clipboard in outer finally block: {clip_clear_err}")
        
        if 'driver' in locals() and driver: # Check if driver was initialized before trying to quit
            quit_browser(driver)

def quit_browser(driver):
    print("Quitting browser...")
    driver.quit()
    print("Browser quit.")

def convert_coinglass_response(response_string):
    try:
        # Process the JSON response if possible
        response = json.loads(response_string)
        if response.get("success") and "imageId" in response.get("data", {}):
            image_id = response["data"]["imageId"]
            image_url = f"https://cdn.coinglasscdn.com/snapshot/{image_id}.png"
            return image_url
    except json.JSONDecodeError:
        print("Clipboard content was not valid JSON.")
    except Exception as e:
        print(f"Error processing clipboard response: {str(e)}")
    # Return the original string if it wasn't processable JSON or an error occurred
    return response_string

# Example usage:
clipboard_data = capture_tradingview_screenshot("Binance_BTCUSDT")
print('\nRaw response received from capture function:')
print(clipboard_data)

if clipboard_data: 
    image_url = convert_coinglass_response(clipboard_data)
    print('\nConverted Image URL (or original response if conversion failed):')
    print(image_url)
else:
    print("\nNo clipboard data captured, skipping conversion.")
