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


if __name__ == "__main__":
    unittest.main(verbosity=2)
