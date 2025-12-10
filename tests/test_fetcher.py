"""Tests for data fetchers."""

import pytest
from unittest.mock import Mock, patch
from src.fetcher.steam import SteamFetcher
from src.fetcher.buff import BuffFetcher


class TestSteamFetcher:
    """Test cases for SteamFetcher."""
    
    def test_parse_price(self):
        """Test price parsing."""
        fetcher = SteamFetcher()
        
        # Test USD price
        assert fetcher._parse_price("$12.34") == 12.34
        
        # Test EUR price
        assert fetcher._parse_price("€10.50") == 10.50
        
        # Test with comma
        assert fetcher._parse_price("$1,234.56") == 1234.56
        
        # Test None
        assert fetcher._parse_price(None) is None
        
        # Test invalid
        assert fetcher._parse_price("invalid") is None
    
    @patch('src.fetcher.steam.requests.get')
    def test_fetch_price_overview_success(self, mock_get):
        """Test successful price fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'lowest_price': '$10.50',
            'volume': '1,234',
            'median_price': '$11.00'
        }
        mock_get.return_value = mock_response
        
        fetcher = SteamFetcher()
        result = fetcher.fetch_price_overview("AK-47 | Redline (Field-Tested)")
        
        assert result is not None
        assert result['success'] is True
        assert result['lowest_price'] == 10.50
        assert result['median_price'] == 11.00


class TestBuffFetcher:
    """Test cases for BuffFetcher."""
    
    @patch('src.fetcher.buff.requests.get')
    def test_get_sell_orders_success(self, mock_get):
        """Test successful sell orders fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'items': [
                    {'price': '8.50'},
                    {'price': '8.60'}
                ]
            }
        }
        mock_get.return_value = mock_response
        
        fetcher = BuffFetcher()
        result = fetcher.get_sell_orders(12345)
        
        assert result is not None
        assert result['success'] is True
        assert result['best_ask'] == 8.50
        assert result['order_count'] == 2
    
    @patch('src.fetcher.buff.requests.get')
    def test_get_buy_orders_success(self, mock_get):
        """Test successful buy orders fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'items': [
                    {'price': '7.50'},
                    {'price': '7.40'}
                ]
            }
        }
        mock_get.return_value = mock_response
        
        fetcher = BuffFetcher()
        result = fetcher.get_buy_orders(12345)
        
        assert result is not None
        assert result['success'] is True
        assert result['best_bid'] == 7.50
        assert result['order_count'] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

