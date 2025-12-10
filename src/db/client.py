"""Database client for arbitrage system."""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class DatabaseClient:
    """SQLite database client for storing market data."""
    
    def __init__(self, db_path: str = "db/arbitrage.sqlite"):
        """Initialize database client.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Ensure database schema exists."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='items'
        """)
        
        if not cursor.fetchone():
            logger.warning("Schema not found. Run migrations/init_db.py first.")
        
        conn.close()
    
    def get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
        return conn
    
    def get_or_create_item(self, market_hash_name: str, buff_goods_id: Optional[int] = None) -> int:
        """Get existing item ID or create new item.
        
        Args:
            market_hash_name: Steam market hash name
            buff_goods_id: Optional Buff goods ID
            
        Returns:
            item_id: Database item ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Try to find existing item
        cursor.execute("""
            SELECT item_id FROM items 
            WHERE market_hash_name = ?
        """, (market_hash_name,))
        
        row = cursor.fetchone()
        if row:
            item_id = row['item_id']
            # Update buff_goods_id if provided
            if buff_goods_id:
                cursor.execute("""
                    UPDATE items 
                    SET buff_goods_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE item_id = ?
                """, (buff_goods_id, item_id))
                conn.commit()
        else:
            # Create new item
            cursor.execute("""
                INSERT INTO items (market_hash_name, buff_goods_id)
                VALUES (?, ?)
            """, (market_hash_name, buff_goods_id))
            item_id = cursor.lastrowid
            conn.commit()
        
        conn.close()
        return item_id
    
    def insert_steam_snapshot(
        self,
        item_id: int,
        best_bid: Optional[float] = None,
        best_ask: Optional[float] = None,
        volume_24h: Optional[int] = None,
        volume_7d: Optional[int] = None,
        median_price: Optional[float] = None,
        lowest_price: Optional[float] = None,
        highest_price: Optional[float] = None,
        currency_id: int = 3,
        raw_response: Optional[Dict] = None
    ) -> int:
        """Insert Steam price snapshot.
        
        Returns:
            snapshot_id: ID of inserted snapshot
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        raw_json = json.dumps(raw_response) if raw_response else None
        
        cursor.execute("""
            INSERT INTO steam_snapshots 
            (item_id, best_bid, best_ask, volume_24h, volume_7d, 
             median_price, lowest_price, highest_price, currency_id, raw_response)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item_id, best_bid, best_ask, volume_24h, volume_7d,
              median_price, lowest_price, highest_price, currency_id, raw_json))
        
        snapshot_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return snapshot_id
    
    def insert_buff_snapshot(
        self,
        item_id: int,
        best_ask: Optional[float] = None,
        best_bid: Optional[float] = None,
        volume_24h: Optional[int] = None,
        volume_7d: Optional[int] = None,
        sell_order_count: Optional[int] = None,
        buy_order_count: Optional[int] = None,
        currency: str = 'CNY',
        raw_response: Optional[Dict] = None
    ) -> int:
        """Insert Buff price snapshot.
        
        Returns:
            snapshot_id: ID of inserted snapshot
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        raw_json = json.dumps(raw_response) if raw_response else None
        
        cursor.execute("""
            INSERT INTO buff_snapshots 
            (item_id, best_ask, best_bid, volume_24h, volume_7d,
             sell_order_count, buy_order_count, currency, raw_response)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item_id, best_ask, best_bid, volume_24h, volume_7d,
              sell_order_count, buy_order_count, currency, raw_json))
        
        snapshot_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return snapshot_id
    
    def log_fetch(
        self,
        source: str,
        endpoint: str,
        status_code: Optional[int] = None,
        latency_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        item_id: Optional[int] = None
    ):
        """Log API fetch request."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO fetch_logs 
            (source, endpoint, status_code, latency_ms, success, error_message, item_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (source, endpoint, status_code, latency_ms, success, error_message, item_id))
        
        conn.commit()
        conn.close()
    
    def get_latest_snapshots(self, item_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get latest snapshots for all items or specific item.
        
        Args:
            item_id: Optional item ID filter
            
        Returns:
            List of snapshot dictionaries with joined item data
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get latest Steam snapshot per item
        # Probably could do this with a window function but sqlite version might not support it
        cursor.execute("""
            SELECT item_id, MAX(timestamp) as max_timestamp
            FROM steam_snapshots
            GROUP BY item_id
        """)
        steam_latest = {row['item_id']: row['max_timestamp'] for row in cursor.fetchall()}
        
        # Get latest Buff snapshot per item
        cursor.execute("""
            SELECT item_id, MAX(timestamp) as max_timestamp
            FROM buff_snapshots
            GROUP BY item_id
        """)
        buff_latest = {row['item_id']: row['max_timestamp'] for row in cursor.fetchall()}
        
        # Build query
        if item_id:
            cursor.execute("""
                SELECT 
                    i.item_id,
                    i.market_hash_name,
                    s.timestamp as steam_timestamp,
                    s.best_bid as steam_best_bid,
                    s.volume_7d as steam_volume_7d,
                    b.timestamp as buff_timestamp,
                    b.best_ask as buff_best_ask,
                    b.volume_7d as buff_volume_7d
                FROM items i
                LEFT JOIN steam_snapshots s ON i.item_id = s.item_id 
                    AND s.timestamp = ?
                LEFT JOIN buff_snapshots b ON i.item_id = b.item_id 
                    AND b.timestamp = ?
                WHERE i.item_id = ?
            """, (steam_latest.get(item_id), buff_latest.get(item_id), item_id))
        else:
            # For all items, we need to join with latest timestamps
            # Use a simpler approach: get items and latest snapshots separately
            cursor.execute("SELECT item_id, market_hash_name FROM items")
            items = cursor.fetchall()
            
            results = []
            for item_row in items:
                item_id = item_row['item_id']
                steam_ts = steam_latest.get(item_id)
                buff_ts = buff_latest.get(item_id)
                
                # Get latest Steam snapshot
                steam_data = None
                if steam_ts:
                    cursor.execute("""
                        SELECT timestamp, best_bid, volume_7d
                        FROM steam_snapshots
                        WHERE item_id = ? AND timestamp = ?
                    """, (item_id, steam_ts))
                    steam_row = cursor.fetchone()
                    if steam_row:
                        steam_data = dict(steam_row)
                
                # Get latest Buff snapshot
                buff_data = None
                if buff_ts:
                    cursor.execute("""
                        SELECT timestamp, best_ask, volume_7d
                        FROM buff_snapshots
                        WHERE item_id = ? AND timestamp = ?
                    """, (item_id, buff_ts))
                    buff_row = cursor.fetchone()
                    if buff_row:
                        buff_data = dict(buff_row)
                
                result = {
                    'item_id': item_id,
                    'market_hash_name': item_row['market_hash_name'],
                    'steam_timestamp': steam_data['timestamp'] if steam_data else None,
                    'steam_best_bid': steam_data['best_bid'] if steam_data else None,
                    'steam_volume_7d': steam_data['volume_7d'] if steam_data else None,
                    'buff_timestamp': buff_data['timestamp'] if buff_data else None,
                    'buff_best_ask': buff_data['best_ask'] if buff_data else None,
                    'buff_volume_7d': buff_data['volume_7d'] if buff_data else None,
                }
                results.append(result)
            
            conn.close()
            return results
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_price_history(self, item_id: int, days: int = 7) -> Dict[str, List]:
        """Get price history for an item.
        
        Args:
            item_id: Item ID
            days: Number of days of history
            
        Returns:
            Dictionary with 'steam' and 'buff' price lists
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get Steam history
        cursor.execute("""
            SELECT timestamp, best_bid, median_price
            FROM steam_snapshots
            WHERE item_id = ? 
            AND timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp ASC
        """, (item_id, days))
        
        steam_data = [dict(row) for row in cursor.fetchall()]
        
        # Get Buff history
        cursor.execute("""
            SELECT timestamp, best_ask
            FROM buff_snapshots
            WHERE item_id = ? 
            AND timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp ASC
        """, (item_id, days))
        
        buff_data = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'steam': steam_data,
            'buff': buff_data
        }

