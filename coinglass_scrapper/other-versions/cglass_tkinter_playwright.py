from playwright.sync_api import sync_playwright
import time
import json
from tkinter import Tk
import platform as sys_platform
import os

def capture_tradingview_screenshot(ticker='NONE', browser_type='chromium'):
    with sync_playwright() as p:
        # Select browser type based on parameter
        browser_launcher = getattr(p, browser_type.lower())
        
        # Launch browser with appropriate options
        browser = browser_launcher.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',  # Helps with cross-origin iframe issues
                '--disable-features=IsolateOrigins,site-per-process'  # Important for iframe access
            ]
        )
        
        # Create context with appropriate viewport settings
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            permissions=["clipboard-read", "clipboard-write"]
        )
        
        page = context.new_page()
        
        # Navigate to the URL
        url = f"https://www.coinglass.com/tv/{ticker}"
        print(f"Navigating to {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        print("Page loaded, waiting for iframe to initialize...")
        
        # Give the page some time to load initial content
        page.wait_for_timeout(5000)
        
        try:
            # Properly locate and interact with the TradingView iframe
            # This is the correct way to handle iframes in Playwright
            iframe_locator = page.frame_locator("iframe[id^='tradingview_']")
            
            # Check if iframe was found
            if iframe_locator:
                print("TradingView iframe found, waiting for chart container...")
                
                # Wait for chart container to be visible within iframe
                chart_container = iframe_locator.locator(".chart-container").first
                chart_container.wait_for(state="visible", timeout=30000)
                print("Chart container visible, clicking to focus...")
                
                # Click on chart container to ensure iframe is focused
                chart_container.click()
                print("Chart container clicked")
                
                # Wait to ensure iframe has focus
                page.wait_for_timeout(2000)


                # time.sleep(10000000)
                
                # Send Alt+S keyboard shortcut
                print("Sending Alt+S keyboard shortcut...")
                page.keyboard.press("Alt+s")
                print("Keyboard shortcut sent")
                
                # Wait for clipboard to be populated
                page.wait_for_timeout(5000)
                
                # Get clipboard content
                try:
                    clipboard_content = Tk().clipboard_get()
                    print(f"Retrieved clipboard content: {clipboard_content[:50]}...")
                    
                    # Close browser and return clipboard content
                    browser.close()
                    return clipboard_content
                except Exception as clip_err:
                    print(f"Clipboard error: {str(clip_err)}")
            else:
                print("No TradingView iframe found")
                
        except Exception as e:
            print(f"Error: {str(e)}")
            
        # In case of failure, take a screenshot for debugging
        try:
            debug_path = f"debug_{ticker}_{int(time.time())}.png"
            page.screenshot(path=debug_path)
            print(f"Debug screenshot saved to {debug_path}")
        except:
            pass
            
        # Wait before closing in case of error
        page.wait_for_timeout(5000)
        browser.close()
        
        return None

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
if __name__ == "__main__":
    clipboard_data = capture_tradingview_screenshot("Binance_RAREUSDT")
    print('Raw response:', clipboard_data)
    
    if clipboard_data:
        # Convert the response to the correct coinglass image URL format
        image_url = convert_coinglass_response(clipboard_data)
        print('Image URL:', image_url)
    else:
        print("Failed to capture screenshot")