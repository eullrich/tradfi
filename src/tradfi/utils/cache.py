"""SQLite caching for API responses and watchlist storage."""

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Default cache location
CACHE_DIR = Path.home() / ".tradfi"
CACHE_DB = CACHE_DIR / "cache.db"
CONFIG_FILE = CACHE_DIR / "config.json"

# Default settings
DEFAULT_CACHE_TTL = 30 * 60  # 30 minutes
# Rate limit for yfinance API calls (only applies on cache miss)
DEFAULT_RATE_LIMIT_DELAY = 2.0  # seconds between yfinance requests


@dataclass
class CacheConfig:
    """Configuration for caching and rate limiting."""
    cache_ttl: int = DEFAULT_CACHE_TTL  # seconds
    rate_limit_delay: float = DEFAULT_RATE_LIMIT_DELAY  # seconds
    cache_enabled: bool = True
    offline_mode: bool = False  # If True, only load from DB, never from API


def load_config() -> CacheConfig:
    """Load configuration from file or return defaults."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
                return CacheConfig(
                    cache_ttl=data.get("cache_ttl", DEFAULT_CACHE_TTL),
                    rate_limit_delay=data.get("rate_limit_delay", DEFAULT_RATE_LIMIT_DELAY),
                    cache_enabled=data.get("cache_enabled", True),
                    offline_mode=data.get("offline_mode", False),
                )
        except Exception:
            pass
    return CacheConfig()


def save_config(config: CacheConfig) -> None:
    """Save configuration to file."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump({
            "cache_ttl": config.cache_ttl,
            "rate_limit_delay": config.rate_limit_delay,
            "cache_enabled": config.cache_enabled,
            "offline_mode": config.offline_mode,
        }, f, indent=2)


# Global config instance
_config: CacheConfig | None = None


def get_config() -> CacheConfig:
    """Get the current cache configuration."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_cache_ttl(minutes: int) -> None:
    """Set cache TTL in minutes."""
    config = get_config()
    config.cache_ttl = minutes * 60
    save_config(config)


def set_rate_limit_delay(seconds: float) -> None:
    """Set rate limit delay in seconds."""
    config = get_config()
    config.rate_limit_delay = seconds
    save_config(config)


def set_cache_enabled(enabled: bool) -> None:
    """Enable or disable caching."""
    config = get_config()
    config.cache_enabled = enabled
    save_config(config)


def set_offline_mode(enabled: bool) -> None:
    """Enable or disable offline mode (DB only, no API calls)."""
    config = get_config()
    config.offline_mode = enabled
    save_config(config)


def get_db_connection() -> sqlite3.Connection:
    """Get a connection to the cache database, creating it if needed."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CACHE_DB)
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    """Initialize the database schema."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS stock_cache (
            ticker TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            cached_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS watchlist (
            ticker TEXT PRIMARY KEY,
            added_at INTEGER NOT NULL,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            threshold REAL NOT NULL,
            created_at INTEGER NOT NULL,
            triggered_at INTEGER,
            FOREIGN KEY (ticker) REFERENCES watchlist(ticker) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS saved_lists (
            name TEXT PRIMARY KEY,
            description TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS saved_list_items (
            list_name TEXT NOT NULL,
            ticker TEXT NOT NULL,
            added_at INTEGER NOT NULL,
            PRIMARY KEY (list_name, ticker),
            FOREIGN KEY (list_name) REFERENCES saved_lists(name) ON DELETE CASCADE
        );

        -- Enhanced list management: Categories/folders for organizing lists
        CREATE TABLE IF NOT EXISTS list_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            color TEXT,
            icon TEXT,
            created_at INTEGER NOT NULL
        );

        -- Enhanced notes for list items (no character limit)
        CREATE TABLE IF NOT EXISTS list_item_notes (
            list_name TEXT NOT NULL,
            ticker TEXT NOT NULL,
            notes TEXT,
            thesis TEXT,
            entry_price REAL,
            target_price REAL,
            added_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            PRIMARY KEY (list_name, ticker)
        );

        -- Smart lists with auto-updating criteria
        CREATE TABLE IF NOT EXISTS smart_lists (
            name TEXT PRIMARY KEY,
            criteria TEXT NOT NULL,
            universe TEXT,
            auto_update INTEGER DEFAULT 1,
            last_updated INTEGER
        );

        -- Link lists to categories
        CREATE TABLE IF NOT EXISTS list_category_membership (
            list_name TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            PRIMARY KEY (list_name, category_id),
            FOREIGN KEY (list_name) REFERENCES saved_lists(name) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES list_categories(id) ON DELETE CASCADE
        );
    """)
    conn.commit()


