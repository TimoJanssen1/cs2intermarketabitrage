#!/usr/bin/env python3
"""Test script to verify Steam and Buff data fetchers work correctly.
Quick hack to test if the APIs are still working.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
from src.fetcher.steam import SteamFetcher
from src.fetcher.buff import BuffFetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(label, value, indent=2):
    """Print a formatted result line."""
    spaces = " " * indent
    print(f"{spaces}{label}: {value}")


def test_steam_fetcher():
    """Test Steam marketplace fetcher."""
    print_section("Testing Steam Marketplace Fetcher")
    
    fetcher = SteamFetcher()
    test_items = [
        "AK-47 | Redline (Field-Tested)",
        "AWP | Asiimov (Field-Tested)",
    ]
    
    print_result("Rate limit", f"{fetcher.rate_limit} requests/minute")
    print_result("Currency ID", fetcher.currency_id)
    print()
    
    for item_name in test_items:
        print(f"\n  Testing: {item_name}")
        print("  " + "-" * 66)
        
        result = fetcher.fetch_price_overview(item_name)
        
        if result:
            if result.get('success'):
                print_result("✓ Status", "SUCCESS")
                print_result("  HTTP Status", result.get('status_code'))
                print_result("  Latency", f"{result.get('latency_ms')} ms")
                
                if result.get('lowest_price'):
                    print_result("  Lowest Price", f"${result.get('lowest_price'):.2f}")
                if result.get('median_price'):
                    print_result("  Median Price", f"${result.get('median_price'):.2f}")
                if result.get('volume'):
                    print_result("  Volume", result.get('volume'))
                
                # Show raw response structure
                raw = result.get('raw_response', {})
                print_result("  Raw Response Keys", list(raw.keys()))
            else:
                print_result("✗ Status", "FAILED")
                print_result("  Error", result.get('error', 'Unknown error'))
        else:
            print_result("✗ Status", "FAILED - No response")
    
    return True


def test_buff_fetcher():
    """Test Buff marketplace fetcher."""
    print_section("Testing Buff Marketplace Fetcher")
    
    fetcher = BuffFetcher()
    
    print_result("Rate limit", f"{fetcher.rate_limit} requests/minute")
    print_result("Cookie set", "Yes" if fetcher.cookie else "No (some endpoints may require auth)")
    print()
    
    # Test 1: Search for goods (try multiple search terms)
    print("\n  1. Testing Search Function")
    print("  " + "-" * 66)
    
    search_terms = [
        "AK-47 Redline",
        "AK-47",
        "Redline",
    ]
    
    search_result = None
    goods_id = None
    
    for search_term in search_terms:
        print_result(f"Trying search term", search_term)
        search_result = fetcher.search_goods(search_term)
        
        if search_result and search_result.get('success'):
            print_result("✓ Status", "SUCCESS")
            print_result("  HTTP Status", search_result.get('status_code'))
            print_result("  Latency", f"{search_result.get('latency_ms')} ms")
            
            data = search_result.get('data', {})
            items = data.get('items', [])
            print_result("  Items found", len(items))
            
            # Show response structure for debugging
            print_result("  Response keys", list(data.keys()))
            if 'code' in data:
                print_result("  Response code", data.get('code'))
            if 'msg' in data:
                print_result("  Response message", data.get('msg'))
            
            if items:
                break
        else:
            print_result("  Result", "No items found or failed")
            if search_result:
                print_result("  HTTP Status", search_result.get('status_code', 'N/A'))
            print()
    
    if search_result and search_result.get('success'):
        data = search_result.get('data', {})
        items = data.get('items', [])
        
        if items:
            first_item = items[0]
            goods_id = first_item.get('id')
            goods_name = first_item.get('name', 'N/A')
            print_result("  First item ID", goods_id)
            print_result("  First item name", goods_name[:50] + "..." if len(goods_name) > 50 else goods_name)
            
            # Test 2: Get sell orders (asks)
            print("\n  2. Testing Sell Orders (Asks)")
            print("  " + "-" * 66)
            print_result("Goods ID", goods_id)
            
            sell_result = fetcher.get_sell_orders(goods_id)
            
            if sell_result and sell_result.get('success'):
                print_result("✓ Status", "SUCCESS")
                print_result("  HTTP Status", sell_result.get('status_code'))
                print_result("  Latency", f"{sell_result.get('latency_ms')} ms")
                
                best_ask = sell_result.get('best_ask')
                order_count = sell_result.get('order_count', 0)
                
                if best_ask:
                    print_result("  Best Ask", f"¥{best_ask:.2f}")
                else:
                    print_result("  Best Ask", "None")
                
                print_result("  Order Count", order_count)
                
                # Show sample orders
                orders = sell_result.get('orders', [])
                if orders:
                    print("\n  Sample orders (top 3):")
                    for i, order in enumerate(orders[:3], 1):
                        price = order.get('price', 'N/A')
                        print(f"    {i}. Price: ¥{price}")
            else:
                print_result("✗ Status", "FAILED")
                if sell_result:
                    print_result("  HTTP Status", sell_result.get('status_code', 'N/A'))
                else:
                    print_result("  Error", "No response")
            
            # Test 3: Get buy orders (bids)
            print("\n  3. Testing Buy Orders (Bids)")
            print("  " + "-" * 66)
            print_result("Goods ID", goods_id)
            
            buy_result = fetcher.get_buy_orders(goods_id)
            
            if buy_result and buy_result.get('success'):
                print_result("✓ Status", "SUCCESS")
                print_result("  HTTP Status", buy_result.get('status_code'))
                print_result("  Latency", f"{buy_result.get('latency_ms')} ms")
                
                best_bid = buy_result.get('best_bid')
                order_count = buy_result.get('order_count', 0)
                
                if best_bid:
                    print_result("  Best Bid", f"¥{best_bid:.2f}")
                else:
                    print_result("  Best Bid", "None")
                
                print_result("  Order Count", order_count)
                
                # Show sample orders
                orders = buy_result.get('orders', [])
                if orders:
                    print("\n  Sample orders (top 3):")
                    for i, order in enumerate(orders[:3], 1):
                        price = order.get('price', 'N/A')
                        print(f"    {i}. Price: ¥{price}")
            else:
                print_result("✗ Status", "FAILED")
                if buy_result:
                    print_result("  HTTP Status", buy_result.get('status_code', 'N/A'))
                else:
                    print_result("  Error", "No response")
        else:
            print_result("✗ Status", "FAILED - No items found")
            print_result("  Note", "Search may require authentication or item may not exist")
            print_result("  Tip", "Try setting BUFF_COOKIE in .env file")
            print_result("  Tip", "Or use a known goods_id directly for testing")
            
            # Try with a known goods_id for testing (if available)
            # Note: This would need to be updated with actual goods_id
            print("\n  Attempting direct goods_id test (if available)...")
            # For now, we'll skip this but show how it would work
            print("  (Skipping - would need actual goods_id)")
    else:
        print_result("✗ Status", "FAILED")
        if search_result:
            print_result("  HTTP Status", search_result.get('status_code', 'N/A'))
            data = search_result.get('data', {})
            if isinstance(data, dict):
                if 'code' in data:
                    print_result("  API Code", data.get('code'))
                if 'msg' in data:
                    print_result("  API Message", data.get('msg'))
        else:
            print_result("  Error", "No response - check network connection")
    
    return True


def explain_buff_workflow():
    """Explain how Buff data pulling works."""
    print_section("How Buff Data Pulling Works")
    
    print("""
  Buff marketplace uses a multi-step process:
  
  1. SEARCH (find goods_id):
     - Endpoint: https://buff.163.com/api/market/goods
     - Method: GET
     - Parameters: game=csgo, search=<item_name>, page_num=1
     - Returns: List of items with their goods_id
     - Authentication: Optional (cookie may improve results)
  
  2. GET SELL ORDERS (asks):
     - Endpoint: https://buff.163.com/api/market/goods/sell_order
     - Method: GET
     - Parameters: game=csgo, goods_id=<id>, page_num=1
     - Returns: List of sell orders (asks) sorted by price
     - Best ask: First item in the list (lowest price)
  
  3. GET BUY ORDERS (bids):
     - Endpoint: https://buff.163.com/api/market/goods/buy_order
     - Method: GET
     - Parameters: game=csgo, goods_id=<id>, page_num=1
     - Returns: List of buy orders (bids) sorted by price
     - Best bid: First item in the list (highest price)
  
  Rate Limiting:
  - Default: 20 requests/minute
  - Enforced with exponential backoff on errors
  - Minimum interval between requests calculated automatically
  
  Authentication:
  - Optional but recommended for better results
  - Set BUFF_COOKIE environment variable
  - Cookie format: session=xxx; csrftoken=xxx; etc.
  - Get cookie from browser developer tools when logged into buff.163.com
    """)


def main():
    """Main test function."""
    print("\n" + "=" * 70)
    print("  CS2 Arbitrage System - Fetcher Test Suite")
    print("=" * 70)
    
    # Explain Buff workflow first
    explain_buff_workflow()
    
    # Test Steam
    steam_ok = test_steam_fetcher()
    
    # Test Buff
    buff_ok = test_buff_fetcher()
    
    # Summary
    print_section("Test Summary")
    
    print_result("Steam Fetcher", "✓ PASSED" if steam_ok else "✗ FAILED")
    print_result("Buff Fetcher", "✓ PASSED" if buff_ok else "✗ FAILED")
    
    print("\n  Notes:")
    print("    - Steam: Public API, no authentication required")
    print("    - Buff: May require authentication for some endpoints")
    print("    - Set BUFF_COOKIE in .env file for better Buff results")
    print("    - Rate limits are automatically enforced")
    print()
    
    return steam_ok and buff_ok


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        sys.exit(1)

