import pytest
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
from server import get_page, load_menu, load_regions, dianping_category_rank

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

def test_login():
    """Test login state using saved auth"""
    context, page = get_page('https://www.dianping.com/beijing')
    assert context is not None, "Failed to get authenticated context"
    assert page is not None, "Failed to create page"
    
    try:
        # Get and verify nickname using correct selectors
        username_element = page.wait_for_selector('.userinfo-container .username', state='visible', timeout=10000)
        username = username_element.text_content().strip()
        print(f"Login verified - User: {username}")
                
        # Additional login checks
        assert username, "Username is empty"
        assert not page.locator('.login-container a[href*="account.dianping.com/login"]').is_visible(), \
            "Login link visible - not logged in"
        
    finally:
        if page:
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

def test_category_rank_basic():
    """Test basic category ranking for restaurants in Beijing"""
    result = dianping_category_rank('beijing', '火锅')
    print(f"Category rank result: {result}")
    assert result['success'], "Category rank query failed"
    assert len(result['result']) > 0, "No shops returned"
    
    # Verify shop data structure
    shop = result['result'][0]
    assert 'shop_id' in shop, "Missing shop_id"
    assert 'name' in shop, "Missing name"
    assert 'rating' in shop, "Missing rating"
    #assert 'reviews' in shop, "Missing reviews"
    assert 'address' in shop, "Missing address"

def test_category_rank_with_region():
    """Test category ranking with region filter"""
    result = dianping_category_rank('beijing', '日本菜', region='三里屯/工体')
    print(f"Category rank result: {result}")
    assert result['success'], "Category rank query failed"
    assert len(result['result']) > 0, "No shops returned"
    
    # Verify location filtering
    for shop in result['result']:
        assert '朝阳' in shop['address'] or '三里屯' in shop['address'], \
            f"Shop not in expected region: {shop['address']}"

def test_category_rank_with_sort():
    """Test category ranking with different sort options"""
    # Test rating-based sorting
    result = dianping_category_rank('beijing', '西餐', sort='o3')
    print(f"Category rank result: {result}")
    assert result['success'], "Category rank query failed"
    assert len(result['result']) > 0, "No shops returned"
    
    # Verify shop data structure
    shop = result['result'][0]
    assert 'shop_id' in shop, "Missing shop_id"
    assert 'name' in shop, "Missing name"
    assert 'rating' in shop, "Missing rating"
    #assert 'reviews' in shop, "Missing reviews"
    assert 'address' in shop, "Missing address"

if __name__ == "__main__":
    pytest.main(['-v', __file__])