import pytest
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
from server import get_page, load_menu, load_regions

@pytest.fixture(scope="session")
def playwright_browser():
    """Create a browser instance that persists for all tests"""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        yield browser
        browser.close()

@pytest.fixture(scope="session")
def auth_context(playwright_browser):
    """Create an authenticated context for tests"""
    auth_file = Path("auth.json")
    if not auth_file.exists():
        pytest.skip("auth.json not found - run get_auth.py first")
        
    try:
        with open(auth_file) as f:
            auth_data = json.load(f)
    except json.JSONDecodeError:
        pytest.fail("Invalid auth.json format")
        
    context = playwright_browser.new_context(storage_state=str(auth_file))
    yield context
    context.close()

def test_auth_file_exists():
    """Test if auth.json exists and is valid JSON"""
    auth_file = Path("auth.json")
    assert auth_file.exists(), "auth.json not found"
    
    try:
        with open(auth_file) as f:
            auth_data = json.load(f)
        assert "cookies" in auth_data, "auth.json missing cookies data"
        assert "origins" in auth_data, "auth.json missing origins data"
    except json.JSONDecodeError:
        pytest.fail("auth.json contains invalid JSON")

def test_login_verification(auth_context):
    """Test login state using saved auth"""
    page = auth_context.new_page()
    
    try:
        # Navigate to homepage
        print("Navigating to Beijing homepage...")
        page.goto('https://www.dianping.com/beijing', wait_until='domcontentloaded')
        
        # Wait for initial page load and verify user profile
        print("Verifying login status...")
        page.wait_for_selector('.username', state='visible', timeout=10000)
        
        # Get and verify nickname using correct selectors
        username_element = page.wait_for_selector('.userinfo-container .username', state='visible', timeout=10000)
        username = username_element.text_content().strip()
        print(f"Login verified - User: {username}")
                
        # Additional login checks
        assert username, "Username is empty"
        assert page.locator('.userinfo-container'), "User info container not found"
        
    finally:
        page.close()

def test_load_menu():
    """Test menu loading from file"""
    menu = load_menu()
    assert menu, "Menu is empty"
    
    # Test some expected categories
    expected_categories = ['美食', '火锅', '日本菜', '西餐']
    for category in expected_categories:
        assert category in menu, f"Category '{category}' not found in menu"
        assert menu[category].startswith('/ch'), \
            f"Invalid URL format for category '{category}': {menu[category]}"

def test_load_regions():
    """Test region loading from file"""
    regions = load_regions()
    assert regions, "Regions dict is empty"
    
    # Test Beijing regions
    assert 'beijing' in regions, "Beijing not found in regions"
    beijing = regions['beijing']
    assert beijing, "Beijing regions empty"
    
    # Test some expected regions
    expected_regions = ['三里屯/工体', '国贸/建外']
    for region in expected_regions:
        assert region in beijing, f"Region '{region}' not found in Beijing"
        assert beijing[region].startswith('r'), \
            f"Invalid region code format for '{region}': {beijing[region]}"

if __name__ == "__main__":
    pytest.main(['-v', __file__])