def cache_stock_data(ticker: str, data: dict) -> None:
    """Cache stock data for a ticker."""
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO stock_cache (ticker, data, cached_at) VALUES (?, ?, ?)",
            (ticker.upper(), json.dumps(data), int(time.time()))
        )
        conn.commit()
    finally:
        conn.close()


def get_cached_stock_data(ticker: str, ttl: int | None = None, ignore_ttl: bool = False) -> dict | None:
    """Get cached stock data if it exists and is fresh.

    Args:
        ticker: Stock ticker symbol
        ttl: Override TTL in seconds (uses config default if None)
        ignore_ttl: If True, return cached data regardless of age

    Returns:
        Cached data dict or None if not found/stale
    """
    config = get_config()
    if not config.cache_enabled:
        return None

    if ttl is None:
        ttl = config.cache_ttl

    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT data, cached_at FROM stock_cache WHERE ticker = ?",
            (ticker.upper(),)
        ).fetchone()

        if row is None:
            return None

        # Check if cache is stale (unless ignoring TTL)
        if not ignore_ttl:
            cache_age = time.time() - row["cached_at"]
            if cache_age > ttl:
                return None

        return json.loads(row["data"])
    finally:
        conn.close()


def get_cache_age(ticker: str) -> float | None:
    """Get the age of cached data in seconds, or None if not cached."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT cached_at FROM stock_cache WHERE ticker = ?",
            (ticker.upper(),)
        ).fetchone()
        if row is None:
            return None
        return time.time() - row["cached_at"]
    finally:
        conn.close()


def get_all_cached_industries() -> list[tuple[str, int]]:
    """Get all unique industries from cached stocks with counts.

    Returns:
        List of (industry_name, count) tuples sorted by count descending.
    """
    from collections import Counter

    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT data FROM stock_cache").fetchall()

        industry_counts: Counter = Counter()
        for row in rows:
            try:
                data = json.loads(row["data"])
                industry = data.get("industry")
                if industry:
                    industry_counts[industry] += 1
            except (json.JSONDecodeError, KeyError):
                pass

        return industry_counts.most_common()
    finally:
        conn.close()


def get_cache_stats() -> dict:
    """Get cache statistics."""
    config = get_config()
    conn = get_db_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM stock_cache").fetchone()[0]
        fresh = conn.execute(
            "SELECT COUNT(*) FROM stock_cache WHERE ? - cached_at <= ?",
            (int(time.time()), config.cache_ttl)
        ).fetchone()[0]
        stale = total - fresh

        # Get most recent cache update time
        last_updated_row = conn.execute(
            "SELECT MAX(cached_at) FROM stock_cache"
        ).fetchone()
        last_updated = last_updated_row[0] if last_updated_row and last_updated_row[0] else None

        return {
            "total_cached": total,
            "fresh": fresh,
            "stale": stale,
            "cache_ttl_minutes": config.cache_ttl // 60,
            "cache_enabled": config.cache_enabled,
            "rate_limit_delay": config.rate_limit_delay,
            "last_updated": last_updated,
        }
    finally:
        conn.close()


def clear_cache() -> int:
    """Clear all cached stock data. Returns number of entries cleared."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("DELETE FROM stock_cache")
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


# Watchlist functions

