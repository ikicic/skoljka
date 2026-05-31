from unittest import mock

from django.test import SimpleTestCase

from skoljka.transcription.api_keys import require_api_key


class ApiKeyTest(SimpleTestCase):
    def test_require_api_key_returns_configured_value(self):
        with mock.patch.dict("os.environ", {"MISTRAL_API_KEY": "secret"}, clear=True):
            self.assertEqual(require_api_key("MISTRAL_API_KEY"), "secret")

    def test_require_api_key_rejects_missing_value(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesMessage(RuntimeError, "MISTRAL_API_KEY is not configured."):
                require_api_key("MISTRAL_API_KEY")

    def test_require_api_key_rejects_empty_value(self):
        with mock.patch.dict("os.environ", {"MISTRAL_API_KEY": ""}, clear=True):
            with self.assertRaisesMessage(RuntimeError, "MISTRAL_API_KEY is not configured."):
                require_api_key("MISTRAL_API_KEY")
