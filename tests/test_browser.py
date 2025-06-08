import pytest
import random
from playwright.sync_api import sync_playwright
import json

def get_random_filters():
    """Get random region and food category combinations"""
    regions = [
        ('朝阳区', 'r14'),
        ('海淀区', 'r17'), 
        ('东城区', 'r15'),
        ('西城区', 'r16'),
        ('丰台区', 'r20')
    ]
    
    categories = [
        ('火锅', 'g110'),
        ('日本料理', 'g113'), 
        ('韩国料理', 'g114'),
        ('西餐', 'g116'),
        ('自助餐', 'g111')
    ]
    
    return random.choice(regions), random.choice(categories)

def test_browser_launch():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        assert page is not None
        browser.close()

def test_dianping_login():
    """Test login functionality and ensure user session is established"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        page = browser.new_page()
        
        # Set user agent to avoid detection 
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        print("Navigating to Beijing homepage...")
        page.goto('https://www.dianping.com/beijing', wait_until='domcontentloaded')
        
        # Wait for initial page load
        print("Waiting for page content to fully load...")
        page.wait_for_selector('.top-nav', state='visible', timeout=30000)
        
        print("Checking login status...")
        login_link = page.locator('.login-container a[href*="account.dianping.com/login"]')
        
        if login_link.is_visible():
            print("Login required. Please login manually. Waiting for 10 minutes...")
            login_link.click()
            
            # Wait for login completion and main page reload
            print("Waiting for login completion...")
            page.wait_for_selector('div.home_root', state='visible', timeout=600000)
            page.wait_for_selector('div.user-container', state='visible', timeout=10000)
            page.wait_for_selector('p.nick-name', state='visible', timeout=10000)
            print("Login successful, detected user profile")
            
            # Store cookies for future use
            storage_state = browser.contexts[0].storage_state()
            with open("auth.json", "w") as f:
                json.dump(storage_state, f)
            print("Saved authentication state")
            
        page.close()
        browser.close()
        
def test_query_listings():
    """Test querying restaurant listings with filters"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        context = browser.new_context(storage_state="auth.json")
        page = context.new_page()
        
        # Navigate to Beijing food category
        print("Navigating to Beijing food listings...")
        page.goto('https://www.dianping.com/beijing/ch10', wait_until='domcontentloaded')
        
        # Wait for filter options to load
        print("Waiting for filters to load...")
        page.wait_for_selector('.J_filter_box', timeout=30000)
        
        # Apply filters
        print("Applying filters...")
        
        # Select region (e.g., Haidian)
        region_filter = page.locator('text=海淀区')
        region_filter.click()
        
        # Select cuisine type (e.g., Hot Pot)
        cuisine_filter = page.locator('text=火锅')
        cuisine_filter.click()
        
        # Wait for filtered results
        print("Waiting for filtered results...")
        page.wait_for_selector('.shop-list', timeout=30000)
        
        # Extract restaurant data
        shops = page.locator('.shop-list .txt')
        shop_count = shops.count()
        assert shop_count > 0, "No restaurants found matching filters"
        
        # Get first page of results
        results = []
        for i in range(shop_count):
            shop = shops.nth(i)
            name = shop.locator('.tit h4').text_content()
            rating = shop.locator('.comment').text_content()
            results.append({
                'name': name,
                'rating': rating
            })
            
        print(f"Found {len(results)} restaurants")
        
        page.close()
        browser.close()
        
def test_multiple_queries():
    """Test multiple random combinations of region and category filters"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        context = browser.new_context(storage_state="auth.json")
        page = context.new_page()
        
        # Run 3 random combinations
        for i in range(3):
            region, category = get_random_filters()
            print(f"\nTest #{i+1}: {region[0]} + {category[0]}")
            
            # Navigate to filtered URL
            url = f"https://www.dianping.com/beijing/ch10/{region[1]}{category[1]}"
            print(f"Navigating to: {url}")
            page.goto(url, wait_until='networkidle')
            
            # Wait for page load
            page.wait_for_selector('.shop-list', timeout=30000)
            
            # Verify listings loaded
            shop_list = page.locator('.shop-list .txt')
            shop_count = shop_list.count()
            print(f"Found {shop_count} restaurants")
            assert shop_count > 0, "No restaurants found"
            
            # Sample shop data
            first_shop = shop_list.first
            name = first_shop.locator('.tit h4').text_content()
            rating = first_shop.locator('.comment').text_content()
            print(f"Sample listing: {name} ({rating})")
            
            # Optional: Take screenshot
            page.screenshot(path=f"query_test_{i+1}.png")
            
        page.close()
        browser.close()

if __name__ == "__main__":
    pytest.main(['-v', __file__])