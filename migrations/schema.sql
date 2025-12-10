-- CS2 Arbitrage Database Schema
-- Version: 1.0

-- Items table: normalized item metadata
CREATE TABLE IF NOT EXISTS items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_hash_name TEXT NOT NULL UNIQUE,
    buff_goods_id INTEGER,
    app_id INTEGER DEFAULT 730,  -- CS2 app ID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_items_market_hash_name ON items(market_hash_name);
CREATE INDEX IF NOT EXISTS idx_items_buff_goods_id ON items(buff_goods_id);

-- Steam snapshots: price and order book data from Steam
CREATE TABLE IF NOT EXISTS steam_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    best_bid REAL,
    best_ask REAL,
    volume_24h INTEGER,
    volume_7d INTEGER,
    median_price REAL,
    lowest_price REAL,
    highest_price REAL,
    currency_id INTEGER DEFAULT 3,  -- EUR default
    raw_response TEXT,  -- JSON response for debugging
    FOREIGN KEY (item_id) REFERENCES items(item_id),
    UNIQUE(item_id, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_steam_snapshots_item_id ON steam_snapshots(item_id);
CREATE INDEX IF NOT EXISTS idx_steam_snapshots_timestamp ON steam_snapshots(timestamp);

-- Buff snapshots: price and order book data from Buff
CREATE TABLE IF NOT EXISTS buff_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    best_ask REAL,
    best_bid REAL,
    volume_24h INTEGER,
    volume_7d INTEGER,
    sell_order_count INTEGER,
    buy_order_count INTEGER,
    currency TEXT DEFAULT 'CNY',
    raw_response TEXT,  -- JSON response for debugging
    FOREIGN KEY (item_id) REFERENCES items(item_id),
    UNIQUE(item_id, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_buff_snapshots_item_id ON buff_snapshots(item_id);
CREATE INDEX IF NOT EXISTS idx_buff_snapshots_timestamp ON buff_snapshots(timestamp);

-- Book depth: detailed order book data (optional, for deeper analysis)
CREATE TABLE IF NOT EXISTS book_depth (
    depth_id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    source TEXT NOT NULL,  -- 'steam' or 'buff'
    side TEXT NOT NULL,  -- 'bid' or 'ask'
    price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    order_rank INTEGER,  -- Position in book (1 = top of book)
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- Note: Foreign key constraint removed due to SQLite limitation
    -- snapshot_id can reference either steam_snapshots or buff_snapshots
);

CREATE INDEX IF NOT EXISTS idx_book_depth_snapshot_source ON book_depth(snapshot_id, source);
CREATE INDEX IF NOT EXISTS idx_book_depth_side ON book_depth(side);

-- Fetch logs: track API requests for debugging and rate limiting
CREATE TABLE IF NOT EXISTS fetch_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,  -- 'steam' or 'buff'
    endpoint TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status_code INTEGER,
    latency_ms INTEGER,
    success BOOLEAN,
    error_message TEXT,
    item_id INTEGER,
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);

CREATE INDEX IF NOT EXISTS idx_fetch_logs_timestamp ON fetch_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_fetch_logs_source ON fetch_logs(source);

-- Trade candidates: evaluated arbitrage opportunities
CREATE TABLE IF NOT EXISTS trade_candidates (
    candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    buff_ask REAL NOT NULL,
    steam_bid REAL NOT NULL,
    adj_steam_bid REAL NOT NULL,  -- After Steam fee
    pnl_now REAL NOT NULL,
    spread_pct REAL NOT NULL,
    hold_days INTEGER DEFAULT 3,
    prob_positive_after_hold REAL,
    expected_pnl_after_hold REAL,
    var_95 REAL,  -- 95% VaR
    risk_score REAL,
    execution_prob REAL DEFAULT 0.6,
    recommended_action TEXT,  -- 'monitor', 'candidate', 'skip'
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);

CREATE INDEX IF NOT EXISTS idx_trade_candidates_timestamp ON trade_candidates(timestamp);
CREATE INDEX IF NOT EXISTS idx_trade_candidates_pnl ON trade_candidates(pnl_now);

