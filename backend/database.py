import os
import sqlite3
from datetime import datetime, timezone

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")


def get_db_path():
    if DATABASE_URL.startswith("sqlite:////"):
        return "/" + DATABASE_URL.replace("sqlite:////", "", 1)

    if DATABASE_URL.startswith("sqlite:///"):
        return DATABASE_URL.replace("sqlite:///", "", 1)

    return "app.db"


def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_session
        ON messages(session_id)
    """)

    conn.commit()
    conn.close()


def add_message(session_id, role, content, metadata=None):
    conn = get_connection()

    conn.execute(
        """
        INSERT INTO messages
        (session_id, role, content, metadata, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            session_id,
            role,
            content,
            metadata,
            datetime.now(timezone.utc).isoformat()
        )
    )

    conn.commit()
    conn.close()


def get_messages(session_id):
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT role, content, metadata
        FROM messages
        WHERE session_id = ?
        ORDER BY id ASC
        """,
        (session_id,)
    ).fetchall()

    conn.close()
    return rows