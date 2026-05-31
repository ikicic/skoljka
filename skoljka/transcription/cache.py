"""Encrypted SQLite API cache with TTL cleanup."""

import hashlib
import logging
import sqlite3
import time
from pathlib import Path

from cryptography.fernet import InvalidToken

from skoljka.transcription.crypto import cache_key, decrypt_blob, encrypt_blob

logger = logging.getLogger(__name__)


class APICache:
    def __init__(self, db_path: Path, ttl_seconds: int) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS cache "
            "(key TEXT PRIMARY KEY, value BLOB NOT NULL, created_at REAL NOT NULL)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS cache_created_at ON cache(created_at)"
        )
        self.conn.commit()

    def get(self, key: str) -> str | None:
        row = self.conn.execute(
            "SELECT value, created_at FROM cache WHERE key=?", (key,),
        ).fetchone()
        if row is None:
            return None
        value, created_at = row
        if time.time() - created_at > self.ttl_seconds:
            self._delete(key)
            return None
        try:
            return decrypt_blob(bytes(value), cache_key()).decode("utf-8")
        except InvalidToken:
            logger.warning("APICache: stale ciphertext for key=%s, purging", _short(key))
            self._delete(key)
            return None

    def put(self, key: str, value: str) -> None:
        enc = encrypt_blob(value.encode("utf-8"), cache_key())
        self.conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, created_at) VALUES (?, ?, ?)",
            (key, enc, time.time()),
        )
        self.conn.commit()

    def cleanup_expired(self) -> int:
        cutoff = time.time() - self.ttl_seconds
        cur = self.conn.execute("DELETE FROM cache WHERE created_at < ?", (cutoff,))
        self.conn.commit()
        return cur.rowcount

    def _delete(self, key: str) -> None:
        self.conn.execute("DELETE FROM cache WHERE key=?", (key,))
        self.conn.commit()


def _short(key: str) -> str:
    """Short, non-reversible preview of a cache key for logs."""
    return hashlib.sha256(key.encode()).hexdigest()[:8]


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()
