import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestCronManagerNative(unittest.TestCase):
    """Testes em modo nativo (com crontab disponivel)."""

    def setUp(self):
        self._patches = [
            patch.dict(os.environ, {}, clear=True),
            patch("os.path.exists", return_value=True),
        ]
        for p in self._patches:
            p.start()
        from importlib import reload
        import app.cron_manager
        reload(app.cron_manager)
        self.cm = app.cron_manager

    def tearDown(self):
        for p in reversed(self._patches):
            p.stop()

    @patch("crontab.CronTab")
    def test_add_cron_job(self, mock_cls):
        mock_cron = MagicMock()
        mock_cron.__iter__.return_value = []
        mock_cls.return_value = mock_cron

        self.assertTrue(self.cm.add_cron_job(42, "0 8 * * 3", "Wed 8AM"))
        mock_cron.new.assert_called_once()
        mock_cron.write.assert_called_once()

    def test_add_cron_invalid_expr(self):
        with self.assertRaises(ValueError):
            self.cm.add_cron_job(1, "invalid", "bad")

    @patch("crontab.CronTab")
    def test_remove_cron_job(self, mock_cls):
        mock_job = MagicMock()
        mock_job.comment = "AI_SCHEDULER:5 | desc"
        mock_cron = MagicMock()
        mock_cron.__iter__.return_value = [mock_job]
        mock_cls.return_value = mock_cron

        self.assertTrue(self.cm.remove_cron_job(5))
        mock_cron.remove.assert_called_once_with(mock_job)

    @patch("crontab.CronTab")
    def test_remove_not_found(self, mock_cls):
        mock_cron = MagicMock()
        mock_cron.__iter__.return_value = []
        mock_cls.return_value = mock_cron
        self.assertFalse(self.cm.remove_cron_job(999))

    @patch("crontab.CronTab")
    def test_get_status(self, mock_cls):
        mock_job = MagicMock()
        mock_job.comment = "AI_SCHEDULER:1 | test"
        mock_job.slices = "0 8 * * 3"
        mock_job.command = "/path/run.sh 1"
        mock_job.enabled = True
        mock_cron = MagicMock()
        mock_cron.__iter__.return_value = [mock_job]
        mock_cls.return_value = mock_cron

        entries = self.cm.get_cron_status()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["schedule"], "0 8 * * 3")

    @patch("crontab.CronTab")
    def test_get_status_empty(self, mock_cls):
        mock_cron = MagicMock()
        mock_cron.__iter__.return_value = []
        mock_cls.return_value = mock_cron
        self.assertEqual(len(self.cm.get_cron_status()), 0)

    def test_comment_marker(self):
        self.assertEqual(self.cm.COMMENT_MARKER, "AI_SCHEDULER")

    @patch("app.models.Schedule")
    @patch("crontab.CronTab")
    def test_sync_all(self, mock_cls, mock_sched):
        mock_job = MagicMock()
        mock_job.comment = "AI_SCHEDULER:99 | old"
        mock_cron = MagicMock()
        mock_cron.__iter__.return_value = [mock_job]
        mock_cls.return_value = mock_cron

        mock_sched.get_active_schedules.return_value = [
            {"id": 1, "cron_expr": "0 8 * * 1", "description": "S1"},
            {"id": 2, "cron_expr": "0 9 * * 2", "description": "S2"},
        ]
        r = self.cm.sync_all_schedules()
        self.assertEqual(r["removed"], 1)

    def test_not_docker_mode(self):
        self.assertFalse(self.cm._is_docker())


class TestCronManagerDocker(unittest.TestCase):
    """Testes em modo Docker (sem crontab)."""

    def setUp(self):
        self._patches = [
            patch.dict(os.environ, {"CRON_MODE": "docker"}),
        ]
        for p in self._patches:
            p.start()
        from importlib import reload
        import app.cron_manager
        reload(app.cron_manager)
        self.cm = app.cron_manager

    def tearDown(self):
        for p in reversed(self._patches):
            p.stop()

    def test_is_docker_mode(self):
        self.assertTrue(self.cm._is_docker())

    def test_add_returns_true(self):
        self.assertTrue(self.cm.add_cron_job(1, "0 0 * * *", "test"))

    def test_remove_returns_true(self):
        self.assertTrue(self.cm.remove_cron_job(99))

    def test_update_returns_true(self):
        self.assertTrue(self.cm.update_cron_job(1, "0 5 * * *"))

    def test_sync_returns_docker_result(self):
        from app import create_app
        app = create_app()
        with app.app_context():
            r = self.cm.sync_all_schedules()
        self.assertTrue(r.get("docker_mode"))

    def test_get_status_from_db(self):
        from app import create_app
        app = create_app()
        with app.app_context():
            from app.models import Prompt, Schedule
            pid = Prompt.create("P docker", "c")
            Schedule.create(pid, "0 9 * * *", "Docker sched", "d@d.com")
            entries = self.cm.get_cron_status()
            self.assertGreaterEqual(len(entries), 1)
            self.assertTrue(entries[0].get("docker_mode"))


class TestCronValidation(unittest.TestCase):

    def test_valid(self):
        for e in ["0 8 * * 3", "*/15 * * * *", "0 0 1 * *", "30 14 * * 1-5"]:
            self.assertEqual(len(e.strip().split()), 5)

    def test_invalid(self):
        for e in ["", "*", "* * *", "* * * *"]:
            self.assertNotEqual(len(e.strip().split()), 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
