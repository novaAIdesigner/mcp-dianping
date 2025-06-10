from mcp.server.fastmcp import FastMCP
from playwright.sync_api import sync_playwright  # Changed to sync API
from pathlib import Path
import os
import logging
from typing import Annotated, Literal
from pydantic import Field

mcp = FastMCP("DianpingMCP")

# Global instances
_browser = None
_context = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_browser():
    """Get or create a browser instance with anti-automation features disabled"""
    global _browser
    
    if _browser is None:
        logger.info("Creating new browser instance...")
        p = sync_playwright().start()
        _browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        logger.info("Browser instance created successfully")
    else:
        logger.debug("Using existing browser instance")
        
    return _browser
# 加载分类菜单（dianping-menu.txt），返回dict: {分类名: url}
def load_menu(filepath="dianping-menu.txt"):
    menu = {}
    
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//") or line.startswith("#"):
                continue
                
            parts = line.split("\t")
            if len(parts) == 2:
                name, url = parts
                menu[name] = url
    return menu

def load_regions(filepath="dianping-region.txt"):
    """
    Load region information from file, organized by city
    Returns: dict {city: {region_name: region_code}}
    Format example:
    beijing 国贸/建外 r2578
    beijing 三里屯/工体 r2580
    """
    regions = {}
    current_city = None
    
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines, comments and headers
            if not line or line.startswith("#") or line.startswith("//"):
                continue
                
            # Parse region line
            parts = line.split()
            if len(parts) == 3:
                city, name, code = parts
                city = city.lower()
                if city not in regions:
                    regions[city] = {}
                regions[city][name] = code
    
    return regions

MENU = load_menu()
REGIONS = load_regions()

def get_context():
    """Get authenticated context from auth.json or return None if login required"""
    auth_file = Path("auth.json")
    if not auth_file.exists():
        logger.error("Auth file not found")
        return None
        
    try:
        browser = get_browser()
        context = browser.new_context(storage_state=str(auth_file))
        
        # Create test page with anti-detection headers
        page = context.new_page()
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        return context
            
    except Exception as e:
        logger.error(f"Error loading auth context: {e}")
        return None

def get_page(url: str = 'https://www.dianping.com/beijing'):
    """Get an authenticated page with anti-detection settings
    
    Args:
        url: Page URL to load (default: Beijing homepage)
        
    Returns:
        tuple: (context, page) if authenticated, (None, None) if login required
    """
    auth_file = Path("auth.json")
    if not auth_file.exists():
        logger.error("Auth file not found")
        return None, None
        
    try:
        browser = get_browser()
        context = browser.new_context(storage_state=str(auth_file))
        page = context.new_page()
        
        logger.info(f"Navigating to: {url}")
        page.goto(url, wait_until='domcontentloaded')
                    
        try:
            username_element = page.wait_for_selector('.userinfo-container .username', state='visible', timeout=10000)
            username = username_element.text_content()
            username = username.strip()
            
            if not username:
                raise Exception("Username is empty")
            logger.info(f"Login verified for user: {username}")
            return context, page
        except Exception as e:
            logger.error(f"Login verification failed: {e}")
            page.close()
            return None, None
            
    except Exception as e:
        logger.error(f"Page creation failed: {e}")
        return None, None

def star_class_to_rating(star_classes: str) -> str:
    """Convert star class string to numeric rating
    
    Args:
        star_classes: Class string like 'star star_40 star_sml'
        
    Returns:
        String rating like '4.0' or '4.5'
    """
    if not star_classes:
        return "0"
    try:
        # Find the class that starts with 'star_' and contains numbers
        classes = star_classes.split()
        rating_class = next((c for c in classes if c.startswith('star_') and c[5:].isdigit()), None)
        if rating_class:
            num = int(rating_class.replace('star_', ''))
            rating = num / 10
            return str(rating)
        return "0"
    except:
        return "0"

