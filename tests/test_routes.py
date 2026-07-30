import os
import sys
import tempfile
import shutil
import unittest

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


class TestAuthRoutes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    def _register(self, username, password):
        return self.client.post("/auth/register", data={
            "username": username, "password": password, "confirm": password,
        }, follow_redirects=True)

    def _login(self, username, password):
        return self.client.post("/auth/login", data={
            "username": username, "password": password,
        }, follow_redirects=True)

    def _logout(self):
        return self.client.get("/auth/logout", follow_redirects=True)

    def test_login_page_loads(self):
        r = self.client.get("/auth/login")
        self.assertEqual(r.status_code, 200)

    def test_register_page_loads(self):
        r = self.client.get("/auth/register")
        self.assertEqual(r.status_code, 200)

    def test_register_success(self):
        r = self._register("newuser", "pass1234")
        self.assertIn(b"sucesso", r.data.lower())

    def test_register_duplicate(self):
        self._register("dupuser", "pass1234")
        r = self._register("dupuser", "pass1234")
        self.assertIn(b"existe", r.data.lower())

    def test_register_short_password(self):
        r = self._register("shortpw", "ab")
        self.assertIn(b"pelo menos 4", r.data.lower())

    def test_register_password_mismatch(self):
        r = self.client.post("/auth/register", data={
            "username": "mismatch", "password": "pass1", "confirm": "pass2",
        }, follow_redirects=True)
        self.assertIn(b"conferem", r.data.lower())

    def test_login_success(self):
        self._register("loginuser", "mypassword")
        r = self._login("loginuser", "mypassword")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Dashboard", r.data)

    def test_login_wrong_password(self):
        self._register("wpuser", "correct")
        r = self._login("wpuser", "wrongpass")
        self.assertIn(b"inv", r.data.lower())

    def test_login_nonexistent(self):
        r = self._login("ghostuser99", "whatever")
        self.assertIn(b"inv", r.data.lower())

    def test_protected_redirects(self):
        self._register("protuser", "pass1234")
        self._login("protuser", "pass1234")
        self._logout()
        r = self.client.get("/prompts")
        self.assertEqual(r.status_code, 302)


class TestAuthenticatedRoutes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    def setUp(self):
        import uuid
        self.username = f"user_{uuid.uuid4().hex[:8]}"
        self.password = "pass1234"
        self.client.post("/auth/register", data={
            "username": self.username, "password": self.password,
            "confirm": self.password,
        }, follow_redirects=True)
        self.client.post("/auth/login", data={
            "username": self.username, "password": self.password,
        }, follow_redirects=True)

    def test_dashboard_loads(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Dashboard", r.data)

    def test_dashboard_with_stats(self):
        with self.app.app_context():
            from app.models import Prompt, Schedule, ExecutionLog
            Prompt.create("P1", "c1")
            pid = Prompt.create("P2", "c2")
            sid = Schedule.create(pid, "0 0 * * *", "D", "e@e.com")
            ExecutionLog.create(sid, "success", None, 1000, "cron")

        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)

    def test_prompts_crud_flow(self):
        r = self.client.get("/prompts")
        self.assertEqual(r.status_code, 200)

        r = self.client.post("/prompts/create", data={
            "title": "ZZ-TEST-PROMPT", "content": "Conteudo",
            "tone": "resumo", "format": "html",
        }, follow_redirects=True)
        self.assertIn(b"ZZ-TEST-PROMPT", r.data)

    def test_prompts_create_no_title(self):
        r = self.client.post("/prompts/create", data={
            "title": "", "content": "Algum conteudo",
        }, follow_redirects=True)
        self.assertIn(b"obrigat", r.data.lower())

    def test_prompts_edit(self):
        with self.app.app_context():
            from app.models import Prompt
            pid = Prompt.create(f"OLD_{self.username}", "old", "infografico", "html")

        r = self.client.post(f"/prompts/{pid}/edit", data={
            "title": f"NEW_{self.username}", "content": "new",
            "tone": "analise", "format": "html", "active": "1",
        }, follow_redirects=True)
        self.assertIn(f"NEW_{self.username}".encode(), r.data)

    def test_prompts_delete(self):
        with self.app.app_context():
            from app.models import Prompt
            pid = Prompt.create(f"DEL_{self.username}", "content")

        r = self.client.post(f"/prompts/{pid}/delete", follow_redirects=True)
        self.assertEqual(r.status_code, 200)

    def test_schedules_flow(self):
        with self.app.app_context():
            from app.models import Prompt
            pid = Prompt.create(f"P4SCHED_{self.username}", "content")

        r = self.client.get("/schedules")
        self.assertEqual(r.status_code, 200)

        r = self.client.post("/schedules/create", data={
            "prompt_id": pid, "description": f"SCHED_{self.username}",
            "minute": "0", "hour": "9", "day": "*", "month": "*",
            "weekday": "*", "email_to": "test@email.com",
        }, follow_redirects=True)
        self.assertIn(f"SCHED_{self.username}".encode(), r.data)

    def test_schedules_no_email(self):
        with self.app.app_context():
            from app.models import Prompt
            pid = Prompt.create(f"PNOEMAIL_{self.username}", "content")

        r = self.client.post("/schedules/create", data={
            "prompt_id": pid, "description": "Sem email",
            "email_to": "", "minute": "0", "hour": "8",
            "day": "*", "month": "*", "weekday": "*",
        }, follow_redirects=True)
        self.assertIn(b"obrigat", r.data.lower())

    def test_schedules_toggle(self):
        with self.app.app_context():
            from app.models import Prompt, Schedule
            pid = Prompt.create(f"TOGGLE_{self.username}", "c")
            sid = Schedule.create(pid, "0 8 * * *", "T", "t@t.com")

        r = self.client.post(f"/schedules/{sid}/toggle", follow_redirects=True)
        self.assertEqual(r.status_code, 200)

        with self.app.app_context():
            s = Schedule.get_by_id(sid)
            self.assertEqual(s["active"], 0)

    def test_schedules_delete(self):
        with self.app.app_context():
            from app.models import Prompt, Schedule
            pid = Prompt.create(f"DELS_{self.username}", "c")
            sid = Schedule.create(pid, "0 10 * * *", "D", "d@d.com")

        r = self.client.post(f"/schedules/{sid}/delete", follow_redirects=True)
        self.assertEqual(r.status_code, 200)

    def test_logs_page(self):
        r = self.client.get("/logs")
        self.assertIn(r.status_code, [200, 302])

    def test_cron_status_page(self):
        r = self.client.get("/cron/status")
        self.assertIn(r.status_code, [200, 302])

    def test_cron_sync(self):
        r = self.client.post("/cron/sync", follow_redirects=True)
        self.assertIn(r.status_code, [200, 302])


if __name__ == "__main__":
    unittest.main(verbosity=2)
