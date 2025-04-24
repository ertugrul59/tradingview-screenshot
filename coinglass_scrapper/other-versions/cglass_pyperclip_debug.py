from selenium import webdriver
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.chrome.options import Options
import time
import json
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

def capture_tradingview_screenshot(ticker='Binance_BTCUSDT'):
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--force-dark-mode')
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--window-size=1920,1080")
    
    prefs = {
        "profile.content_settings.exceptions.clipboard": {
            "[*.]coinglass.com,*": {"setting": 1} # 1 means Allow
        }
    }
    chrome_options.add_experimental_option("prefs", prefs)

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
        
        try:
            ActionChains(driver).move_to_element(iframe).click().perform()
            print("Clicked iframe element.")
            driver.switch_to.frame(iframe)
            print("Switched to iframe.")
            time.sleep(2) 

            driver.switch_to.default_content()

            max_attempts = 5 
            wait_interval = 1 
            for attempt in range(max_attempts):
                print(f'Attempting to get clipboard content (attempt {attempt + 1}/{max_attempts})...')

                ActionChains(driver).move_to_element(iframe).click().perform()
                driver.switch_to.frame(iframe)
                time.sleep(0.5) 

                print("Sending Alt+S...")
                ActionChains(driver).key_down(Keys.ALT).key_down('s').key_up(Keys.ALT).key_up('s').perform()
                print("Alt+S sent.")

                try:
                    debug_screenshot_path = f"debug_screenshot_after_alt_s_attempt_{attempt + 1}_{int(time.time())}.png"
                    driver.switch_to.default_content() 
                    time.sleep(0.1) 
                    driver.save_screenshot(debug_screenshot_path)
                    print(f"Saved debug screenshot to {debug_screenshot_path}")
                    driver.switch_to.frame(iframe) 
                except Exception as screenshot_err:
                    print(f"Failed to save debug screenshot after Alt+S: {screenshot_err}")
                    try:
                       driver.switch_to.default_content()
                    except:
                        pass 

                time.sleep(2) 

                driver.switch_to.default_content()
                time.sleep(0.5) 

                clipboard_content = None 
                try:
                    print("Clicking iframe to ensure focus before JS execution...")
                    ActionChains(driver).move_to_element(iframe).click().perform()
                    time.sleep(0.2) 

                    driver.switch_to.frame(iframe)
                    print("Attempting to read remote clipboard via JavaScript...")
                    clipboard_content = driver.execute_script("return navigator.clipboard.readText();")
                    print('Clipboard content via JS:', clipboard_content)

                    driver.switch_to.default_content()

                    if clipboard_content and clipboard_content.strip() != '':
                        print("Remote clipboard content retrieved via JS.")
                        break 
                    else:
                         print("Remote clipboard empty or JS returned no content.")

                except Exception as js_err:
                    print(f"Error reading remote clipboard via JavaScript: {js_err}")
                    try:
                        driver.switch_to.default_content()
                    except:
                        pass 

                if not clipboard_content or clipboard_content.strip() == '':
                     print("Clipboard empty/no content yet, retrying...")
                     time.sleep(wait_interval)

            if clipboard_content and clipboard_content.strip() != '':
                return clipboard_content
            else:
                try:
                    debug_screenshot_path = f"debug_screenshot_fail_{int(time.time())}.png"
                    driver.save_screenshot(debug_screenshot_path)
                    print(f"Saved debug screenshot to {debug_screenshot_path}")
                except Exception as screenshot_err:
                    print(f"Failed to save debug screenshot on failure: {screenshot_err}")
                
                print("Failed to get clipboard content after multiple attempts.")
                raise Exception("Failed to get clipboard content after multiple attempts")
                
        except Exception as interaction_err:
            print(f"Interaction Error: {str(interaction_err)}")
            try:
                debug_screenshot_path = f"debug_screenshot_error_{int(time.time())}.png"
                driver.save_screenshot(debug_screenshot_path)
                print(f"Saved debug screenshot to {debug_screenshot_path}")
            except Exception as screenshot_err:
                print(f"Failed to save debug screenshot during error handling: {screenshot_err}")
            
            try:
                if driver: 
                    driver.switch_to.default_content()
            except Exception as switch_err:
                print(f"Error switching back to default content during error handling: {switch_err}")
            return None 
        finally:
            print("Entering inner finally block for cleanup...")
            pass 

    except Exception as setup_err:
        print(f"Setup Error: {str(setup_err)}")
        if 'driver' in locals() and driver:
            try:
                debug_screenshot_path = f"debug_screenshot_setup_error_{int(time.time())}.png"
                driver.save_screenshot(debug_screenshot_path)
                print(f"Saved debug screenshot to {debug_screenshot_path}")
            except Exception as screenshot_err:
                print(f"Failed to save debug screenshot during setup error handling: {screenshot_err}")
        return None 
    finally:
        print("Entering outer finally block for cleanup...")
        # Note: No actual clipboard clearing happens here anymore
        if 'driver' in locals() and driver: 
            quit_browser(driver)

def quit_browser(driver):
    print("Quitting browser...")
    driver.quit()
    print("Browser quit.")

def convert_coinglass_response(response_string):
    try:
        response = json.loads(response_string)
        if response.get("success") and "imageId" in response.get("data", {}):
            image_id = response["data"]["imageId"]
            image_url = f"https://cdn.coinglasscdn.com/snapshot/{image_id}.png"
            return image_url
    except json.JSONDecodeError:
        print("Clipboard content was not valid JSON.")
    except Exception as e:
        print(f"Error processing clipboard response: {str(e)}")
    return response_string

clipboard_data = capture_tradingview_screenshot("Binance_BTCUSDT")
print('\nRaw response received from capture function:')
print(clipboard_data)

if clipboard_data: 
    image_url = convert_coinglass_response(clipboard_data)
    print('\nConverted Image URL (or original response if conversion failed):')
    print(image_url)
else:
    print("\nNo clipboard data captured, skipping conversion.")
