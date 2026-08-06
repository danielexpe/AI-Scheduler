import os
import sys
import tempfile
import shutil
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

_TMPDIR = tempfile.mkdtemp()
_TMP_DB = os.path.join(_TMPDIR, "test.db")
_orig_dir = None
_orig_path = None


def setUpModule():
    import app.models as m
    global _orig_dir, _orig_path
    _orig_dir = m.DATABASE_DIR
    _orig_path = m.DATABASE_PATH
    m.DATABASE_DIR = _TMPDIR
    m.DATABASE_PATH = _TMP_DB


def tearDownModule():
    import app.models as m
    m.DATABASE_DIR = _orig_dir
    m.DATABASE_PATH = _orig_path
    shutil.rmtree(_TMPDIR, ignore_errors=True)


class TestFullIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    def _register(self, u, p):
        return self.client.post("/auth/register", data={
            "username": u, "password": p, "confirm": p,
        }, follow_redirects=True)

    def _login(self, u, p):
        return self.client.post("/auth/login", data={
            "username": u, "password": p,
        }, follow_redirects=True)

    def test_register_login_dashboard(self):
        self._register("user1", "pass1234")
        r = self._login("user1", "pass1234")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Dashboard", r.data)

    def test_full_flow(self):
        import uuid
        u = f"flow_{uuid.uuid4().hex[:8]}"

        self._register(u, "flow1234")
        self._login(u, "flow1234")

        r = self.client.post("/prompts/create", data={
            "title": f"FINANCE_{u}",
            "content": "Resuma as noticias do mercado financeiro",
            "tone": "newsletter", "format": "html",
        }, follow_redirects=True)
        self.assertIn(f"FINANCE_{u}".encode(), r.data)

        # Get the prompt ID
        with self.app.app_context():
            from app.models import Prompt
            prompts = Prompt.get_all()
            pid = None
            for p in prompts:
                if p["title"] == f"FINANCE_{u}":
                    pid = p["id"]
                    break
        self.assertIsNotNone(pid)

        r = self.client.post("/schedules/create", data={
            "prompt_id": str(pid), "description": f"MON_{u}",
            "minute": "0", "hour": "8", "day": "*", "month": "*",
            "weekday": "1", "email_to": "user@domain.com",
        }, follow_redirects=True)
        self.assertIn(f"MON_{u}".encode(), r.data)

    def test_prompt_crud_flow(self):
        import uuid
        u = f"crud_{uuid.uuid4().hex[:8]}"

        self._register(u, "crud1234")
        self._login(u, "crud1234")

        r = self.client.post("/prompts/create", data={
            "title": f"ALPHA_{u}", "content": "a",
        }, follow_redirects=True)
        self.assertIn(f"ALPHA_{u}".encode(), r.data)

        r = self.client.post("/prompts/create", data={
            "title": f"BETA_{u}", "content": "b",
        }, follow_redirects=True)
        self.assertIn(f"BETA_{u}".encode(), r.data)

        with self.app.app_context():
            from app.models import Prompt
            prompts = Prompt.get_all()
            pid_a = None
            pid_b = None
            for p in prompts:
                if p["title"] == f"ALPHA_{u}":
                    pid_a = p["id"]
                if p["title"] == f"BETA_{u}":
                    pid_b = p["id"]

        r = self.client.post(f"/prompts/{pid_a}/edit", data={
            "title": f"ALPHA_MOD_{u}", "content": "updated",
            "tone": "analise", "format": "html", "active": "1",
        }, follow_redirects=True)
        self.assertIn(f"ALPHA_MOD_{u}".encode(), r.data)

        r = self.client.post(f"/prompts/{pid_b}/delete", follow_redirects=True)
        self.assertNotIn(f"BETA_{u}".encode(), r.data)


class TestExecutorIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.__enter__()

    def tearDown(self):
        self.ctx.__exit__(None, None, None)

    @patch.dict(os.environ, {
        "DEEPSEEK_API_KEY": "sk-test", "GMAIL_USER": "t@gmail.com",
        "GMAIL_APP_PASSWORD": "test-pass",
    })
    @patch("app.executor.send_email")
    @patch("app.executor.call_deepseek")
    def test_run_schedule_success(self, mock_deepseek, mock_email):
        mock_deepseek.return_value = (
            "<html><body><h1>Report</h1><p>This is a long enough response for testing purposes.</p><p>With multiple paragraphs to make sure it exceeds 50 chars.</p></body></html>",
            None
        )
        mock_email.return_value = (True, None)

        from app.models import Prompt, Schedule
        pid = Prompt.create("Test P", "content")
        sid = Schedule.create(pid, "0 0 * * *", "Test", "t@t.com")

        from app.executor import run_schedule
        duration, html, error = run_schedule(schedule_id=sid)

        self.assertIsNone(error)
        self.assertIsNotNone(html)
        self.assertGreaterEqual(duration, 0)

    @patch.dict(os.environ, {
        "DEEPSEEK_API_KEY": "sk-test", "GMAIL_USER": "t@gmail.com",
        "GMAIL_APP_PASSWORD": "test-pass",
    })
    @patch("app.executor.send_email")
    @patch("app.executor.call_deepseek")
    def test_run_schedule_deepseek_error(self, mock_deepseek, mock_email):
        mock_deepseek.return_value = (None, "API Error")

        from app.models import Prompt, Schedule
        pid = Prompt.create("Test P2", "content")
        sid = Schedule.create(pid, "0 0 * * *", "Test2", "t2@t.com")

        from app.executor import run_schedule
        duration, html, error = run_schedule(schedule_id=sid)

        self.assertIsNotNone(error)
        self.assertIsNone(html)

    @patch.dict(os.environ, {
        "DEEPSEEK_API_KEY": "sk-test", "GMAIL_USER": "t@gmail.com",
        "GMAIL_APP_PASSWORD": "test-pass",
    })
    @patch("app.executor.send_email")
    @patch("app.executor.call_deepseek")
    def test_run_manual_success(self, mock_deepseek, mock_email):
        mock_deepseek.return_value = (
            "<html><body><h1>Manual Report</h1><p>Content for manual execution test with sufficient length.</p></body></html>",
            None
        )
        mock_email.return_value = (True, None)

        from app.executor import run_schedule
        duration, html, error = run_schedule(
            schedule_id=None, email_to="manual@test.com",
            prompt_content="Manual prompt", prompt_tone="resumo"
        )

        self.assertIsNone(error)
        self.assertIsNotNone(html)
        self.assertGreaterEqual(duration, 0)

    @patch.dict(os.environ, {
        "DEEPSEEK_API_KEY": "sk-test", "GMAIL_USER": "t@gmail.com",
        "GMAIL_APP_PASSWORD": "test-pass",
    })
    @patch("app.executor.send_email")
    @patch("app.executor.call_deepseek")
    @patch("app.search_client.web_search")
    def test_debug_mode_section_present(self, mock_search, mock_deepseek, mock_email):
        mock_search.return_value = "[DADOS DE PESQUISA RECENTE]\nResultados mockados de busca\n[FIM DOS DADOS DE PESQUISA]"
        mock_deepseek.return_value = (
            "<html><body><h1>Debug Test</h1><p>Long enough response for testing debug mode with sufficient text.</p></body></html>",
            None
        )
        mock_email.return_value = (True, None)

        from app.models import Prompt, Schedule
        pid = Prompt.create("Debug P", "conteudo do prompt", debug_mode=1, enable_search=1,
                            search_max_results=3)
        sid = Schedule.create(pid, "0 0 * * *", "Debug S", "t@t.com")

        from app.executor import run_schedule
        duration, html, error = run_schedule(schedule_id=sid)

        self.assertIsNone(error)
        self.assertIsNotNone(html)
        self.assertIn("=== DEBUG - Trilha do Prompt ===", html)
        self.assertIn("--- System Prompt", html)
        self.assertIn("--- User Prompt", html)
        self.assertIn("=== FIM DEBUG ===", html)
        self.assertIn("Resultados mockados de busca", html)
        self.assertIn("[DADOS DE PESQUISA RECENTE]", html)

    @patch.dict(os.environ, {
        "DEEPSEEK_API_KEY": "sk-test", "GMAIL_USER": "t@gmail.com",
        "GMAIL_APP_PASSWORD": "test-pass",
    })
    @patch("app.executor.send_email")
    @patch("app.executor.call_deepseek")
    @patch("app.search_client.web_search")
    def test_debug_mode_no_search_results(self, mock_search, mock_deepseek, mock_email):
        mock_search.return_value = ""
        mock_deepseek.return_value = (
            "<html><body><h1>No Search</h1><p>Long enough response for testing debug mode without search results.</p></body></html>",
            None
        )
        mock_email.return_value = (True, None)

        from app.models import Prompt, Schedule
        pid = Prompt.create("Debug NoSrch", "conteudo", debug_mode=1, enable_search=1)
        sid = Schedule.create(pid, "0 0 * * *", "Debug NS", "t@t.com")

        from app.executor import run_schedule
        duration, html, error = run_schedule(schedule_id=sid)

        self.assertIsNone(error)
        self.assertIsNotNone(html)
        self.assertIn("=== DEBUG - Trilha do Prompt ===", html)
        self.assertIn("sem resultados", html)

    @patch.dict(os.environ, {
        "DEEPSEEK_API_KEY": "sk-test", "GMAIL_USER": "t@gmail.com",
        "GMAIL_APP_PASSWORD": "test-pass",
    })
    @patch("app.executor.send_email")
    @patch("app.executor.call_deepseek")
    @patch("app.search_client.web_search")
    def test_debug_mode_search_disabled(self, mock_search, mock_deepseek, mock_email):
        mock_deepseek.return_value = (
            "<html><body><h1>Search Off</h1><p>Long enough response for testing debug mode with search disabled entirely.</p></body></html>",
            None
        )
        mock_email.return_value = (True, None)

        from app.models import Prompt, Schedule
        pid = Prompt.create("Debug Off", "conteudo", debug_mode=1, enable_search=0)
        sid = Schedule.create(pid, "0 0 * * *", "Debug Off", "t@t.com")

        from app.executor import run_schedule
        duration, html, error = run_schedule(schedule_id=sid)

        self.assertIsNone(error)
        self.assertIsNotNone(html)
        self.assertIn("=== DEBUG - Trilha do Prompt ===", html)
        self.assertIn("Busca Web: Desativada", html)
        self.assertNotIn("[DADOS DE PESQUISA RECENTE]", html)
        mock_search.assert_not_called()

    @patch.dict(os.environ, {
        "DEEPSEEK_API_KEY": "sk-test", "GMAIL_USER": "t@gmail.com",
        "GMAIL_APP_PASSWORD": "test-pass",
    })
    @patch("app.executor.send_email")
    @patch("app.executor.call_deepseek")
    def test_debug_mode_disabled_no_section(self, mock_deepseek, mock_email):
        mock_deepseek.return_value = (
            "<html><body><h1>No Debug</h1><p>Long enough response for testing without debug mode enabled at all.</p></body></html>",
            None
        )
        mock_email.return_value = (True, None)

        from app.models import Prompt, Schedule
        pid = Prompt.create("NoDebug P", "conteudo", debug_mode=0)
        sid = Schedule.create(pid, "0 0 * * *", "NoDebug S", "t@t.com")

        from app.executor import run_schedule
        duration, html, error = run_schedule(schedule_id=sid)

        self.assertIsNone(error)
        self.assertIsNotNone(html)
        self.assertNotIn("=== DEBUG - Trilha do Prompt ===", html)
        self.assertNotIn("--- System Prompt", html)
        self.assertNotIn("--- User Prompt", html)

    @patch.dict(os.environ, {
        "DEEPSEEK_API_KEY": "sk-test", "GMAIL_USER": "t@gmail.com",
        "GMAIL_APP_PASSWORD": "test-pass",
    })
    @patch("app.executor.send_email")
    @patch("app.executor.call_deepseek")
    @patch("app.search_client.web_search")
    def test_debug_user_prompt_matches_deepseek(self, mock_search, mock_deepseek, mock_email):
        mock_search.return_value = "[DADOS DE PESQUISA RECENTE]\nBusca mock para teste\n[FIM DOS DADOS DE PESQUISA]"
        mock_deepseek.return_value = (
            "<html><body><h1>Match Test</h1><p>Long enough response for testing prompt matching with sufficient length.</p></body></html>",
            None
        )
        mock_email.return_value = (True, None)

        from app.models import Prompt, Schedule
        pid = Prompt.create("Match P", "meu prompt de teste", debug_mode=1, enable_search=1)
        sid = Schedule.create(pid, "0 0 * * *", "Match S", "t@t.com")

        from app.executor import run_schedule
        duration, html, error = run_schedule(schedule_id=sid)

        self.assertIsNone(error)
        self.assertIsNotNone(html)

        mock_deepseek.assert_called_once()
        sent_prompt = mock_deepseek.call_args[0][0]

        self.assertIn("meu prompt de teste", sent_prompt)
        self.assertIn("Busca mock para teste", sent_prompt)
        self.assertIn(sent_prompt, html)

    @patch.dict(os.environ, {
        "DEEPSEEK_API_KEY": "sk-test", "GMAIL_USER": "t@gmail.com",
        "GMAIL_APP_PASSWORD": "test-pass",
    })
    @patch("app.executor.send_email")
    @patch("app.executor.call_deepseek")
    @patch("app.search_client.web_search")
    def test_debug_system_prompt_includes_tone_and_search(self, mock_search, mock_deepseek, mock_email):
        mock_search.return_value = ""
        mock_deepseek.return_value = (
            "<html><body><h1>Sys Test</h1><p>Long enough response for testing system prompt content in debug section.</p></body></html>",
            None
        )
        mock_email.return_value = (True, None)

        from app.models import Prompt, Schedule
        pid = Prompt.create("Sys P", "conteudo", tone="analise", debug_mode=1, enable_search=1)
        sid = Schedule.create(pid, "0 0 * * *", "Sys S", "t@t.com")

        from app.executor import run_schedule
        duration, html, error = run_schedule(schedule_id=sid)

        self.assertIsNone(error)
        self.assertIn("=== DEBUG - Trilha do Prompt ===", html)
        self.assertIn("Tom/Estilo: analise", html)
        self.assertIn("tabelas comparativas", html.lower())

    @patch.dict(os.environ, {
        "DEEPSEEK_API_KEY": "sk-test", "GMAIL_USER": "t@gmail.com",
        "GMAIL_APP_PASSWORD": "test-pass",
    })
    @patch("app.executor.send_email")
    @patch("app.executor.call_deepseek")
    @patch("app.search_client.web_search")
    def test_debug_mode_with_search_error_graceful(self, mock_search, mock_deepseek, mock_email):
        mock_search.side_effect = ConnectionError("Falha de rede simulada")
        mock_deepseek.return_value = (
            "<html><body><h1>Graceful</h1><p>Long enough response for testing graceful handling of search errors.</p></body></html>",
            None
        )
        mock_email.return_value = (True, None)

        from app.models import Prompt, Schedule
        pid = Prompt.create("Graceful P", "conteudo", debug_mode=1, enable_search=1)
        sid = Schedule.create(pid, "0 0 * * *", "Graceful S", "t@t.com")

        from app.executor import run_schedule
        duration, html, error = run_schedule(schedule_id=sid)

        self.assertIsNone(error)
        self.assertIsNotNone(html)
        self.assertIn("=== DEBUG - Trilha do Prompt ===", html)
        self.assertIn("sem resultados", html)

    @patch.dict(os.environ, {
        "DEEPSEEK_API_KEY": "sk-test", "GMAIL_USER": "t@gmail.com",
        "GMAIL_APP_PASSWORD": "test-pass",
    })
    @patch("app.executor.send_email")
    @patch("app.executor.call_deepseek")
    @patch("app.search_client.web_search")
    def test_debug_manual_execution_with_search(self, mock_search, mock_deepseek, mock_email):
        mock_search.return_value = "[DADOS DE PESQUISA RECENTE]\nBusca manual\n[FIM DOS DADOS DE PESQUISA]"
        mock_deepseek.return_value = (
            "<html><body><h1>Manual Debug</h1><p>Long enough response for testing manual execution with debug mode.</p></body></html>",
            None
        )
        mock_email.return_value = (True, None)

        from app.models import Prompt
        pid = Prompt.create("Manual P", "conteudo manual", debug_mode=1, enable_search=1,
                            search_max_results=2)

        from app.executor import run_schedule
        duration, html, error = run_schedule(
            schedule_id=None, prompt_id_override=pid,
            email_to="manual@test.com",
            prompt_content="conteudo manual", prompt_tone="resumo"
        )

        self.assertIsNone(error)
        self.assertIsNotNone(html)
        self.assertIn("=== DEBUG - Trilha do Prompt ===", html)
        self.assertIn("Busca manual", html)
        self.assertIn("conteudo manual", html)
        mock_email.assert_called_once()
        email_body = mock_email.call_args[0][2]
        self.assertIn("=== DEBUG - Trilha do Prompt ===", email_body)
        self.assertIn("Busca manual", email_body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
