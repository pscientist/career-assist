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
    job_id INTEGER,
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
    names = {row["name"] for row in connection.execute("PRAGMA table_info(job_status)")}
    if "job_id" not in names:
        connection.execute("ALTER TABLE job_status ADD COLUMN job_id INTEGER")
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS job_status_job_id ON job_status(job_id)"
    )


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


def _manual_row_id(card_id):
    text = str(card_id)
    if text.startswith("m") and text[1:].isdigit():
        return int(text[1:])
    return None


def add_manual_job(title, company, location="", url="", seek_id="", source="", tech_stack=None, requirements=""):
    """Insert a hand-added job. A blank Seek id is stored as empty, not as a made-up number."""
    seek_id = (seek_id or "").strip() or None
    now = _now()
    try:
        with _connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO jobs (
                    seek_id, is_manual, source, title, company, location, url,
                    tech_stack, requirements, created_at, updated_at
                )
                VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    seek_id,
                    (source or "").strip() or None,
                    title.strip(),
                    company.strip(),
                    (location or "").strip() or None,
                    (url or "").strip() or None,
                    json.dumps(tech_stack or []),
                    requirements or "",
                    now,
                    now,
                ),
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError as error:
        raise ValueError("That Seek id is already stored.") from error


def manual_jobs():
    """Hand-added jobs, newest first, shaped like a scrape record."""
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, seek_id, title, company, location, url, tech_stack, requirements
            FROM jobs
            WHERE is_manual = 1
            ORDER BY id DESC
            """
        ).fetchall()
    jobs = []
    for row in rows:
        # check the tech stack being correct json 
        try:
            stack = json.loads(row["tech_stack"] or "[]")
        except json.JSONDecodeError:
            stack = []


        if not isinstance(stack, list):
            stack = []
        jobs.append(
            {
                "id": row["seek_id"] or f"m{row['id']}",
                "title": row["title"] or "",
                "company": row["company"] or "",
                "location": row["location"] or "",
                "url": row["url"] or "",
                "tech_stack": [str(term) for term in stack],
                "requirements": row["requirements"] or "",
            }
        )
    return jobs


def set_status(seek_id, status, next_appt_date=None):
    if status not in STATUSES:
        raise ValueError(f"Unknown status: {status}")
    next_appt_date = _check_date(next_appt_date)
    row_id = _manual_row_id(seek_id)
    with _connect() as connection:
        if row_id is not None:
            connection.execute(
                """
                INSERT INTO job_status (job_id, seek_id, status, next_appt_date, updated_at)
                VALUES (?, NULL, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    status = excluded.status,
                    next_appt_date = excluded.next_appt_date,
                    updated_at = excluded.updated_at
                """,
                (row_id, status, next_appt_date, _now()),
            )
            return
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
    row_id = _manual_row_id(seek_id)
    with _connect() as connection:
        if row_id is not None:
            connection.execute("DELETE FROM job_status WHERE job_id = ?", (row_id,))
            return
        connection.execute("DELETE FROM job_status WHERE seek_id = ?", (str(seek_id),))


def statuses():
    with _connect() as connection:
        rows = connection.execute(
            "SELECT seek_id, job_id, status, next_appt_date, updated_at FROM job_status"
        ).fetchall()
    records = {}
    for row in rows:
        record = {
            "status": row["status"],
            "next_appt_date": row["next_appt_date"],
            "updated_at": row["updated_at"],
        }
        if row["seek_id"]:
            records[row["seek_id"]] = record
        if row["job_id"] is not None:
            records[f"m{row['job_id']}"] = record
    return records
