import sqlite3
import os
from datetime import datetime
from flask import current_app
from flask_login import UserMixin

DATABASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DATABASE_PATH = os.path.join(DATABASE_DIR, "scheduler.db")


def get_db():
    if "db" not in current_app.config:
        os.makedirs(DATABASE_DIR, exist_ok=True)
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        current_app.config["db"] = conn
    return current_app.config["db"]


def close_db(exception=None):
    db = current_app.config.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    os.makedirs(DATABASE_DIR, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tone TEXT DEFAULT 'infografico',
            format TEXT DEFAULT 'html',
            active BOOLEAN DEFAULT 1,
            enable_search BOOLEAN DEFAULT 1,
            search_max_results INTEGER DEFAULT 5,
            debug_mode BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_id INTEGER,
            cron_expr TEXT NOT NULL,
            description TEXT,
            email_to TEXT NOT NULL,
            active BOOLEAN DEFAULT 1,
            last_run_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            schedule_type TEXT DEFAULT 'ai',
            static_content TEXT,
            static_is_html INTEGER DEFAULT 0,
            static_subject TEXT,
            command_text TEXT,
            FOREIGN KEY (prompt_id) REFERENCES prompts(id)
        );

        CREATE TABLE IF NOT EXISTS execution_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'success',
            error_message TEXT,
            duration_ms INTEGER,
            triggered_by TEXT DEFAULT 'cron',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_schedules_prompt_id ON schedules(prompt_id);
        CREATE INDEX IF NOT EXISTS idx_schedules_active ON schedules(active);
        CREATE INDEX IF NOT EXISTS idx_execution_logs_schedule_id ON execution_logs(schedule_id);
        CREATE INDEX IF NOT EXISTS idx_execution_logs_created_at ON execution_logs(created_at);

        INSERT OR IGNORE INTO schema_version (version) VALUES (1);
    """)

    try:
        conn.execute("ALTER TABLE schedules ADD COLUMN schedule_type TEXT DEFAULT 'ai'")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE schedules ADD COLUMN static_content TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE schedules ADD COLUMN static_is_html INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE schedules ADD COLUMN static_subject TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE schedules ADD COLUMN command_text TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE prompts ADD COLUMN enable_search BOOLEAN DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE prompts ADD COLUMN search_max_results INTEGER DEFAULT 5")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE prompts ADD COLUMN debug_mode BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

    app.teardown_appcontext(close_db)


def query(sql, params=(), one=False):
    db = get_db()
    cur = db.execute(sql, params)
    if one:
        return cur.fetchone()
    return cur.fetchall()


def execute(sql, params=()):
    db = get_db()
    try:
        cur = db.execute(sql, params)
        db.commit()
        return cur.lastrowid
    except Exception:
        db.rollback()
        raise


class User:
    @staticmethod
    def get_by_id(user_id):
        return query("SELECT * FROM users WHERE id = ?", (user_id,), one=True)

    @staticmethod
    def get_by_username(username):
        return query("SELECT * FROM users WHERE username = ?", (username,), one=True)

    @staticmethod
    def create(username, password_hash):
        return execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password_hash)
        )


class UserModel(UserMixin):
    def __init__(self, row):
        self._row = row

    @property
    def id(self):
        return str(self._row["id"])

    @property
    def username(self):
        return self._row["username"]

    @staticmethod
    def get(user_id):
        row = User.get_by_id(int(user_id))
        if row:
            return UserModel(row)
        return None


class Prompt:
    @staticmethod
    def get_all(active_only=False):
        if active_only:
            return query("SELECT * FROM prompts WHERE active = 1 ORDER BY created_at DESC")
        return query("SELECT * FROM prompts ORDER BY created_at DESC")

    @staticmethod
    def get_by_id(prompt_id):
        return query("SELECT * FROM prompts WHERE id = ?", (prompt_id,), one=True)

    @staticmethod
    def create(title, content, tone="infografico", fmt="html", active=1,
               enable_search=1, search_max_results=5, debug_mode=0):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return execute(
            "INSERT INTO prompts (title, content, tone, format, active, enable_search, search_max_results, debug_mode, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (title, content, tone, fmt, active, enable_search, search_max_results, debug_mode, now, now)
        )

    @staticmethod
    def update(prompt_id, title, content, tone, fmt, active,
               enable_search=None, search_max_results=None, debug_mode=None):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        execute(
            "UPDATE prompts SET title=?, content=?, tone=?, format=?, active=?,"
            " enable_search=COALESCE(?, enable_search),"
            " search_max_results=COALESCE(?, search_max_results),"
            " debug_mode=COALESCE(?, debug_mode),"
            " updated_at=? WHERE id=?",
            (title, content, tone, fmt, active, enable_search, search_max_results, debug_mode, now, prompt_id)
        )

    @staticmethod
    def delete(prompt_id):
        execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))

    @staticmethod
    def get_active():
        return query("SELECT * FROM prompts WHERE active = 1 ORDER BY title")


class Schedule:
    @staticmethod
    def get_all():
        return query("""
            SELECT s.*, p.title as prompt_title
            FROM schedules s
            LEFT JOIN prompts p ON s.prompt_id = p.id
            ORDER BY s.created_at DESC
        """)

    @staticmethod
    def get_by_id(schedule_id):
        return query("""
            SELECT s.*, p.title as prompt_title, p.content as prompt_content,
                   p.tone as prompt_tone, p.format as prompt_format,
                   p.enable_search, p.search_max_results, p.debug_mode
            FROM schedules s
            LEFT JOIN prompts p ON s.prompt_id = p.id
            WHERE s.id = ?
        """, (schedule_id,), one=True)

    @staticmethod
    def get_tasks():
        return query("""
            SELECT s.*
            FROM schedules s
            WHERE s.schedule_type IN ('static', 'command')
            ORDER BY s.created_at DESC
        """)

    @staticmethod
    def create(prompt_id, cron_expr, description, email_to,
               schedule_type="ai", static_content=None, static_is_html=0,
               static_subject=None, command_text=None):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if prompt_id is None:
            prompt_id = 0
        db = get_db()
        db.execute("PRAGMA foreign_keys=OFF")
        try:
            rowid = db.execute(
                "INSERT INTO schedules (prompt_id, cron_expr, description, email_to,"
                " schedule_type, static_content, static_is_html, static_subject, command_text,"
                " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (prompt_id, cron_expr, description, email_to, schedule_type,
                 static_content, static_is_html, static_subject, command_text, now, now)
            ).lastrowid
            db.commit()
        finally:
            db.execute("PRAGMA foreign_keys=ON")
        return rowid

    @staticmethod
    def update(schedule_id, prompt_id, cron_expr, description, email_to, active,
               schedule_type=None, static_content=None, static_is_html=None,
               static_subject=None, command_text=None):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if prompt_id is None:
            prompt_id = 0
        bypass_fk = (prompt_id == 0)
        db = get_db()
        if bypass_fk:
            db.execute("PRAGMA foreign_keys=OFF")
        try:
            db.execute(
                "UPDATE schedules SET prompt_id=?, cron_expr=?, description=?, email_to=?,"
                " active=?, schedule_type=?, static_content=?, static_is_html=?,"
                " static_subject=?, command_text=?, updated_at=? WHERE id=?",
                (prompt_id, cron_expr, description, email_to, active, schedule_type,
                 static_content, static_is_html, static_subject, command_text, now, schedule_id)
            )
            db.commit()
        finally:
            if bypass_fk:
                db.execute("PRAGMA foreign_keys=ON")

    @staticmethod
    def delete(schedule_id):
        execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))

    @staticmethod
    def toggle(schedule_id):
        schedule = Schedule.get_by_id(schedule_id)
        if schedule:
            new_active = 0 if schedule["active"] else 1
            execute("UPDATE schedules SET active = ?, updated_at = ? WHERE id = ?",
                    (new_active, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), schedule_id))

    @staticmethod
    def update_last_run(schedule_id):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        execute("UPDATE schedules SET last_run_at = ? WHERE id = ?", (now, schedule_id))

    @staticmethod
    def get_active_schedules():
        return query("""
            SELECT s.*, p.title as prompt_title, p.content as prompt_content,
                   p.tone as prompt_tone, p.format as prompt_format,
                   p.enable_search, p.search_max_results, p.debug_mode
            FROM schedules s
            LEFT JOIN prompts p ON s.prompt_id = p.id
            WHERE s.active = 1
        """)


class ExecutionLog:
    @staticmethod
    def create(schedule_id, status, error_message=None, duration_ms=None, triggered_by="cron"):
        return execute(
            "INSERT INTO execution_logs (schedule_id, status, error_message, duration_ms, triggered_by) VALUES (?, ?, ?, ?, ?)",
            (schedule_id, status, error_message, duration_ms, triggered_by)
        )

    @staticmethod
    def get_recent(limit=10, schedule_id=None):
        if schedule_id:
            return query("""
                SELECT el.*, s.description as schedule_desc, p.title as prompt_title
                FROM execution_logs el
                JOIN schedules s ON el.schedule_id = s.id
                LEFT JOIN prompts p ON s.prompt_id = p.id
                WHERE el.schedule_id = ?
                ORDER BY el.created_at DESC
                LIMIT ?
            """, (schedule_id, limit))
        return query("""
            SELECT el.*, s.description as schedule_desc, p.title as prompt_title
            FROM execution_logs el
            JOIN schedules s ON el.schedule_id = s.id
            LEFT JOIN prompts p ON s.prompt_id = p.id
            ORDER BY el.created_at DESC
            LIMIT ?
        """, (limit,))

    @staticmethod
    def get_stats():
        today = datetime.now().strftime("%Y-%m-%d")
        return {
            "total_prompts": query("SELECT COUNT(*) as cnt FROM prompts", one=True)["cnt"],
            "active_prompts": query("SELECT COUNT(*) as cnt FROM prompts WHERE active=1", one=True)["cnt"],
            "total_schedules": query("SELECT COUNT(*) as cnt FROM schedules", one=True)["cnt"],
            "active_schedules": query("SELECT COUNT(*) as cnt FROM schedules WHERE active=1", one=True)["cnt"],
            "active_tasks": query("SELECT COUNT(*) as cnt FROM schedules WHERE active=1 AND schedule_type != 'ai'", one=True)["cnt"],
            "executions_today": query(
                "SELECT COUNT(*) as cnt FROM execution_logs WHERE date(created_at) = ?", (today,), one=True
            )["cnt"],
            "success_rate": _calculate_success_rate(),
        }


def _calculate_success_rate():
    row = query("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as successes
        FROM execution_logs
    """, one=True)
    if row and row["total"] > 0:
        return round((row["successes"] / row["total"]) * 100, 1)
    return 100.0
