#!/usr/bin/env python3
"""Continuous data puller daemon."""

import argparse
import logging
import time
import sys
from typing import List, Optional
import yaml
from src.db.client import DatabaseClient
from src.fetcher.steam import SteamFetcher
from src.fetcher.buff import BuffFetcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/puller.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PullerDaemon:
    """Continuous data puller for Steam and Buff marketplaces."""
    
    def __init__(
        self,
        config_path: str = "config.yaml",
        db_path: str = "db/arbitrage.sqlite",
        interval_seconds: int = 300
    ):
        """Initialize puller daemon.
        
        Args:
            config_path: Path to config file
            db_path: Path to database file
            interval_seconds: Interval between fetches in seconds
        """
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.db_path = db_path
        self.interval_seconds = interval_seconds
        
        # Initialize components
        self.db_client = DatabaseClient(db_path)
        self.steam_fetcher = SteamFetcher(config_path)
        self.buff_fetcher = BuffFetcher(config_path)
        
        # Items to track (empty = all items in DB)
        self.items_to_track = self.config.get('puller', {}).get('items_to_track', [])
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return {}
    
    def get_items_to_fetch(self) -> List[dict]:
        """Get list of items to fetch data for.
        
        Returns:
            List of item dictionaries with item_id and market_hash_name
        """
        conn = self.db_client.get_connection()
        cursor = conn.cursor()
        
        if self.items_to_track:
            # Fetch specific items
            placeholders = ','.join('?' * len(self.items_to_track))
            cursor.execute(f"""
                SELECT item_id, market_hash_name, buff_goods_id
                FROM items
                WHERE item_id IN ({placeholders})
            """, self.items_to_track)
        else:
            # Fetch all items
            cursor.execute("""
                SELECT item_id, market_hash_name, buff_goods_id
                FROM items
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def fetch_steam_data(self, item: dict) -> bool:
        """Fetch Steam data for an item.
        
        Args:
            item: Item dictionary with item_id and market_hash_name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.steam_fetcher.fetch_price_overview(
                item['market_hash_name']
            )
            
            if result and result.get('success'):
                # Insert snapshot
                self.db_client.insert_steam_snapshot(
                    item_id=item['item_id'],
                    best_bid=result.get('best_bid'),
                    best_ask=result.get('best_ask'),
                    median_price=result.get('median_price'),
                    lowest_price=result.get('lowest_price'),
                    highest_price=result.get('highest_price'),
                    raw_response=result.get('raw_response')
                )
                
                # Log fetch
                self.db_client.log_fetch(
                    source='steam',
                    endpoint='priceoverview',
                    status_code=result.get('status_code'),
                    latency_ms=result.get('latency_ms'),
                    success=True,
                    item_id=item['item_id']
                )
                
                return True
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'No response'
                logger.warning(f"Failed to fetch Steam data for {item['market_hash_name']}: {error_msg}")
                
                self.db_client.log_fetch(
                    source='steam',
                    endpoint='priceoverview',
                    status_code=result.get('status_code') if result else None,
                    latency_ms=result.get('latency_ms') if result else None,
                    success=False,
                    error_message=error_msg,
                    item_id=item['item_id']
                )
                
                return False
        
        except Exception as e:
            logger.error(f"Error fetching Steam data for {item['market_hash_name']}: {e}")
            self.db_client.log_fetch(
                source='steam',
                endpoint='priceoverview',
                success=False,
                error_message=str(e),
                item_id=item['item_id']
            )
            return False
    
    def fetch_buff_data(self, item: dict) -> bool:
        """Fetch Buff data for an item.
        
        Args:
            item: Item dictionary with item_id, market_hash_name, and buff_goods_id
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Need buff_goods_id to fetch orders
            # This is a bit hacky - search might fail if auth is bad
            if not item.get('buff_goods_id'):
                # Try to search for it
                search_result = self.buff_fetcher.search_goods(item['market_hash_name'])
                if search_result and search_result.get('success'):
                    items = search_result.get('data', {}).get('items', [])
                    if items:
                        goods_id = items[0].get('id')
                        # Update item in DB
                        conn = self.db_client.get_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE items 
                            SET buff_goods_id = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE item_id = ?
                        """, (goods_id, item['item_id']))
                        conn.commit()
                        conn.close()
                        item['buff_goods_id'] = goods_id
                    else:
                        logger.warning(f"No Buff goods found for {item['market_hash_name']}")
                        return False
                else:
                    logger.warning(f"Failed to search Buff for {item['market_hash_name']}")
                    return False
            
            # Fetch sell orders (asks)
            sell_result = self.buff_fetcher.get_sell_orders(item['buff_goods_id'])
            
            if sell_result and sell_result.get('success'):
                best_ask = sell_result.get('best_ask')
                order_count = sell_result.get('order_count', 0)
                
                # Insert snapshot
                self.db_client.insert_buff_snapshot(
                    item_id=item['item_id'],
                    best_ask=best_ask,
                    sell_order_count=order_count,
                    raw_response=sell_result.get('raw_response')
                )
                
                # Log fetch
                self.db_client.log_fetch(
                    source='buff',
                    endpoint='sell_order',
                    status_code=sell_result.get('status_code'),
                    latency_ms=sell_result.get('latency_ms'),
                    success=True,
                    item_id=item['item_id']
                )
                
                return True
            else:
                error_msg = 'Failed to fetch sell orders'
                logger.warning(f"Failed to fetch Buff data for {item['market_hash_name']}: {error_msg}")
                
                self.db_client.log_fetch(
                    source='buff',
                    endpoint='sell_order',
                    status_code=sell_result.get('status_code') if sell_result else None,
                    latency_ms=sell_result.get('latency_ms') if sell_result else None,
                    success=False,
                    error_message=error_msg,
                    item_id=item['item_id']
                )
                
                return False
        
        except Exception as e:
            logger.error(f"Error fetching Buff data for {item['market_hash_name']}: {e}")
            self.db_client.log_fetch(
                source='buff',
                endpoint='sell_order',
                success=False,
                error_message=str(e),
                item_id=item['item_id']
            )
            return False
    
    def run_once(self):
        """Run one fetch cycle."""
        items = self.get_items_to_fetch()
        
        if not items:
            logger.warning("No items to fetch. Add items to database first.")
            return
        
        logger.info(f"Fetching data for {len(items)} items...")
        
        steam_success = 0
        buff_success = 0
        
        for item in items:
            # Fetch Steam data
            if self.fetch_steam_data(item):
                steam_success += 1
            
            # Small delay between items
            time.sleep(1)
            
            # Fetch Buff data
            if self.fetch_buff_data(item):
                buff_success += 1
            
            # Small delay between items
            time.sleep(1)
        
        logger.info(
            f"Fetch cycle complete: Steam {steam_success}/{len(items)}, "
            f"Buff {buff_success}/{len(items)}"
        )
    
    def run(self):
        """Run continuous puller loop."""
        logger.info(f"Starting puller daemon (interval: {self.interval_seconds}s)")
        
        try:
            while True:
                self.run_once()
                logger.info(f"Sleeping for {self.interval_seconds} seconds...")
                time.sleep(self.interval_seconds)
        
        except KeyboardInterrupt:
            logger.info("Puller daemon stopped by user")
        except Exception as e:
            logger.error(f"Puller daemon error: {e}", exc_info=True)
            raise


def main():
    """Main entry point for puller daemon."""
    parser = argparse.ArgumentParser(
        description='Continuous data puller for CS2 arbitrage system'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=None,
        help='Interval between fetches in seconds (default: from config)'
    )
    parser.add_argument(
        '--db_path',
        type=str,
        default='db/arbitrage.sqlite',
        help='Path to database file'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to config file'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once instead of continuously'
    )
    
    args = parser.parse_args()
    
    # Load config to get default interval
    try:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
        default_interval = config.get('puller', {}).get('interval_seconds', 300)
    except:
        default_interval = 300
    
    interval = args.interval if args.interval is not None else default_interval
    
    # Ensure logs directory exists
    import os
    os.makedirs('logs', exist_ok=True)
    
    # Initialize and run daemon
    daemon = PullerDaemon(
        config_path=args.config,
        db_path=args.db_path,
        interval_seconds=interval
    )
    
    if args.once:
        daemon.run_once()
    else:
        daemon.run()


if __name__ == "__main__":
    main()