@mcp.tool()
def dianping_category_rank(
    city: Annotated[str, Field(
        description="城市拼音，如 'beijing', 'shanghai'"
    )],
    category: Annotated[Literal[
        # 美食类
        '美食', '火锅', '面包甜点', '本帮江浙菜', '日本菜', '咖啡厅', '自助餐', 
        '小吃快餐', '西餐', '韩国料理', '粤菜', '烧烤', '东南亚菜', '川菜', 
        '素菜', '东北菜', '湘菜', '云南菜', '新疆菜', '海鲜', '西北菜', 
        '蟹宴', '台湾菜', '贵州菜', '面馆', '小龙虾', '江西菜', '家常菜', '其他',
        # 周边游
        '周边游', '自然景观', '人文古迹', '景区设施', '水上项目', '展览馆', 
        '动植物园', '滑雪景区', '休闲园区', '公园', '公园售票处', '地标建筑', 
        '主题乐园', '动物园', '温泉景区', '人文街区', '植物园', '纪念地', 
        '度假景区', '影视基地', 
        # 展览场馆
        '博物馆', '美术馆', '纪念馆', '科技馆', '名人故居', '陈列馆', 
        '天文馆', '蜡像馆', '宗教景区', '古村古镇',
        # 休闲娱乐
        '休闲娱乐', '足疗', 'KTV', '足疗按摩', '洗浴/汗蒸', '酒吧', '密室逃脱',
        '轰趴馆', '茶馆', '私人影院', '网吧网咖', 'DIY手工坊', '采摘/农家乐',
        '文化艺术', '游乐游艺', 'VR', '桌游', '团建拓展', '棋牌室', '桌球馆',
        # 电影演出
        '电影院', '演出场馆', '剧场/影院', '音乐厅/礼堂', '艺术中心/文化广场',
        '热门演出', '赛事展览', '其他电影演出赛事',
        # 酒店住宿
        '酒店', '五星/豪华', '经济连锁', '四星级/高档型', '三星级/舒适型',
        '情侣酒店', '青年旅社', '客栈',
        # 其他服务
        '亲子', '运动健身', '购物', '家装', '学习培训', 
        '生活服务', '医疗健康', '爱车', '宠物'
    ], Field(
        description="分类榜单包括餐饮美食，游玩，休闲，酒店等"
    )],
    region: Annotated[str, Field(
        description="商圈或地点名称，如'三里屯'、'国贸'等"
    )] = "",
    sort: Annotated[Literal[
        "智能排序", "好评优先", "人气优先", "口味优先", "评价最多",
        "环境最佳", "服务最佳", "预订优先", "人均最高", "人均最低"
    ], Field(
        description="排序方式"
    )] = "智能排序"
) -> dict:
    """获取大众点评商户排行榜"""
    # Validate inputs and build URL
    # 验证输入
    if category not in MENU:
        return {"success": False, "error": f"分类'{category}'不在榜单中"}
    
    if city.lower() not in REGIONS:
        return {"success": False, "error": f"城市'{city}'不在支持列表中"}

    # 获取分类代码
    category_code = MENU[category]
    
    # 排序参数映射
    sort_map = {
        "智能排序": "",
        "好评优先": "o3",
        "人气优先": "o2", 
        "口味优先": "o4",
        "评价最多": "o11",
        "环境最佳": "o5",
        "服务最佳": "o6",
        "预订优先": "o13",
        "人均最高": "o9",
        "人均最低": "o8"
    }

    # 构建基础URL
    base_url = f"https://www.dianping.com/{city.lower()}{category_code}"
    
    # 添加区域代码
    if region:
        if region not in REGIONS[city.lower()]:
            return {"success": False, "error": f"区域'{region}'在{city}中未找到"}
        base_url += REGIONS[city.lower()][region]
    
    # 添加排序参数
    base_url += sort_map[sort]

    # Get authenticated page
    context, page = get_page(base_url)
    if not context:
        return {"success": False, "error": "需要登录并上传auth.json"}
    
    try:
        page.wait_for_load_state('domcontentloaded')
        items = []
        for shop in page.query_selector_all('.shop-all-list ul li'):
            name = shop.query_selector('.tit a h4').inner_text() if shop.query_selector('.tit a h4') else ""
            href = shop.query_selector('.tit a').get_attribute('href') if shop.query_selector('.tit a') else ""
            shop_id = ""
            if href:
                parts = href.split("/")
                if "shop" in parts:
                    idx = parts.index("shop")
                    if idx + 1 < len(parts):
                        shop_id = parts[idx + 1]
            star = shop.query_selector('.nebula_star .star_icon span')
            rating = star_class_to_rating(star.get_attribute('class')) if star else ""
            review_count = shop.query_selector('.review-num b').inner_text() if shop.query_selector('.review-num b') else ""
            address = ""
            addr_tag = shop.query_selector('.tag-addr')
            if addr_tag:
                addr_spans = addr_tag.query_selector_all('a span.tag')
                address = " ".join([span.inner_text() for span in addr_spans]) if addr_spans else ""
            #img = shop.query_selector('.pic img')
            #img_url = img.get_attribute('src') if img else ""
            price = shop.query_selector('.mean-price b').inner_text() if shop.query_selector('.mean-price b') else ""
            recommend = []
            recommend_tag = shop.query_selector('.recommend')
            if recommend_tag:
                recommend_links = recommend_tag.query_selector_all('a.recommend-click')
                recommend = [a.inner_text() for a in recommend_links] if recommend_links else []
            items.append({
                "shop_id": shop_id,
                "name": name,
                "rating": rating,  # Now contains numeric rating like "4.5"
                "review_count": review_count,
                "address": address,
                "price": price,
                "recommend": recommend
            })
        return {"success": True, "city": city, "category": category, "region": region, "result": items}
    finally:
        page.close()

