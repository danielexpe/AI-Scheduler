import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestDeepSeekClient(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._saved_env = {}
        for key in ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL",
                     "DEEPSEEK_MAX_TOKENS", "DEEPSEEK_TIMEOUT", "DEEPSEEK_MAX_RETRIES"):
            cls._saved_env[key] = os.environ.get(key)

    @classmethod
    def tearDownClass(cls):
        for key, orig_value in cls._saved_env.items():
            if orig_value is not None:
                os.environ[key] = orig_value
            elif key in os.environ:
                del os.environ[key]

    def setUp(self):
        os.environ.update({
            "DEEPSEEK_API_KEY": "sk-test-key",
            "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
            "DEEPSEEK_MODEL": "deepseek-chat",
            "DEEPSEEK_MAX_TOKENS": "4096",
            "DEEPSEEK_TIMEOUT": "10",
            "DEEPSEEK_MAX_RETRIES": "1",
        })
        from importlib import reload
        import app.deepseek_client
        reload(app.deepseek_client)
        self.client = app.deepseek_client

    def tearDown(self):
        for key in self._saved_env:
            if self._saved_env[key] is not None:
                os.environ[key] = self._saved_env[key]
            elif key in os.environ:
                del os.environ[key]

    def test_api_key_not_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            from importlib import reload
            import app.deepseek_client
            reload(app.deepseek_client)
            result, error = app.deepseek_client.call_deepseek("Test prompt")
            self.assertIsNone(result)
            self.assertIn("API_KEY", error)

    @patch("app.deepseek_client.requests.post")
    def test_successful_call(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "<html><body>Resultado</body></html>"}}]
        }
        mock_post.return_value = mock_response

        result, error = self.client.call_deepseek("Resuma noticias", tone="resumo")
        self.assertIsNone(error)
        self.assertIsNotNone(result)
        self.assertIn("<html>", result)

    @patch("app.deepseek_client.requests.post")
    def test_cleans_code_blocks(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "```html\n<html><body>Test</body></html>\n```"}}]
        }
        mock_post.return_value = mock_response

        result, error = self.client.call_deepseek("Test")
        self.assertIsNone(error)
        self.assertNotIn("```", result)
        self.assertIn("<html>", result)

    @patch("app.deepseek_client.requests.post")
    def test_401_invalid_key(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        result, error = self.client.call_deepseek("Test")
        self.assertIsNone(result)
        error_text = error.lower().replace('\xe1', 'a').replace('\xe9', 'e').replace('\xed', 'i').replace('\xf3', 'o').replace('\xfa', 'u').replace('\xe7', 'c')
        self.assertTrue("invalida" in error_text or "inv" in error_text)

    @patch("app.deepseek_client.requests.post")
    def test_429_rate_limit_retry(self, mock_post):
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429

        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200
        mock_response_ok.json.return_value = {
            "choices": [{"message": {"content": "<p>OK</p>"}}]
        }

        mock_post.side_effect = [mock_response_429, mock_response_ok]

        result, error = self.client.call_deepseek("Test retry")
        self.assertIsNone(error)
        self.assertIsNotNone(result)

    @patch("app.deepseek_client.requests.post")
    def test_timeout_retry(self, mock_post):
        import requests
        mock_post.side_effect = [requests.exceptions.Timeout(), MagicMock(
            status_code=200,
            json=MagicMock(return_value={
                "choices": [{"message": {"content": "<p>After timeout</p>"}}]
            })
        )]

        result, error = self.client.call_deepseek("Test timeout")
        self.assertIsNone(error)
        self.assertIsNotNone(result)

    @patch("app.deepseek_client.requests.post")
    def test_all_retries_fail(self, mock_post):
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()

        result, error = self.client.call_deepseek("Test all fail")
        self.assertIsNone(result)
        self.assertIsNotNone(error)

    def test_tone_instructions_included(self):
        self.assertIn("infografico", self.client.TONE_INSTRUCTIONS)
        self.assertIn("resumo", self.client.TONE_INSTRUCTIONS)
        self.assertIn("newsletter", self.client.TONE_INSTRUCTIONS)
        self.assertIn("analise", self.client.TONE_INSTRUCTIONS)

    def test_system_prompt_exists(self):
        self.assertIn("CSS deve ser INLINE", self.client.SYSTEM_PROMPT_BASE)
        self.assertIn("JavaScript", self.client.SYSTEM_PROMPT_BASE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
