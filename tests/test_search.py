import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestSearchClient(unittest.TestCase):

    def setUp(self):
        from importlib import reload
        import app.search_client
        reload(app.search_client)
        self.search = app.search_client

    def test_empty_query_returns_empty(self):
        result = self.search.web_search("", max_results=5)
        self.assertEqual(result, "")

    def test_whitespace_query_returns_empty(self):
        result = self.search.web_search("   ", max_results=5)
        self.assertEqual(result, "")

    def test_max_results_clamped(self):
        with patch.object(self.search, "_search_tavily", return_value=None):
            with patch.object(self.search, "_search_duckduckgo", return_value=None):
                result = self.search.web_search("test", max_results=0)
                self.assertEqual(result, "")
                result = self.search.web_search("test", max_results=50)
                self.assertEqual(result, "")

    @patch("app.search_client._search_tavily")
    @patch("app.search_client._search_duckduckgo")
    def test_tavily_success_no_fallback(self, mock_ddg, mock_tavily):
        mock_tavily.return_value = [
            {"title": "Noticia 1", "url": "https://exemplo.com/1", "content": "Conteudo relevante 1"},
            {"title": "Noticia 2", "url": "https://exemplo.com/2", "content": "Conteudo relevante 2"},
        ]

        result = self.search.web_search("noticias hoje", max_results=2)
        self.assertIn("[DADOS DE PESQUISA RECENTE]", result)
        self.assertIn("Noticia 1", result)
        self.assertIn("https://exemplo.com/1", result)
        self.assertIn("Noticia 2", result)
        self.assertIn("[FIM DOS DADOS DE PESQUISA]", result)
        mock_ddg.assert_not_called()

    @patch("app.search_client._search_tavily")
    @patch("app.search_client._search_duckduckgo")
    def test_tavily_fail_fallback_ddg(self, mock_ddg, mock_tavily):
        mock_tavily.return_value = None
        mock_ddg.return_value = [
            {"title": "DDG Noticia", "url": "https://ddg.com/1", "content": "Conteudo do DuckDuckGo"},
        ]

        result = self.search.web_search("test query", max_results=1)
        self.assertIn("[DADOS DE PESQUISA RECENTE]", result)
        self.assertIn("DDG Noticia", result)
        mock_ddg.assert_called_once()

    @patch("app.search_client._search_tavily")
    @patch("app.search_client._search_duckduckgo")
    def test_both_fail_return_empty(self, mock_ddg, mock_tavily):
        mock_tavily.return_value = None
        mock_ddg.return_value = None

        result = self.search.web_search("test", max_results=5)
        self.assertEqual(result, "")

    @patch("app.search_client._search_tavily")
    @patch("app.search_client._search_duckduckgo")
    def test_both_return_empty_lists(self, mock_ddg, mock_tavily):
        mock_tavily.return_value = []
        mock_ddg.return_value = []

        result = self.search.web_search("test", max_results=5)
        self.assertEqual(result, "")

    @patch.dict(os.environ, {}, clear=True)
    def test_tavily_no_api_key_fallsback(self):
        from importlib import reload
        import app.search_client
        reload(app.search_client)

        with patch.object(app.search_client, "_search_tavily", wraps=app.search_client._search_tavily) as mock_tav:
            with patch.object(app.search_client, "_search_duckduckgo", return_value=[
                {"title": "Fallback OK", "url": "https://fb.com", "content": "ok"}
            ]):
                result = app.search_client.web_search("test", max_results=1)
                self.assertIn("Fallback OK", result)

    def test_format_output_structure(self):
        results = [
            {"title": "T1", "url": "http://u1", "content": "C1"},
            {"title": "T2", "url": "http://u2", "content": "C2"},
        ]
        formatted = self.search._format_results(results)
        self.assertIn("[DADOS DE PESQUISA RECENTE]", formatted)
        self.assertIn("[FIM DOS DADOS DE PESQUISA]", formatted)
        self.assertIn("1. Titulo: T1", formatted)
        self.assertIn("2. Titulo: T2", formatted)
        self.assertIn("Fonte: http://u1", formatted)
        self.assertIn("Conteudo: C1", formatted)

    def test_format_results_missing_fields(self):
        results = [{"title": "Sem fonte"}]
        formatted = self.search._format_results(results)
        self.assertIn("Sem fonte", formatted)
        self.assertIn("Fonte:", formatted)


if __name__ == "__main__":
    unittest.main(verbosity=2)
