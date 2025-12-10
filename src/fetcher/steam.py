"""Steam marketplace data fetcher."""

import requests
import time
import logging
from typing import Optional, Dict, Any
from urllib.parse import quote
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class SteamFetcher:
    """Fetches price data from Steam Community Market."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize Steam fetcher.
        
        Args:
            config_path: Path to config file
        """
        self.config = self._load_config(config_path)
        self.rate_limit = self.config.get('rate_limits', {}).get('steam', {}).get('requests_per_minute', 10)
        self.backoff_base = self.config.get('rate_limits', {}).get('steam', {}).get('backoff_base', 2.0)
        self.max_retries = self.config.get('rate_limits', {}).get('steam', {}).get('max_retries', 3)
        self.currency_id = self.config.get('currency', {}).get('steam_currency_id', 3)
        
        self.last_request_time = 0
        self.request_count = 0
        self.request_window_start = time.time()
        
        # Headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    
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
    
    def fetch_price_overview(
        self,
        market_hash_name: str,
        app_id: int = 730,
        currency_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch price overview for an item.
        
        Args:
            market_hash_name: Steam market hash name (URL encoded)
            app_id: Steam app ID (730 for CS2)
            currency_id: Currency ID (defaults to config value)
            
        Returns:
            Dictionary with price data or None on error
        """
        if currency_id is None:
            currency_id = self.currency_id
        
        # URL encode the market hash name
        encoded_name = quote(market_hash_name)
        
        url = (
            f"https://steamcommunity.com/market/priceoverview/"
            f"?appid={app_id}&currency={currency_id}&market_hash_name={encoded_name}"
        )
        
        # Rate limiting
        self._rate_limit()
        
        # Retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                response = requests.get(url, headers=self.headers, timeout=10)
                latency_ms = int((time.time() - start_time) * 1000)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Parse Steam response
                    result = {
                        'success': data.get('success', False),
                        'lowest_price': self._parse_price(data.get('lowest_price')),
                        'volume': data.get('volume', '0').replace(',', ''),
                        'median_price': self._parse_price(data.get('median_price')),
                        'raw_response': data,
                        'status_code': response.status_code,
                        'latency_ms': latency_ms
                    }
                    
                    # Extract best bid/ask from lowest_price (Steam shows lowest ask)
                    result['best_ask'] = result['lowest_price']
                    # Steam doesn't provide bid data in this endpoint, set to None
                    result['best_bid'] = None
                    
                    return result
                else:
                    logger.warning(f"Steam API returned status {response.status_code} for {market_hash_name}")
                    if attempt < self.max_retries - 1:
                        sleep_time = self.backoff_base ** attempt
                        time.sleep(sleep_time)
                    else:
                        return {
                            'success': False,
                            'error': f"HTTP {response.status_code}",
                            'status_code': response.status_code,
                            'latency_ms': latency_ms
                        }
            
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching Steam data for {market_hash_name}: {e}")
                if attempt < self.max_retries - 1:
                    sleep_time = self.backoff_base ** attempt
                    time.sleep(sleep_time)
                else:
                    return {
                        'success': False,
                        'error': str(e),
                        'status_code': None,
                        'latency_ms': None
                    }
        
        return None
    
    def _parse_price(self, price_str: Optional[str]) -> Optional[float]:
        """Parse price string to float.
        
        Examples: "$12.34" -> 12.34, "€10.50" -> 10.50
        """
        if not price_str:
            return None
        
        # Remove currency symbols and whitespace
        # This probably doesn't handle all edge cases but works for most
        cleaned = price_str.replace('$', '').replace('€', '').replace('£', '')
        cleaned = cleaned.replace(',', '').strip()
        
        try:
            return float(cleaned)
        except ValueError:
            logger.warning(f"Could not parse price: {price_str}")
            return None


if __name__ == "__main__":
    # Test fetcher
    logging.basicConfig(level=logging.INFO)
    fetcher = SteamFetcher()
    
    # Test with a common CS2 item
    result = fetcher.fetch_price_overview("AK-47 | Redline (Field-Tested)")
    print(result)

