import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from contextlib import contextmanager

from utils.app_data import APP_DATA_DIR

DB_FILE = APP_DATA_DIR / "bilibili_client.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_database():
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS whitelist (
                uid TEXT PRIMARY KEY,
                username TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                sender_uid TEXT NOT NULL,
                sender_name TEXT,
                bv_id TEXT NOT NULL,
                content TEXT,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bv_id TEXT NOT NULL,
                sender_uid TEXT,
                sender_name TEXT,
                subtitle_text TEXT,
                summary_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                date TEXT PRIMARY KEY,
                count INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS login_state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)


class Database:
    @staticmethod
    def add_whitelist(uid: str, username: str = None) -> bool:
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO whitelist (uid, username) VALUES (?, ?)",
                    (uid, username)
                )
            return True
        except Exception:
            return False

    @staticmethod
    def remove_whitelist(uid: str) -> bool:
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM whitelist WHERE uid = ?", (uid,))
            return True
        except Exception:
            return False

    @staticmethod
    def get_whitelist() -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM whitelist ORDER BY added_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def is_whitelist(uid: str) -> bool:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM whitelist WHERE uid = ?", (uid,))
            return cursor.fetchone() is not None

    @staticmethod
    def get_not_whitelisted_messages() -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM messages WHERE status = 'not_whitelisted' ORDER BY received_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def add_message(msg_id: str, sender_uid: str, sender_name: str, bv_id: str, content: str = None) -> bool:
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO messages (id, sender_uid, sender_name, bv_id, content, status)
                    VALUES (?, ?, ?, ?, ?, 'pending')
                """, (msg_id, sender_uid, sender_name, bv_id, content))
            return True
        except Exception:
            return False

    @staticmethod
    def get_pending_messages() -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM messages WHERE status = 'pending' ORDER BY received_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_message(msg_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM messages WHERE id = ?", (msg_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def update_message_status(msg_id: str, status: str):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE messages SET status = ? WHERE id = ?", (status, msg_id))

    @staticmethod
    def get_messages(limit: int = 50) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM messages ORDER BY received_at DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def add_summary(bv_id: str, sender_uid: str, sender_name: str, subtitle_text: str, summary_text: str) -> int:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO summaries (bv_id, sender_uid, sender_name, subtitle_text, summary_text)
                VALUES (?, ?, ?, ?, ?)
            """, (bv_id, sender_uid, sender_name, subtitle_text, summary_text))
            summary_id = cursor.lastrowid

            today = date.today().isoformat()
            cursor.execute("""
                INSERT INTO stats (date, count) VALUES (?, 1)
                ON CONFLICT(date) DO UPDATE SET count = count + 1
            """, (today,))
            return summary_id

    @staticmethod
    def get_summaries(limit: int = 100) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM summaries ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_today_count() -> int:
        with get_db() as conn:
            cursor = conn.cursor()
            today = date.today().isoformat()
            cursor.execute("SELECT count FROM stats WHERE date = ?", (today,))
            row = cursor.fetchone()
            return row["count"] if row else 0

    @staticmethod
    def get_total_count() -> int:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM summaries")
            return cursor.fetchone()[0]

    @staticmethod
    def save_login_state(key: str, value: str):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO login_state (key, value) VALUES (?, ?)
            """, (key, value))

    @staticmethod
    def get_login_state(key: str) -> Optional[str]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM login_state WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else None

    @staticmethod
    def clear_login_state():
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM login_state")


init_database()
database = Database()