import os
import sys
import tempfile
import sqlite3
import unittest
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

_orig_db_dir = None
_orig_db_path = None
_tmpdir = None


class TestModelsBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        global _orig_db_dir, _orig_db_path, _tmpdir

        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True

        _tmpdir = tempfile.mkdtemp()
        import app.models as m
        _orig_db_dir = m.DATABASE_DIR
        _orig_db_path = m.DATABASE_PATH
        m.DATABASE_DIR = _tmpdir
        m.DATABASE_PATH = os.path.join(_tmpdir, "test.db")

        cls._db_path = m.DATABASE_PATH

    @classmethod
    def tearDownClass(cls):
        import app.models as m
        m.DATABASE_DIR = _orig_db_dir
        m.DATABASE_PATH = _orig_db_path
        shutil.rmtree(_tmpdir, ignore_errors=True)

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.__enter__()
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL, content TEXT NOT NULL,
                tone TEXT DEFAULT 'infografico', format TEXT DEFAULT 'html',
                active BOOLEAN DEFAULT 1,
                enable_search BOOLEAN DEFAULT 1,
                search_max_results INTEGER DEFAULT 5,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_id INTEGER, cron_expr TEXT NOT NULL,
                description TEXT, email_to TEXT NOT NULL,
                active BOOLEAN DEFAULT 1, last_run_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                schedule_type TEXT DEFAULT 'ai',
                static_content TEXT,
                static_is_html INTEGER DEFAULT 0,
                static_subject TEXT,
                command_text TEXT,
                FOREIGN KEY (prompt_id) REFERENCES prompts(id));
            CREATE TABLE IF NOT EXISTS execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'success',
                error_message TEXT, duration_ms INTEGER,
                triggered_by TEXT DEFAULT 'cron',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (schedule_id) REFERENCES schedules(id));
        """)
        conn.commit()
        conn.close()

    def tearDown(self):
        conn = sqlite3.connect(self._db_path)
        conn.execute("DELETE FROM execution_logs")
        conn.execute("DELETE FROM schedules")
        conn.execute("DELETE FROM prompts")
        conn.execute("DELETE FROM users")
        conn.commit()
        conn.close()
        self.ctx.__exit__(None, None, None)


class TestDatabaseCreation(TestModelsBase):

    def test_database_has_tables(self):
        conn = sqlite3.connect(self._db_path)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        self.assertIn("users", tables)
        self.assertIn("prompts", tables)
        self.assertIn("schedules", tables)
        self.assertIn("execution_logs", tables)


class TestUserModel(TestModelsBase):

    def test_create_user(self):
        from werkzeug.security import generate_password_hash
        from app.models import User
        uid = User.create("testuser", generate_password_hash("secret"))
        self.assertIsNotNone(uid)
        self.assertGreater(uid, 0)

    def test_get_by_username(self):
        from werkzeug.security import generate_password_hash
        from app.models import User
        User.create("alice", generate_password_hash("pass1"))
        user = User.get_by_username("alice")
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "alice")

    def test_get_by_username_not_found(self):
        from app.models import User
        user = User.get_by_username("nonexistent_user_xyz")
        self.assertIsNone(user)

    def test_get_by_id(self):
        from werkzeug.security import generate_password_hash
        from app.models import User
        uid = User.create("bob", generate_password_hash("pass2"))
        user = User.get_by_id(uid)
        self.assertEqual(user["username"], "bob")

    def test_duplicate_username(self):
        from werkzeug.security import generate_password_hash
        from app.models import User
        User.create("charlie", generate_password_hash("pass3"))
        with self.assertRaises(Exception):
            User.create("charlie", generate_password_hash("pass4"))


class TestPromptModel(TestModelsBase):

    def test_create_prompt(self):
        from app.models import Prompt
        pid = Prompt.create("Titulo", "Conteudo", "resumo", "html")
        self.assertGreater(pid, 0)

    def test_get_all(self):
        from app.models import Prompt
        Prompt.create("P1", "C1", "infografico", "html")
        Prompt.create("P2", "C2", "newsletter", "html")
        prompts = Prompt.get_all()
        self.assertEqual(len(prompts), 2)

    def test_get_by_id(self):
        from app.models import Prompt
        pid = Prompt.create("Find Me", "content")
        prompt = Prompt.get_by_id(pid)
        self.assertEqual(prompt["title"], "Find Me")

    def test_update(self):
        from app.models import Prompt
        pid = Prompt.create("Old", "old content", "resumo", "html")
        Prompt.update(pid, "New", "new content", "analise", "html", 1)
        updated = Prompt.get_by_id(pid)
        self.assertEqual(updated["title"], "New")
        self.assertEqual(updated["tone"], "analise")

    def test_delete(self):
        from app.models import Prompt
        pid = Prompt.create("Delete Me", "content")
        Prompt.delete(pid)
        self.assertIsNone(Prompt.get_by_id(pid))


class TestScheduleModel(TestModelsBase):

    def test_create_schedule(self):
        from app.models import Prompt, Schedule
        pid = Prompt.create("P", "c")
        sid = Schedule.create(pid, "0 8 * * 3", "Wed 8AM", "test@test.com")
        self.assertGreater(sid, 0)

    def test_get_all_with_join(self):
        from app.models import Prompt, Schedule
        pid = Prompt.create("Prompt A", "content")
        Schedule.create(pid, "0 9 * * 1", "Mon 9AM", "a@a.com")
        schedules = Schedule.get_all()
        self.assertEqual(len(schedules), 1)
        self.assertEqual(schedules[0]["prompt_title"], "Prompt A")

    def test_get_by_id(self):
        from app.models import Prompt, Schedule
        pid = Prompt.create("P", "c", tone="newsletter")
        sid = Schedule.create(pid, "*/15 * * * *", "Every 15 min", "b@b.com")
        s = Schedule.get_by_id(sid)
        self.assertEqual(s["prompt_title"], "P")
        self.assertEqual(s["prompt_tone"], "newsletter")
        self.assertEqual(s["email_to"], "b@b.com")

    def test_toggle(self):
        from app.models import Prompt, Schedule
        pid = Prompt.create("P", "c")
        sid = Schedule.create(pid, "0 0 * * *", "Daily", "t@t.com")
        Schedule.toggle(sid)
        s = Schedule.get_by_id(sid)
        self.assertEqual(s["active"], 0)
        Schedule.toggle(sid)
        s = Schedule.get_by_id(sid)
        self.assertEqual(s["active"], 1)

    def test_update_last_run(self):
        from app.models import Prompt, Schedule
        pid = Prompt.create("P", "c")
        sid = Schedule.create(pid, "0 0 * * *", "Daily", "t@t.com")
        s = Schedule.get_by_id(sid)
        self.assertIsNone(s["last_run_at"])
        Schedule.update_last_run(sid)
        s = Schedule.get_by_id(sid)
        self.assertIsNotNone(s["last_run_at"])

    def test_get_active_schedules(self):
        from app.models import Prompt, Schedule
        pid1 = Prompt.create("P1", "c1")
        Prompt.create("P2 Inactive", "c2", active=0)
        pid3 = Prompt.create("P3", "c3")
        Schedule.create(pid1, "0 8 * * 1", "Active sched", "a@a.com")
        Schedule.create(pid3, "0 8 * * 3", "Inactive sched", "c@c.com")
        active = Schedule.get_active_schedules()
        self.assertEqual(len(active), 2)

    def test_delete_schedule(self):
        from app.models import Prompt, Schedule
        pid = Prompt.create("P", "c")
        sid = Schedule.create(pid, "0 0 * * *", "D", "d@d.com")
        Schedule.delete(sid)
        self.assertIsNone(Schedule.get_by_id(sid))


class TestExecutionLogModel(TestModelsBase):

    def test_create_log(self):
        from app.models import Prompt, Schedule, ExecutionLog
        pid = Prompt.create("P", "c")
        sid = Schedule.create(pid, "0 0 * * *", "D", "e@e.com")
        lid = ExecutionLog.create(sid, "success", None, 1500, "cron")
        self.assertGreater(lid, 0)

    def test_get_recent(self):
        from app.models import Prompt, Schedule, ExecutionLog
        pid = Prompt.create("P", "c")
        sid = Schedule.create(pid, "0 0 * * *", "D", "e@e.com")
        ExecutionLog.create(sid, "success", None, 1000, "cron")
        ExecutionLog.create(sid, "error", "timeout", 3000, "manual")
        ExecutionLog.create(sid, "success", None, 500, "cron")
        logs = ExecutionLog.get_recent(limit=2)
        self.assertEqual(len(logs), 2)

    def test_get_recent_by_schedule(self):
        from app.models import Prompt, Schedule, ExecutionLog
        pid = Prompt.create("P", "c")
        sid1 = Schedule.create(pid, "0 0 * * *", "S1", "s1@t.com")
        sid2 = Schedule.create(pid, "0 0 * * *", "S2", "s2@t.com")
        ExecutionLog.create(sid1, "success", None, 1000, "cron")
        ExecutionLog.create(sid2, "error", "fail", 2000, "manual")
        logs = ExecutionLog.get_recent(schedule_id=sid1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["schedule_desc"], "S1")

    def test_get_stats(self):
        from app.models import Prompt, Schedule, ExecutionLog
        pid1 = Prompt.create("P1", "c1")
        Prompt.create("P2", "c2", active=0)
        sid = Schedule.create(pid1, "0 0 * * *", "D", "e@e.com")
        ExecutionLog.create(sid, "success", None, 1000, "cron")
        ExecutionLog.create(sid, "error", "err", 2000, "cron")
        stats = ExecutionLog.get_stats()
        self.assertEqual(stats["total_prompts"], 2)
        self.assertEqual(stats["active_prompts"], 1)
        self.assertEqual(stats["total_schedules"], 1)
        self.assertEqual(stats["active_schedules"], 1)
        self.assertEqual(stats["success_rate"], 50.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
