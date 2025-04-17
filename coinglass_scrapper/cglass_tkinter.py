from selenium import webdriver
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.chrome.options import Options
import time
import subprocess
import re
import platform
import json
from tkinter import Tk
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

def capture_tradingview_screenshot(ticker='NONE'):
    # Login to TradingView
    chrome_options = Options()
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--force-dark-mode')
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--window-size=1280,720")
    chrome_options.add_argument('--blink-settings=imagesEnabled=false')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-software-rasterizer')
    
    driver = webdriver.Chrome(options=chrome_options)
    # https://www.tradingview.com/chart/LuDjaV3K/
    url = "https://www.coinglass.com/tv/" + str(ticker)
    
    # Navigate to the URL
    driver.get(url)

    # Wait for iframe with explicit wait instead of sleep
    wait = WebDriverWait(driver, 10)
    iframe = wait.until(
        EC.presence_of_element_located(("css selector", "iframe[id^='tradingview_']"))
    )
    
    try:
        # Click and switch to iframe
        ActionChains(driver).move_to_element(iframe).click().perform()
        driver.switch_to.frame(iframe)
        
        # Reduce wait time
        time.sleep(1)  # Short pause for iframe focus
        
        ActionChains(driver)\
            .key_down(Keys.ALT)\
            .send_keys('s')\
            .key_up(Keys.ALT)\
            .perform()
        
        driver.switch_to.default_content()
        
        # Wait for clipboard content with timeout
        max_attempts = 10
        clipboard_content = None
        for _ in range(max_attempts):
            try:
                clipboard_content = Tk().clipboard_get()
                if clipboard_content:
                    break
            except:
                time.sleep(1)
                continue
        
        if clipboard_content:
            quit_browser(driver)
            return clipboard_content
        else:
            raise Exception("Failed to get clipboard content")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        driver.switch_to.default_content()
        quit_browser(driver)
        return None

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
clipboard_data = capture_tradingview_screenshot("Binance_BTCUSDT")
print('Raw response:', clipboard_data)
# https://www.coinglass.com/tv/Binance_RAREUSDT


# Convert the response to the correct coinglass image URL format
image_url = convert_coinglass_response(clipboard_data)
print('Image URL:', image_url)
