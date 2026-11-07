import sqlite3
from contextlib import contextmanager
from pathlib import Path

# backend/app/models/db.py -> repository root
ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "jobs.sqlite"

_NOTES_SCHEMA = """
CREATE TABLE IF NOT EXISTS interview_notes (
    id INTEGER PRIMARY KEY,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL,
    user_id INTEGER
)
"""

_USERS_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""

_SESSIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL
)
"""

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    seek_id TEXT UNIQUE,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    url TEXT,
    tech_stack TEXT,
    requirements TEXT,
    status TEXT NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'applied', 'interviewing', 'deleted')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


@contextmanager
def connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(_SCHEMA)
    connection.execute(_NOTES_SCHEMA)
    connection.execute(_USERS_SCHEMA)
    connection.execute(_SESSIONS_SCHEMA)
    user_columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
    if "name" not in user_columns:
        connection.execute("ALTER TABLE users ADD COLUMN name TEXT NOT NULL DEFAULT ''")
    note_columns = {row[1] for row in connection.execute("PRAGMA table_info(interview_notes)")}
    if "user_id" not in note_columns:
        connection.execute("ALTER TABLE interview_notes ADD COLUMN user_id INTEGER")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    with connect():
        pass
