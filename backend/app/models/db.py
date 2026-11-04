import sqlite3
from contextlib import contextmanager
from pathlib import Path

# backend/app/models/db.py -> repository root
ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "jobs.sqlite"

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
