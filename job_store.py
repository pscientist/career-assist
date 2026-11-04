import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "jobs.sqlite"
LEGACY_STATUS_PATH = ROOT / "job_status.json"
STATUSES = {"deleted", "applied", "interviewing"}
_JOB_STATUS_COLUMNS = """
    id INTEGER PRIMARY KEY,
    seek_id TEXT UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('deleted', 'applied', 'interviewing')),
    next_appt_date TEXT,
    updated_at TEXT NOT NULL
"""


def _ensure_job_status(connection):
    """Give job_status its own id. Copy rows when the old seek_id key is still in place."""
    columns = connection.execute("PRAGMA table_info(job_status)").fetchall()
    names = {row["name"] for row in columns}
    if names and "id" not in names:
        connection.execute(f"CREATE TABLE job_status_new ({_JOB_STATUS_COLUMNS})")
        connection.execute(
            """
            INSERT INTO job_status_new (seek_id, status, next_appt_date, updated_at)
            SELECT seek_id, status, next_appt_date, updated_at FROM job_status
            """
        )
        connection.execute("DROP TABLE job_status")
        connection.execute("ALTER TABLE job_status_new RENAME TO job_status")
    connection.execute(f"CREATE TABLE IF NOT EXISTS job_status ({_JOB_STATUS_COLUMNS})")


def _connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    _ensure_job_status(connection)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY,
            seek_id TEXT UNIQUE,
            is_manual INTEGER NOT NULL,
            source TEXT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,
            url TEXT,
            tech_stack TEXT,
            requirements TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS store_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    _import_legacy_removals(connection)
    connection.commit()
    return connection


def _import_legacy_removals(connection):
    """Copy removed ids from job_status.json once. The JSON file is left in place."""
    already = connection.execute(
        "SELECT value FROM store_meta WHERE key = 'legacy_imported'"
    ).fetchone()
    if already:
        return
    if LEGACY_STATUS_PATH.is_file():
        try:
            data = json.loads(LEGACY_STATUS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        if isinstance(data, dict):
            now = _now()
            for seek_id, entry in data.items():
                if isinstance(entry, dict) and entry.get("status") == "removed":
                    connection.execute(
                        """
                        INSERT INTO job_status (seek_id, status, next_appt_date, updated_at)
                        VALUES (?, 'deleted', NULL, ?)
                        ON CONFLICT(seek_id) DO NOTHING
                        """,
                        (str(seek_id), now),
                    )
    connection.execute(
        "INSERT INTO store_meta (key, value) VALUES ('legacy_imported', '1')"
    )


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _check_date(next_appt_date):
    if next_appt_date in (None, ""):
        return None
    datetime.strptime(next_appt_date, "%Y-%m-%d")
    return next_appt_date


def set_status(seek_id, status, next_appt_date=None):
    if status not in STATUSES:
        raise ValueError(f"Unknown status: {status}")
    next_appt_date = _check_date(next_appt_date)
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO job_status (seek_id, status, next_appt_date, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(seek_id) DO UPDATE SET
                status = excluded.status,
                next_appt_date = excluded.next_appt_date,
                updated_at = excluded.updated_at
            """,
            (str(seek_id), status, next_appt_date, _now()),
        )


def clear_status(seek_id):
    """Drop a status row so the job returns to New."""
    with _connect() as connection:
        connection.execute("DELETE FROM job_status WHERE seek_id = ?", (str(seek_id),))


def statuses():
    with _connect() as connection:
        rows = connection.execute(
            "SELECT seek_id, status, next_appt_date, updated_at FROM job_status"
        ).fetchall()
    return {
        row["seek_id"]: {
            "status": row["status"],
            "next_appt_date": row["next_appt_date"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    }
