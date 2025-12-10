"""Buff marketplace data fetcher."""

import requests
import time
import logging
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class BuffFetcher:
    """Fetches price data from Buff marketplace."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize Buff fetcher.
        
        Args:
            config_path: Path to config file
        """
        self.config = self._load_config(config_path)
        self.rate_limit = self.config.get('rate_limits', {}).get('buff', {}).get('requests_per_minute', 20)
        self.backoff_base = self.config.get('rate_limits', {}).get('buff', {}).get('backoff_base', 2.0)
        self.max_retries = self.config.get('rate_limits', {}).get('buff', {}).get('max_retries', 3)
        
        self.last_request_time = 0
        self.request_count = 0
        self.request_window_start = time.time()
        
        # Get cookie from environment variable
        # TODO: should probably handle cookie expiration better
        self.cookie = os.getenv('BUFF_COOKIE', '')
        if not self.cookie:
            logger.warning("BUFF_COOKIE not set in environment. Some endpoints may require authentication.")
        
        # Headers (Buff requires specific headers)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Referer': 'https://buff.163.com/market/?game=csgo',
            'X-Requested-With': 'XMLHttpRequest',
        }
        
        if self.cookie:
            self.headers['Cookie'] = self.cookie
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return {}
    
    def _rate_limit(self):
        """Enforce rate limiting."""
        current_time = time.time()
        
        # Reset counter if window expired
        if current_time - self.request_window_start >= 60:
            self.request_count = 0
            self.request_window_start = current_time
        
        # Check if we need to wait
        if self.request_count >= self.rate_limit:
            sleep_time = 60 - (current_time - self.request_window_start)
            if sleep_time > 0:
                logger.debug(f"Rate limit reached, sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
                self.request_count = 0
                self.request_window_start = time.time()
        
        # Enforce minimum time between requests
        time_since_last = current_time - self.last_request_time
        min_interval = 60.0 / self.rate_limit
        if time_since_last < min_interval:
            time.sleep(min_interval - time_since_last)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def search_goods(self, search_term: str, game: str = 'csgo') -> Optional[Dict[str, Any]]:
        """Search for goods by name.
        
        Args:
            search_term: Item name to search for
            game: Game identifier ('csgo' for CS2)
            
        Returns:
            Dictionary with search results or None on error
        """
        url = "https://buff.163.com/api/market/goods"
        params = {
            'game': game,
            'search': search_term,
            'page_num': 1,
            'sort_by': 'sell_num.desc'
        }
        
        self._rate_limit()
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                latency_ms = int((time.time() - start_time) * 1000)
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'success': True,
                        'data': data,
                        'status_code': response.status_code,
                        'latency_ms': latency_ms
                    }
                else:
                    logger.warning(f"Buff search API returned status {response.status_code}")
                    if attempt < self.max_retries - 1:
                        sleep_time = self.backoff_base ** attempt
                        time.sleep(sleep_time)
            
            except requests.exceptions.RequestException as e:
                logger.error(f"Error searching Buff for {search_term}: {e}")
                if attempt < self.max_retries - 1:
                    sleep_time = self.backoff_base ** attempt
                    time.sleep(sleep_time)
        
        return None
    
    def get_sell_orders(self, goods_id: int, game: str = 'csgo', page_num: int = 1) -> Optional[Dict[str, Any]]:
        """Get sell orders (asks) for a goods ID.
        
        Args:
            goods_id: Buff goods ID
            game: Game identifier ('csgo' for CS2)
            page_num: Page number
            
        Returns:
            Dictionary with sell order data or None on error
        """
        url = "https://buff.163.com/api/market/goods/sell_order"
        params = {
            'game': game,
            'goods_id': goods_id,
            'page_num': page_num,
            'sort_by': 'default'
        }
        
        self._rate_limit()
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                latency_ms = int((time.time() - start_time) * 1000)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Parse sell orders
                    orders = data.get('data', {}).get('items', [])
                    if orders:
                        best_ask = float(orders[0].get('price', 0))
                        order_count = len(orders)
                    else:
                        best_ask = None
                        order_count = 0
                    
                    return {
                        'success': True,
                        'best_ask': best_ask,
                        'order_count': order_count,
                        'orders': orders,
                        'raw_response': data,
                        'status_code': response.status_code,
                        'latency_ms': latency_ms
                    }
                else:
                    logger.warning(f"Buff sell orders API returned status {response.status_code} for goods_id {goods_id}")
                    if attempt < self.max_retries - 1:
                        sleep_time = self.backoff_base ** attempt
                        time.sleep(sleep_time)
            
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching Buff sell orders for goods_id {goods_id}: {e}")
                if attempt < self.max_retries - 1:
                    sleep_time = self.backoff_base ** attempt
                    time.sleep(sleep_time)
        
        return None
    
    def get_buy_orders(self, goods_id: int, game: str = 'csgo', page_num: int = 1) -> Optional[Dict[str, Any]]:
        """Get buy orders (bids) for a goods ID.
        
        Args:
            goods_id: Buff goods ID
            game: Game identifier ('csgo' for CS2)
            page_num: Page number
            
        Returns:
            Dictionary with buy order data or None on error
        """
        url = "https://buff.163.com/api/market/goods/buy_order"
        params = {
            'game': game,
            'goods_id': goods_id,
            'page_num': page_num
        }
        
        self._rate_limit()
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                latency_ms = int((time.time() - start_time) * 1000)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Parse buy orders
                    orders = data.get('data', {}).get('items', [])
                    if orders:
                        best_bid = float(orders[0].get('price', 0))
                        order_count = len(orders)
                    else:
                        best_bid = None
                        order_count = 0
                    
                    return {
                        'success': True,
                        'best_bid': best_bid,
                        'order_count': order_count,
                        'orders': orders,
                        'raw_response': data,
                        'status_code': response.status_code,
                        'latency_ms': latency_ms
                    }
                else:
                    logger.warning(f"Buff buy orders API returned status {response.status_code} for goods_id {goods_id}")
                    if attempt < self.max_retries - 1:
                        sleep_time = self.backoff_base ** attempt
                        time.sleep(sleep_time)
            
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching Buff buy orders for goods_id {goods_id}: {e}")
                if attempt < self.max_retries - 1:
                    sleep_time = self.backoff_base ** attempt
                    time.sleep(sleep_time)
        
        return None


if __name__ == "__main__":
    # Test fetcher
    logging.basicConfig(level=logging.INFO)
    fetcher = BuffFetcher()
    
    # Test search
    result = fetcher.search_goods("AK-47 Redline")
    if result and result.get('success'):
        print(f"Search results: {len(result.get('data', {}).get('items', []))} items found")
        if result.get('data', {}).get('items'):
            goods_id = result['data']['items'][0].get('id')
            print(f"First item goods_id: {goods_id}")
            
            # Test sell orders
            sell_result = fetcher.get_sell_orders(goods_id)
            print(f"Sell orders: {sell_result}")

