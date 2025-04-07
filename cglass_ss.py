from selenium import webdriver
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.chrome.options import Options
import time
import subprocess
import re
import platform
import json

def capture_tradingview_screenshot(ticker='NONE'):
    # Login to TradingView
    chrome_options = Options()
    #chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--force-dark-mode')
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--window-size=1280,720")
    
    driver = webdriver.Chrome(options=chrome_options)
    # https://www.tradingview.com/chart/LuDjaV3K/
    url = "https://www.coinglass.com/tv/" + str(ticker)
    
    # Navigate to the URL
    driver.get(url)

    # Wait for a few seconds for the new page to load
    time.sleep(3)
  
    print('Chart is ready for capture')
    
    try:
        # Find iframe that starts with "tradingview_"
        iframes = driver.find_elements("css selector", "iframe[id^='tradingview_']")
        if iframes:
            iframe = iframes[0]  # Get the first matching iframe
            # Click on the iframe first
            ActionChains(driver).move_to_element(iframe).click().perform()
            print("Clicked on iframe")
            
            # Switch to the iframe
            driver.switch_to.frame(iframe)
            print("Switched to TradingView iframe")
            
            # Wait a bit for iframe to be fully focused
            time.sleep(2)
            
            # Send the keyboard shortcut
            ActionChains(driver)\
                .key_down(Keys.ALT)\
                .send_keys('s')\
                .key_up(Keys.ALT)\
                .perform()
            
            print('Attempted to capture screenshot')
            
            # Switch back to main content
            driver.switch_to.default_content()
        else:
            print("No TradingView iframe found")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        driver.switch_to.default_content()

    time.sleep(10)
    
    # Use pbpaste for macOS clipboard content
    if platform.system() == 'Darwin':  # macOS
        clipboard = subprocess.check_output(['pbpaste']).decode('utf-8')
    else:  # Linux
        clipboard = subprocess.check_output(['xclip', '-o']).decode('utf-8')
    
    time.sleep(5)    
        
    quit_browser(driver)

    return clipboard

def quit_browser(driver):
    driver.quit()

def convert_coinglass_response(response_string):
    try:
        # Extract the imageId from the JSON response
        response = json.loads(response_string)
        if response["success"] and "imageId" in response["data"]:
            image_id = response["data"]["imageId"]
            # Construct the correct image URL for coinglass
            image_url = f"https://cdn.coinglasscdn.com/snapshot/{image_id}.png"
            return image_url
    except Exception as e:
        print(f"Error parsing response: {str(e)}")
    return response_string

# Example usage:
clipboard_data = capture_tradingview_screenshot("Binance_RAREUSDT")
print('Raw response:', clipboard_data)
# https://www.coinglass.com/tv/Binance_RAREUSDT


# Convert the response to the correct coinglass image URL format
image_url = convert_coinglass_response(clipboard_data)
print('Image URL:', image_url)
