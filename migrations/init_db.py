#!/usr/bin/env python3
"""Initialize the database with schema."""

import sqlite3
import os
from pathlib import Path

def init_database(db_path: str = "db/arbitrage.sqlite"):
    """Create database and apply schema."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Read schema
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, 'r') as f:
        schema = f.read()
    
    # Create database and apply schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Execute schema
    cursor.executescript(schema)
    
    conn.commit()
    conn.close()
    
    print(f"Database initialized at {db_path}")

if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "db/arbitrage.sqlite"
    init_database(db_path)

