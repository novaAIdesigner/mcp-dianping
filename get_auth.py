from playwright.sync_api import sync_playwright
import json
from pathlib import Path

def get_auth():
    """Get authentication state from dianping.com and save to auth.json"""
    with sync_playwright() as p:
        # Launch browser with anti-detection
        browser = p.chromium.launch(
            headless=False, 
            args=['--disable-blink-features=AutomationControlled']
        )
        page = browser.new_page()
        
        # Set anti-detection headers
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        # Navigate to homepage
        page.goto('https://www.dianping.com/beijing', wait_until='domcontentloaded')
        page.wait_for_selector('.top-nav', state='visible', timeout=30000)
        
        # Check login status
        login_link = page.locator('.login-container a[href*="account.dianping.com/login"]')
        
        if login_link.is_visible():
            print("Please login in the browser window...")
            login_link.click()
            
            # Wait for login completion
            page.wait_for_selector('div.home_root', state='visible', timeout=600000)
            page.wait_for_selector('div.user-container', state='visible', timeout=10000)
            page.wait_for_selector('p.nick-name', state='visible', timeout=10000)
            print("Login successful!")
            
            # Save authentication state
            storage_state = browser.contexts[0].storage_state()
            auth_file = Path("auth.json")
            auth_file.write_text(json.dumps(storage_state))
            print(f"Authentication saved to {auth_file}")
        else:
            print("Already logged in")
            
        page.close()
        browser.close()

if __name__ == "__main__":
    get_auth()