@mcp.tool()
async def dianping_shop_detail(shop_id: str) -> dict:
    """
    查询指定shop_id的店铺详情，返回:店铺名称、评分、地址、电话、简介、推荐、团购、评价。
    """
    context, page = await get_page(f"https://www.dianping.com/shop/{shop_id}")
    if not context:
        return {"success": False, "error": "需要登录并上传auth.json"}
    
    try:
        try:
            page.wait_for_selector('.shopName', timeout=10000)
        except Exception:
            await page.close()
            return {"success": False, "error": "页面加载失败"}

        # 店名
        name = page.query_selector('.shopName').inner_text() if page.query_selector('.shopName') else ""

        # 评分和评价数 
        rating = page.query_selector('.star-score').inner_text() if page.query_selector('.star-score') else ""
        review_count = page.query_selector('.reviews').inner_text() if page.query_selector('.reviews') else ""

        # 人均价格
        price = page.query_selector('.price').inner_text() if page.query_selector('.price') else ""

        # 地区和分类
        region = page.query_selector('.region').inner_text() if page.query_selector('.region') else ""
        category = page.query_selector('.category').inner_text() if page.query_selector('.category') else ""

        # 细分评分
        score_text = page.query_selector('.scoreText').inner_text() if page.query_selector('.scoreText') else ""

        # 地址 
        address = page.query_selector('.addressText').inner_text() if page.query_selector('.addressText') else ""
        address_desc = page.query_selector('.desc-addr-txt').inner_text() if page.query_selector('.desc-addr-txt') else ""

        # 营业时间和标签
        biz_info = ""
        biz_tag = page.query_selector('.biz-txt')
        biz_time = page.query_selector('.biz-time')
        if biz_tag and biz_time:
            biz_info = f"{biz_tag.inner_text()} {biz_time.inner_text()}"

        # 特色标签
        tags = []
        for tag in page.query_selector_all('.feature-txt'):
            tags.append(tag.inner_text())

        # 推荐菜
        recommend_dishes = []
        dishes = page.query_selector_all('.food')
        for dish in dishes:
            recommend_dishes.append(dish.inner_text())

        # 生成Markdown格式文本
        md = f"""# {name}

**评分**: {rating} ({review_count})  
**人均**: {price}  
**地区**: {region}  
**分类**: {category}  
**评分详情**: {score_text}

**地址**: {address}  
{address_desc}

**营业信息**: {biz_info}  
**特色**: {' '.join(tags)}

**推荐菜**:
{', '.join(recommend_dishes)}
"""

        return {
            "success": True, 
            "shop_id": shop_id,
            "name": name,
            "rating": rating,
            "review_count": review_count,
            "price": price,
            "address": address,
            "md": md
        }
    finally:
        await page.close()

def initialize_browser():
    """Initialize browser instance on server startup"""
    global _browser
    try:
        logger.info("Initializing browser on startup...")
        p = sync_playwright().start()
        _browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        logger.info("Browser initialization successful")
        return True
    except Exception as e:
        logger.error(f"Browser initialization failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting DianpingMCP server")
    
    # Initialize browser on startup
    if not initialize_browser():
        logger.error("Failed to initialize browser. Exiting...")
        exit(1)
        
    # Start MCP server
    mcp.run(transport="stdio")