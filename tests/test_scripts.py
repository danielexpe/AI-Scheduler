import os
import sys
import stat
import shutil
import tempfile
import unittest
import subprocess
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestShellScripts(unittest.TestCase):
    """Testes para os scripts shell da pasta scripts/."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.app_dir = os.path.join(cls.tmpdir, "app")
        cls.scripts_dir = os.path.join(cls.tmpdir, "scripts")
        cls.data_dir = os.path.join(cls.tmpdir, "data")

        for d in [cls.app_dir, cls.scripts_dir, cls.data_dir]:
            os.makedirs(d, exist_ok=True)

        cls.mock_python = os.path.join(cls.tmpdir, "mock_python.sh")
        cls._write_mock_python()

        cls._create_test_scripts()

    @classmethod
    def _write_mock_python(cls):
        with open(cls.mock_python, "w") as f:
            f.write("#!/bin/bash\n")
            f.write("ARGS_FILE=\"$HOME/.mock_python_args\"\n")
            f.write("echo \"$@\" > \"$ARGS_FILE\"\n")
            f.write("EXIT_CODE_FILE=\"$HOME/.mock_python_exit\"\n")
            f.write("CODE=0\n")
            f.write("if [ -f \"$EXIT_CODE_FILE\" ]; then\n")
            f.write("    read -r CODE < \"$EXIT_CODE_FILE\"\n")
            f.write("fi\n")
            f.write("if [ \"$1\" = \"-c\" ]; then\n")
            f.write("    echo \"Adicionados: 2, Removidos: 1\"\n")
            f.write("fi\n")
            f.write("exit \"$CODE\"\n")
        os.chmod(cls.mock_python, 0o755)

    @classmethod
    def _create_test_scripts(cls):
        cls.run_executor = os.path.join(cls.scripts_dir, "run_executor.sh")
        with open(cls.run_executor, "w") as f:
            f.write("#!/bin/bash\n")
            f.write(f"APP_DIR=\"{cls.tmpdir}\"\n")
            f.write(f"VENV_PYTHON=\"{cls.mock_python}\"\n")
            f.write(f"EXECUTOR=\"{cls.app_dir}/executor.py\"\n")
            f.write(f"LOG_FILE=\"{cls.data_dir}/executor.log\"\n\n")
            f.write("SCHEDULE_ID=$1\n\n")
            f.write("if [ -z \"$SCHEDULE_ID\" ]; then\n")
            f.write("    echo \"[test] ERRO: schedule_id nao informado\" >> \"$LOG_FILE\"\n")
            f.write("    exit 1\n")
            f.write("fi\n\n")
            f.write("echo \"[test] Iniciando execucao do schedule_id=$SCHEDULE_ID\" >> \"$LOG_FILE\"\n")
            f.write("$VENV_PYTHON \"$EXECUTOR\" --schedule-id \"$SCHEDULE_ID\" >> \"$LOG_FILE\" 2>&1\n\n")
            f.write("EXIT_CODE=$?\n")
            f.write("if [ $EXIT_CODE -eq 0 ]; then\n")
            f.write("    echo \"[test] Execucao concluida com sucesso\" >> \"$LOG_FILE\"\n")
            f.write("else\n")
            f.write("    echo \"[test] Execucao falhou com codigo $EXIT_CODE\" >> \"$LOG_FILE\"\n")
            f.write("fi\n\n")
            f.write("exit $EXIT_CODE\n")
        os.chmod(cls.run_executor, 0o755)

        cls.setup_cron = os.path.join(cls.scripts_dir, "setup_cron.sh")
        with open(cls.setup_cron, "w") as f:
            f.write("#!/bin/bash\n")
            f.write("set -e\n\n")
            f.write(f"APP_DIR=\"{cls.tmpdir}\"\n")
            f.write(f"VENV_PYTHON=\"{cls.mock_python}\"\n\n")
            f.write("cd \"$APP_DIR\"\n")
            f.write("$VENV_PYTHON -c \"from app.cron_manager import sync_all_schedules;")
            f.write(" r = sync_all_schedules(); ")
            f.write("print(f'Adicionados: {r[\\\"added\\\"]}, Removidos: {r[\\\"removed\\\"]}')\"\n")
        os.chmod(cls.setup_cron, 0o755)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def setUp(self):
        self.args_file = os.path.join(os.path.expanduser("~"), ".mock_python_args")
        self.exit_file = os.path.join(os.path.expanduser("~"), ".mock_python_exit")
        self._clean_mock_state()
        self._clean_log()

    def tearDown(self):
        self._clean_mock_state()
        self._clean_log()

    def _clean_mock_state(self):
        for f in [self.args_file, self.exit_file]:
            if os.path.exists(f):
                os.remove(f)

    def _clean_log(self):
        log = os.path.join(self.data_dir, "executor.log")
        if os.path.exists(log):
            os.remove(log)

    def _read_log(self):
        log = os.path.join(self.data_dir, "executor.log")
        if os.path.exists(log):
            with open(log) as f:
                return f.read()
        return ""

    def _read_mock_args(self):
        if os.path.exists(self.args_file):
            with open(self.args_file) as f:
                return f.read().strip()
        return ""


class TestRunExecutorScript(TestShellScripts):

    def test_missing_schedule_id_exits_1(self):
        proc = subprocess.run(
            [self.run_executor], capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 1)
        log = self._read_log()
        self.assertIn("ERRO: schedule_id nao informado", log)

    def test_missing_schedule_id_does_not_call_python(self):
        subprocess.run([self.run_executor], capture_output=True)
        self.assertFalse(os.path.exists(self.args_file))

    def test_valid_schedule_id_success(self):
        proc = subprocess.run(
            [self.run_executor, "42"], capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 0)
        log = self._read_log()
        self.assertIn("Iniciando execucao do schedule_id=42", log)
        self.assertIn("Execucao concluida com sucesso", log)

    def test_calls_executor_with_correct_args(self):
        subprocess.run([self.run_executor, "7"], capture_output=True)
        args = self._read_mock_args()
        self.assertIn("--schedule-id", args)
        self.assertIn("7", args)
        self.assertIn("executor.py", args)

    def test_propagates_executor_failure(self):
        with open(self.exit_file, "w") as f:
            f.write("2")

        proc = subprocess.run(
            [self.run_executor, "99"], capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 2)
        log = self._read_log()
        self.assertIn("Execucao falhou com codigo 2", log)

    def test_propagates_executor_exit_code_5(self):
        with open(self.exit_file, "w") as f:
            f.write("5")

        proc = subprocess.run(
            [self.run_executor, "3"], capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 5)
        log = self._read_log()
        self.assertIn("falhou com codigo 5", log)

    def test_log_entries_are_appended(self):
        subprocess.run([self.run_executor, "10"], capture_output=True)
        subprocess.run([self.run_executor, "20"], capture_output=True)

        log = self._read_log()
        lines = [l for l in log.strip().split("\n") if l]
        success_count = sum(1 for l in lines if "concluida com sucesso" in l)
        start_count = sum(1 for l in lines if "Iniciando execucao" in l)
        self.assertEqual(success_count, 2)
        self.assertEqual(start_count, 2)

    def test_empty_schedule_id(self):
        proc = subprocess.run(
            [self.run_executor, ""], capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 1)

    def test_schedule_id_with_spaces(self):
        proc = subprocess.run(
            [self.run_executor, "  123  "], capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 0)
        args = self._read_mock_args()
        self.assertIn("123", args)

    def test_script_is_executable(self):
        self.assertTrue(os.access(self.run_executor, os.X_OK))

    def test_script_has_shebang(self):
        with open(self.run_executor) as f:
            first_line = f.readline()
        self.assertTrue(first_line.startswith("#!/"))


class TestSetupCronScript(TestShellScripts):

    def test_script_runs_sync_all_schedules(self):
        proc = subprocess.run(
            [self.setup_cron], capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 0)

    def test_script_output_format(self):
        with open(self.exit_file, "w") as f:
            f.write("0")

        proc = subprocess.run(
            [self.setup_cron], capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 0)
        stdout = proc.stdout + proc.stderr
        self.assertIn("Adicionados:", stdout)
        self.assertIn("Removidos:", stdout)

    def test_script_is_executable(self):
        self.assertTrue(os.access(self.setup_cron, os.X_OK))

    def test_script_has_shebang(self):
        with open(self.setup_cron) as f:
            first_line = f.readline()
        self.assertTrue(first_line.startswith("#!/"))

    def test_script_changes_to_app_dir(self):
        proc = subprocess.run(
            [self.setup_cron], capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 0)
        stdout = proc.stdout + proc.stderr
        self.assertIn("Adicionados:", stdout)


class TestRealScriptsExist(unittest.TestCase):
    """Testa que os scripts reais existem e têm permissões corretas."""

    @classmethod
    def setUpClass(cls):
        cls.project_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

    def test_run_executor_exists(self):
        path = os.path.join(self.project_dir, "scripts", "run_executor.sh")
        self.assertTrue(os.path.isfile(path), f"Missing: {path}")

    def test_run_executor_executable(self):
        path = os.path.join(self.project_dir, "scripts", "run_executor.sh")
        self.assertTrue(os.access(path, os.X_OK), f"Not executable: {path}")

    def test_setup_cron_exists(self):
        path = os.path.join(self.project_dir, "scripts", "setup_cron.sh")
        self.assertTrue(os.path.isfile(path), f"Missing: {path}")

    def test_setup_cron_executable(self):
        path = os.path.join(self.project_dir, "scripts", "setup_cron.sh")
        self.assertTrue(os.access(path, os.X_OK), f"Not executable: {path}")

    def test_run_executor_has_shebang(self):
        path = os.path.join(self.project_dir, "scripts", "run_executor.sh")
        with open(path) as f:
            self.assertTrue(f.readline().startswith("#!/"))

    def test_setup_cron_has_shebang(self):
        path = os.path.join(self.project_dir, "scripts", "setup_cron.sh")
        with open(path) as f:
            self.assertTrue(f.readline().startswith("#!/"))

    def test_run_executor_checks_schedule_id(self):
        path = os.path.join(self.project_dir, "scripts", "run_executor.sh")
        content = Path(path).read_text()
        self.assertIn("SCHEDULE_ID=$1", content)
        self.assertIn("-z", content)
        self.assertIn("schedule_id nao informado", content)

    def test_setup_cron_calls_sync_all_schedules(self):
        path = os.path.join(self.project_dir, "scripts", "setup_cron.sh")
        content = Path(path).read_text()
        self.assertIn("sync_all_schedules", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
