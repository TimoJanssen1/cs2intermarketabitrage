#!/usr/bin/env python3
"""Helper script to add items to the database."""

import argparse
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.db.client import DatabaseClient

def main():
    parser = argparse.ArgumentParser(description='Add an item to the database')
    parser.add_argument('market_hash_name', help='Steam market hash name')
    parser.add_argument('--buff_goods_id', type=int, help='Buff goods ID (optional)')
    parser.add_argument('--db_path', default='db/arbitrage.sqlite', help='Database path')
    
    args = parser.parse_args()
    
    db_client = DatabaseClient(args.db_path)
    item_id = db_client.get_or_create_item(args.market_hash_name, args.buff_goods_id)
    
    print(f"Item added/updated: item_id={item_id}, market_hash_name={args.market_hash_name}")

if __name__ == "__main__":
    main()

