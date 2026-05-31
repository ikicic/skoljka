import os
import time
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase

from skoljka.transcription.cache import APICache


class APICacheTest(SimpleTestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "cache.sqlite"

    def test_put_then_get(self):
        cache = APICache(self.path, ttl_seconds=60)
        cache.put("k", "hello")
        self.assertEqual(cache.get("k"), "hello")

    def test_missing_returns_none(self):
        cache = APICache(self.path, ttl_seconds=60)
        self.assertIsNone(cache.get("nope"))

    def test_ttl_expiry(self):
        cache = APICache(self.path, ttl_seconds=0)
        cache.put("k", "v")
        time.sleep(0.01)
        self.assertIsNone(cache.get("k"))

    def test_expired_entries_deleted_on_read(self):
        cache = APICache(self.path, ttl_seconds=0)
        cache.put("k", "v")
        time.sleep(0.01)
        cache.get("k")
        row = cache.conn.execute("SELECT COUNT(*) FROM cache").fetchone()
        self.assertEqual(row[0], 0)

    def test_cleanup_expired(self):
        cache = APICache(self.path, ttl_seconds=0)
        for i in range(3):
            cache.put(f"k{i}", f"v{i}")
        time.sleep(0.01)
        n = cache.cleanup_expired()
        self.assertEqual(n, 3)

    def test_api_key_rotation_purges_lazily(self):
        """Stale ciphertext is treated as a miss and purged."""
        with mock.patch.dict(os.environ, {"MISTRAL_API_KEY": "key-v1"}):
            cache = APICache(self.path, ttl_seconds=60)
            cache.put("k", "value")

        with mock.patch.dict(os.environ, {"MISTRAL_API_KEY": "key-v2"}):
            self.assertIsNone(cache.get("k"))
            row = cache.conn.execute("SELECT COUNT(*) FROM cache").fetchone()
            self.assertEqual(row[0], 0)

    def test_values_are_encrypted_on_disk(self):
        cache = APICache(self.path, ttl_seconds=60)
        cache.put("k", "SECRET_PLAINTEXT_MARKER")
        raw = cache.conn.execute("SELECT value FROM cache WHERE key=?", ("k",)).fetchone()[0]
        self.assertNotIn(b"SECRET_PLAINTEXT_MARKER", bytes(raw))
