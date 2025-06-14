import pytest
from pathlib import Path
import json
import asyncio
from playwright.async_api import async_playwright
from server import get_page, load_menu, load_regions, dianping_category_rank

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def browser():
    """Create a browser instance that persists for all tests"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        yield browser
        await browser.close()

@pytest.mark.asyncio
async def test_login():
    """Test login state using saved auth"""
    context, page = await get_page('https://www.dianping.com/beijing')
    assert context is not None, "Failed to get authenticated context"
    assert page is not None, "Failed to create page"
    
    try:
        # Get and verify nickname using correct selectors
        username_element = await page.wait_for_selector('.userinfo-container .username', state='visible', timeout=10000)
        username = await username_element.text_content()
        username = username.strip()
        print(f"Login verified - User: {username}")
                
        # Additional login checks
        assert username, "Username is empty"
        assert not await page.locator('.login-container a[href*="account.dianping.com/login"]').is_visible(), \
            "Login link visible - not logged in"
        
    finally:
        if page:
            await page.close()

@pytest.mark.asyncio
async def test_category_rank_basic():
    """Test basic category ranking for restaurants in Beijing"""
    result = await dianping_category_rank('beijing', '火锅')
    print(f"Category rank result: {result}")
    assert result['success'], "Category rank query failed"
    assert len(result['result']) > 0, "No shops returned"
    
    # Verify shop data structure
    shop = result['result'][0]
    assert 'shop_id' in shop, "Missing shop_id"
    assert 'name' in shop, "Missing name"
    assert 'rating' in shop, "Missing rating"
    assert 'address' in shop, "Missing address"

@pytest.mark.asyncio
async def test_category_rank_with_region():
    """Test category ranking with region filter"""
    result = await dianping_category_rank('beijing', '日本菜', region='三里屯/工体')
    print(f"Category rank result: {result}")
    assert result['success'], "Category rank query failed"
    assert len(result['result']) > 0, "No shops returned"
    
    # Verify location filtering
    for shop in result['result']:
        assert '朝阳' in shop['address'] or '三里屯' in shop['address'], \
            f"Shop not in expected region: {shop['address']}"
@pytest.mark.asyncio
async def test_category_rank_with_sort():
    """Test category ranking with different sort options"""
    result = await dianping_category_rank('beijing', '西餐', sort='o3')
    print(f"Category rank result: {result}")
    assert result['success'], "Category rank query failed"
    assert len(result['result']) > 0, "No shops returned"
    
    # Verify shop data structure
    shop = result['result'][0]
    assert 'shop_id' in shop, "Missing shop_id"
    assert 'name' in shop, "Missing name"
    assert 'rating' in shop, "Missing rating"
    assert 'address' in shop, "Missing address"

# Sync tests can remain unchanged
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
    pytest.main(['-v', '-s', __file__])