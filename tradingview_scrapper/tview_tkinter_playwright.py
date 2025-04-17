from playwright.sync_api import sync_playwright
import time
from tkinter import Tk
import re

def capture_tradingview_screenshot(ticker='NONE'):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # Set to True for headless mode
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--force-dark-mode',
                '--disable-extensions',
            ]
        )
        
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720}
        )
        page = context.new_page()
        
        url = "https://in.tradingview.com/chart/LuDjaV3K/?symbol=" + str(ticker)
        
        try:
            # Navigate and wait for initial load
            page.goto(url, wait_until='domcontentloaded')
            
            # Wait for the trading view chart iframe to be present
            chart_frame = page.wait_for_selector('iframe[id="trading-view-widget-iframe"]', state='visible', timeout=30000)
            
            if chart_frame:
                # Get the frame handle
                frame = page.frame_locator('iframe[id="trading-view-widget-iframe"]')
                
                # Wait for the chart container inside the frame
                frame.locator('div[class*="chart-container"]').wait_for(state='visible', timeout=30000)
                
                # Switch focus to main page
                page.bring_to_front()
                
                # Additional wait for chart to render
                time.sleep(5)
                
                print('Chart is ready for capture')
                
                # Focus the chart area
                frame.locator('div[class*="chart-container"]').click()
                
                # Send keyboard shortcut
                page.keyboard.down("Alt")
                page.keyboard.down("s")
                page.keyboard.up("s")
                page.keyboard.up("Alt")
                
                # Wait for screenshot processing
                time.sleep(10)
                
                # Get clipboard content
                clipboard = Tk().clipboard_get()
                time.sleep(5)
                
                return clipboard
            else:
                print("Chart frame not found")
                return None
                
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            return None
            
        finally:
            browser.close()

def convert_tradingview_links(input_string):
    # Define a regex pattern to find links of the format 'https://www.tradingview.com/x/...'
    pattern = r'https://www\.tradingview\.com/x/([a-zA-Z0-9]+)/'

    # Find all matching links in the input string
    matches = re.findall(pattern, input_string)

    # Iterate through the matches and replace them
    for match in matches:
        old_link = f'https://www.tradingview.com/x/{match}/'
        new_link = f'https://s3.tradingview.com/snapshots/{match[0].lower()}/{match}.png'
        input_string = input_string.replace(old_link, new_link)

    return input_string

# Example usage:
clipboard_data = capture_tradingview_screenshot("BYBIT:BTCUSDT.P")
print('ertu:', clipboard_data)

if clipboard_data:
    clipboard_data = convert_tradingview_links("Chart Link: " + str(clipboard_data))
    print(clipboard_data)