def add_to_watchlist(ticker: str, notes: str | None = None) -> bool:
    """Add a ticker to the watchlist. Returns True if added, False if already exists."""
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (ticker, added_at, notes) VALUES (?, ?, ?)",
            (ticker.upper(), int(time.time()), notes)
        )
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def remove_from_watchlist(ticker: str) -> bool:
    """Remove a ticker from the watchlist. Returns True if removed."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM watchlist WHERE ticker = ?",
            (ticker.upper(),)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_watchlist() -> list[dict]:
    """Get all tickers in the watchlist."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT ticker, added_at, notes FROM watchlist ORDER BY added_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_watchlist_notes(ticker: str, notes: str) -> bool:
    """Update notes for a watchlist item."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "UPDATE watchlist SET notes = ? WHERE ticker = ?",
            (notes, ticker.upper())
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# Alert functions

def add_alert(ticker: str, alert_type: str, threshold: float) -> int:
    """
    Add an alert for a ticker.

    alert_type can be: 'price_below', 'price_above', 'rsi_below', 'rsi_above', 'pe_below'

    Returns the alert ID.
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO alerts (ticker, alert_type, threshold, created_at) VALUES (?, ?, ?, ?)",
            (ticker.upper(), alert_type, threshold, int(time.time()))
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_alerts(ticker: str | None = None) -> list[dict]:
    """Get all alerts, optionally filtered by ticker."""
    conn = get_db_connection()
    try:
        if ticker:
            rows = conn.execute(
                "SELECT * FROM alerts WHERE ticker = ? AND triggered_at IS NULL ORDER BY created_at",
                (ticker.upper(),)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM alerts WHERE triggered_at IS NULL ORDER BY ticker, created_at"
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def remove_alert(alert_id: int) -> bool:
    """Remove an alert by ID."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def trigger_alert(alert_id: int) -> None:
    """Mark an alert as triggered."""
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE alerts SET triggered_at = ? WHERE id = ?",
            (int(time.time()), alert_id)
        )
        conn.commit()
    finally:
        conn.close()


# Saved list functions

def save_list(name: str, tickers: list[str], description: str | None = None) -> bool:
    """
    Save a list of tickers with a name.

    Args:
        name: Name for the list (will be lowercased)
        tickers: List of ticker symbols
        description: Optional description for the list

    Returns:
        True if saved successfully
    """
    name = name.lower().replace(" ", "-")
    now = int(time.time())
    conn = get_db_connection()
    try:
        # Create or update the list
        conn.execute(
            """INSERT INTO saved_lists (name, description, created_at, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET description = ?, updated_at = ?""",
            (name, description, now, now, description, now)
        )

        # Clear existing items and add new ones
        conn.execute("DELETE FROM saved_list_items WHERE list_name = ?", (name,))

        for ticker in tickers:
            conn.execute(
                "INSERT INTO saved_list_items (list_name, ticker, added_at) VALUES (?, ?, ?)",
                (name, ticker.upper(), now)
            )

        conn.commit()
        return True
    finally:
        conn.close()


def get_saved_list(name: str) -> list[str] | None:
    """
    Get tickers from a saved list.

    Args:
        name: Name of the list

    Returns:
        List of ticker symbols, or None if list doesn't exist
    """
    name = name.lower().replace(" ", "-")
    conn = get_db_connection()
    try:
        # Check if list exists
        row = conn.execute(
            "SELECT name FROM saved_lists WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            return None

        rows = conn.execute(
            "SELECT ticker FROM saved_list_items WHERE list_name = ? ORDER BY added_at",
            (name,)
        ).fetchall()
        return [row["ticker"] for row in rows]
    finally:
        conn.close()


def list_saved_lists() -> list[dict]:
    """
    Get all saved lists with their metadata.

    Returns:
        List of dicts with name, description, count, created_at, updated_at
    """
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT
                sl.name,
                sl.description,
                sl.created_at,
                sl.updated_at,
                COUNT(sli.ticker) as count
            FROM saved_lists sl
            LEFT JOIN saved_list_items sli ON sl.name = sli.list_name
            GROUP BY sl.name
            ORDER BY sl.updated_at DESC
        """).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_saved_list(name: str) -> bool:
    """
    Delete a saved list.

    Args:
        name: Name of the list to delete

    Returns:
        True if deleted, False if list didn't exist
    """
    name = name.lower().replace(" ", "-")
    conn = get_db_connection()
    try:
        # Delete items first (foreign key)
        conn.execute("DELETE FROM saved_list_items WHERE list_name = ?", (name,))
        cursor = conn.execute("DELETE FROM saved_lists WHERE name = ?", (name,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def add_to_saved_list(name: str, ticker: str) -> bool:
    """
    Add a single ticker to an existing saved list.

    Args:
        name: Name of the list
        ticker: Ticker to add

    Returns:
        True if added, False if list doesn't exist or ticker already in list
    """
    name = name.lower().replace(" ", "-")
    conn = get_db_connection()
    try:
        # Check if list exists
        row = conn.execute(
            "SELECT name FROM saved_lists WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            return False

        try:
            conn.execute(
                "INSERT INTO saved_list_items (list_name, ticker, added_at) VALUES (?, ?, ?)",
                (name, ticker.upper(), int(time.time()))
            )
            conn.execute(
                "UPDATE saved_lists SET updated_at = ? WHERE name = ?",
                (int(time.time()), name)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Already in list
    finally:
        conn.close()


def remove_from_saved_list(name: str, ticker: str) -> bool:
    """
    Remove a ticker from a saved list.

    Args:
        name: Name of the list
        ticker: Ticker to remove

    Returns:
        True if removed, False if not found
    """
    name = name.lower().replace(" ", "-")
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM saved_list_items WHERE list_name = ? AND ticker = ?",
            (name, ticker.upper())
        )
        if cursor.rowcount > 0:
            conn.execute(
                "UPDATE saved_lists SET updated_at = ? WHERE name = ?",
                (int(time.time()), name)
            )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ============================================================================
# CATEGORY MANAGEMENT
# ============================================================================

def create_category(name: str, color: str | None = None, icon: str | None = None) -> int | None:
    """
    Create a new list category.

    Args:
        name: Category name
        color: Optional color (e.g., "blue", "red")
        icon: Optional icon/emoji

    Returns:
        Category ID if created, None if already exists
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO list_categories (name, color, icon, created_at) VALUES (?, ?, ?, ?)",
            (name, color, icon, int(time.time()))
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def list_categories() -> list[dict]:
    """Get all categories with their list counts."""
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT
                c.id,
                c.name,
                c.color,
                c.icon,
                c.created_at,
                COUNT(m.list_name) as list_count
            FROM list_categories c
            LEFT JOIN list_category_membership m ON c.id = m.category_id
            GROUP BY c.id
            ORDER BY c.name
        """).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_category(category_id: int) -> bool:
    """Delete a category (lists are not deleted, just unlinked)."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("DELETE FROM list_categories WHERE id = ?", (category_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def add_list_to_category(list_name: str, category_id: int) -> bool:
    """Add a list to a category."""
    list_name = list_name.lower().replace(" ", "-")
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO list_category_membership (list_name, category_id) VALUES (?, ?)",
            (list_name, category_id)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def remove_list_from_category(list_name: str, category_id: int) -> bool:
    """Remove a list from a category."""
    list_name = list_name.lower().replace(" ", "-")
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM list_category_membership WHERE list_name = ? AND category_id = ?",
            (list_name, category_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_lists_in_category(category_id: int) -> list[str]:
    """Get all list names in a category."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT list_name FROM list_category_membership WHERE category_id = ?",
            (category_id,)
        ).fetchall()
        return [row["list_name"] for row in rows]
    finally:
        conn.close()


def get_category_by_name(name: str) -> dict | None:
    """Get a category by name."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT id, name, color, icon, created_at FROM list_categories WHERE name = ?",
            (name,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ============================================================================
# ENHANCED NOTES
# ============================================================================

def set_item_note(
    list_name: str,
    ticker: str,
    notes: str | None = None,
    thesis: str | None = None,
    entry_price: float | None = None,
    target_price: float | None = None,
) -> bool:
    """
    Set or update notes for a list item.

    Args:
        list_name: Name of the list
        ticker: Stock ticker
        notes: General notes
        thesis: Investment thesis
        entry_price: Price at entry
        target_price: Target price

    Returns:
        True if successful
    """
    list_name = list_name.lower().replace(" ", "-")
    ticker = ticker.upper()
    now = int(time.time())

    conn = get_db_connection()
    try:
        # Check if note exists
        existing = conn.execute(
            "SELECT * FROM list_item_notes WHERE list_name = ? AND ticker = ?",
            (list_name, ticker)
        ).fetchone()

        if existing:
            # Update existing - only update provided fields
            updates = []
            params = []
            if notes is not None:
                updates.append("notes = ?")
                params.append(notes)
            if thesis is not None:
                updates.append("thesis = ?")
                params.append(thesis)
            if entry_price is not None:
                updates.append("entry_price = ?")
                params.append(entry_price)
            if target_price is not None:
                updates.append("target_price = ?")
                params.append(target_price)

            if updates:
                updates.append("updated_at = ?")
                params.append(now)
                params.extend([list_name, ticker])
                conn.execute(
                    f"UPDATE list_item_notes SET {', '.join(updates)} WHERE list_name = ? AND ticker = ?",
                    params
                )
        else:
            # Insert new
            conn.execute(
                """INSERT INTO list_item_notes
                   (list_name, ticker, notes, thesis, entry_price, target_price, added_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (list_name, ticker, notes, thesis, entry_price, target_price, now, now)
            )

        conn.commit()
        return True
    finally:
        conn.close()


def get_item_note(list_name: str, ticker: str) -> dict | None:
    """Get notes for a list item."""
    list_name = list_name.lower().replace(" ", "-")
    ticker = ticker.upper()

    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM list_item_notes WHERE list_name = ? AND ticker = ?",
            (list_name, ticker)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_item_notes(list_name: str) -> list[dict]:
    """Get all notes for items in a list."""
    list_name = list_name.lower().replace(" ", "-")

    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM list_item_notes WHERE list_name = ? ORDER BY ticker",
            (list_name,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_item_note(list_name: str, ticker: str) -> bool:
    """Delete notes for a list item."""
    list_name = list_name.lower().replace(" ", "-")
    ticker = ticker.upper()

    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM list_item_notes WHERE list_name = ? AND ticker = ?",
            (list_name, ticker)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ============================================================================
# SMART LISTS
# ============================================================================

def create_smart_list(name: str, criteria: dict, universe: str | None = None, auto_update: bool = True) -> bool:
    """
    Create a smart list with auto-updating criteria.

    Args:
        name: Name of the smart list
        criteria: Screening criteria as dict
        universe: Universe to screen (e.g., "sp500")
        auto_update: Whether to auto-update on refresh

    Returns:
        True if created
    """
    name = name.lower().replace(" ", "-")
    conn = get_db_connection()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO smart_lists
               (name, criteria, universe, auto_update, last_updated)
               VALUES (?, ?, ?, ?, ?)""",
            (name, json.dumps(criteria), universe, 1 if auto_update else 0, int(time.time()))
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_smart_list(name: str) -> dict | None:
    """Get a smart list by name."""
    name = name.lower().replace(" ", "-")
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM smart_lists WHERE name = ?", (name,)
        ).fetchone()
        if row:
            result = dict(row)
            result["criteria"] = json.loads(result["criteria"])
            return result
        return None
    finally:
        conn.close()


def list_smart_lists() -> list[dict]:
    """Get all smart lists."""
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM smart_lists ORDER BY name").fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["criteria"] = json.loads(d["criteria"])
            result.append(d)
        return result
    finally:
        conn.close()


def delete_smart_list(name: str) -> bool:
    """Delete a smart list."""
    name = name.lower().replace(" ", "-")
    conn = get_db_connection()
    try:
        cursor = conn.execute("DELETE FROM smart_lists WHERE name = ?", (name,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def update_smart_list_timestamp(name: str) -> None:
    """Update the last_updated timestamp for a smart list."""
    name = name.lower().replace(" ", "-")
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE smart_lists SET last_updated = ? WHERE name = ?",
            (int(time.time()), name)
        )
        conn.commit()
    finally:
        conn.close()
