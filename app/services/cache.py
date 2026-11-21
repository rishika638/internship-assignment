import os
import sqlite3
import json
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from app.config import get_settings
from app.utils.logger import logger

class SQLiteCacheManager:
    def __init__(self, db_path: Optional[str] = None):
        self.settings = get_settings()
        self.db_path = db_path or self.settings.CACHE_DB_PATH
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # 1. Main cache table keyed by content_hash and url
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS link_analysis_cache (
                        content_hash TEXT PRIMARY KEY,
                        url TEXT NOT NULL,
                        response_json TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        model TEXT NOT NULL,
                        input_tokens INTEGER DEFAULT 0,
                        output_tokens INTEGER DEFAULT 0,
                        estimated_cost_usd REAL DEFAULT 0.0,
                        created_at REAL NOT NULL,
                        expires_at REAL NOT NULL,
                        hit_count INTEGER DEFAULT 0
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_url ON link_analysis_cache(url)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON link_analysis_cache(expires_at)")

                # 2. Analysis history table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS analysis_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        content_hash TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        model TEXT NOT NULL,
                        execution_time_ms REAL NOT NULL,
                        estimated_cost_usd REAL NOT NULL
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_time ON analysis_history(timestamp DESC)")
                conn.commit()
                logger.info(f"SQLite cache initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize SQLite cache database: {e}")

    def get(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve unexpired cached analysis by content hash."""
        if not self.settings.CACHE_ENABLED:
            return None

        now = time.time()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT response_json, expires_at, hit_count FROM link_analysis_cache WHERE content_hash = ?",
                    (content_hash,)
                )
                row = cursor.fetchone()
                if not row:
                    return None

                if row["expires_at"] < now:
                    # Expired, clean it up
                    cursor.execute("DELETE FROM link_analysis_cache WHERE content_hash = ?", (content_hash,))
                    conn.commit()
                    logger.info(f"Cache expired for content hash {content_hash}")
                    return None

                # Increment hit count
                cursor.execute(
                    "UPDATE link_analysis_cache SET hit_count = hit_count + 1 WHERE content_hash = ?",
                    (content_hash,)
                )
                conn.commit()
                logger.info(f"Cache HIT for content hash {content_hash} (total hits: {row['hit_count'] + 1})")
                return json.loads(row["response_json"])
        except Exception as e:
            logger.warning(f"Error reading from SQLite cache: {e}")
            return None

    def set(
        self,
        content_hash: str,
        url: str,
        response_dict: Dict[str, Any],
        provider: str,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
        ttl_seconds: Optional[int] = None,
    ):
        """Store analysis response in SQLite cache."""
        if not self.settings.CACHE_ENABLED:
            return

        ttl = ttl_seconds or self.settings.CACHE_TTL_SECONDS
        now = time.time()
        expires_at = now + ttl

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO link_analysis_cache (
                        content_hash, url, response_json, provider, model,
                        input_tokens, output_tokens, estimated_cost_usd,
                        created_at, expires_at, hit_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    content_hash,
                    url,
                    json.dumps(response_dict),
                    provider,
                    model,
                    input_tokens,
                    output_tokens,
                    estimated_cost_usd,
                    now,
                    expires_at,
                    0
                ))
                conn.commit()
                logger.info(f"Cached analysis for {url} [hash: {content_hash[:10]}...] TTL: {ttl}s")
        except Exception as e:
            logger.warning(f"Error saving to SQLite cache: {e}")

    def record_history(
        self,
        url: str,
        content_hash: str,
        provider: str,
        model: str,
        execution_time_ms: float,
        estimated_cost_usd: float
    ):
        """Record an entry in the analysis audit history."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                iso_now = datetime.now(timezone.utc).isoformat()
                cursor.execute("""
                    INSERT INTO analysis_history (
                        url, timestamp, content_hash, provider, model,
                        execution_time_ms, estimated_cost_usd
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (url, iso_now, content_hash, provider, model, execution_time_ms, estimated_cost_usd))
                conn.commit()
        except Exception as e:
            logger.warning(f"Error recording analysis history: {e}")

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch latest analysis history entries."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT url, timestamp, content_hash, provider, model, execution_time_ms, estimated_cost_usd FROM analysis_history ORDER BY id DESC LIMIT ?",
                    (limit,)
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching history: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get caching telemetry including hit rates, token savings, and cost savings."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) AS total_entries, SUM(hit_count) AS total_hits FROM link_analysis_cache")
                summary = cursor.fetchone()
                total_entries = summary["total_entries"] or 0
                total_hits = summary["total_hits"] or 0

                # Compute approximate savings
                cursor.execute("SELECT SUM(input_tokens * hit_count) AS tokens_in_saved, SUM(output_tokens * hit_count) AS tokens_out_saved, SUM(estimated_cost_usd * hit_count) AS cost_saved FROM link_analysis_cache")
                savings = cursor.fetchone()
                tokens_saved = (savings["tokens_in_saved"] or 0) + (savings["tokens_out_saved"] or 0)
                cost_saved = round(savings["cost_saved"] or 0.0, 6)

                return {
                    "cache_enabled": self.settings.CACHE_ENABLED,
                    "total_entries": total_entries,
                    "total_hits": total_hits,
                    "tokens_saved": tokens_saved,
                    "cost_saved_usd": cost_saved,
                    "ttl_seconds": self.settings.CACHE_TTL_SECONDS
                }
        except Exception as e:
            logger.error(f"Error computing cache stats: {e}")
            return {"error": str(e)}

cache_manager = SQLiteCacheManager()
