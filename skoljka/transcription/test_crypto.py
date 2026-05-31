import os
from unittest import mock

from cryptography.fernet import InvalidToken
from django.test import SimpleTestCase, override_settings

from skoljka.transcription.crypto import (
    cache_key,
    decrypt_blob,
    encrypt_blob,
    file_key,
)


class FileKeyTest(SimpleTestCase):
    def test_roundtrip(self):
        key = file_key()
        payload = b"hello world"
        ct = encrypt_blob(payload, key)
        self.assertEqual(decrypt_blob(ct, key), payload)

    def test_stable_across_calls(self):
        self.assertEqual(file_key(), file_key())

    @override_settings(SECRET_KEY="different-secret-value")
    def test_rotating_secret_invalidates(self):
        k1 = file_key()
        ct = encrypt_blob(b"x", k1)
        with override_settings(SECRET_KEY="another-secret"):
            k2 = file_key()
            with self.assertRaises(InvalidToken):
                decrypt_blob(ct, k2)


class CacheKeyTest(SimpleTestCase):
    def test_rotating_mistral_key_invalidates(self):
        with mock.patch.dict(os.environ, {"MISTRAL_API_KEY": "k1", "ANTHROPIC_API_KEY": ""}):
            k1 = cache_key()
            ct = encrypt_blob(b"x", k1)
        with mock.patch.dict(os.environ, {"MISTRAL_API_KEY": "k2", "ANTHROPIC_API_KEY": ""}):
            k2 = cache_key()
            with self.assertRaises(InvalidToken):
                decrypt_blob(ct, k2)

    def test_rotating_anthropic_key_invalidates(self):
        with mock.patch.dict(os.environ, {"MISTRAL_API_KEY": "", "ANTHROPIC_API_KEY": "k1"}):
            k1 = cache_key()
            ct = encrypt_blob(b"x", k1)
        with mock.patch.dict(os.environ, {"MISTRAL_API_KEY": "", "ANTHROPIC_API_KEY": "k2"}):
            k2 = cache_key()
            with self.assertRaises(InvalidToken):
                decrypt_blob(ct, k2)

    def test_same_env_same_key(self):
        with mock.patch.dict(os.environ, {"MISTRAL_API_KEY": "a", "ANTHROPIC_API_KEY": "b"}):
            self.assertEqual(cache_key(), cache_key())


class CompressionTest(SimpleTestCase):
    def test_compressible_payload_smaller_than_plain_fernet(self):
        """Compression happens before encryption."""
        from cryptography.fernet import Fernet

        payload = b"abc" * 10_000
        key = file_key()
        ours = encrypt_blob(payload, key)
        naive = Fernet(key).encrypt(payload)
        self.assertLess(len(ours), len(naive))

    def test_large_random_binary_roundtrip(self):
        payload = os.urandom(200_000)
        key = file_key()
        self.assertEqual(decrypt_blob(encrypt_blob(payload, key), key), payload)
