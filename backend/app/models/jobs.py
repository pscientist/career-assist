import json
import sqlite3
from datetime import datetime, timezone

from app.models.db import connect

STATUSES = {"new", "applied", "interviewing", "deleted"}


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _blank(value):
    text = (value or "").strip()
    return text or None


def _job(row):
    try:
        stack = json.loads(row["tech_stack"] or "[]")
    except json.JSONDecodeError:
        stack = []
    if not isinstance(stack, list):
        stack = []
    return {
        "id": row["id"],
        "seek_id": row["seek_id"] or "",
        "title": row["title"] or "",
        "company": row["company"] or "",
        "location": row["location"] or "",
        "url": row["url"] or "",
        "tech_stack": [str(term) for term in stack],
        "requirements": row["requirements"] or "",
        "status": row["status"],
        "created_at": row["created_at"] or "",
    }


def list_jobs(include_deleted=False):
    """Jobs still on the list, newest first. Pass include_deleted for market counts."""
    sql = "SELECT * FROM jobs ORDER BY id DESC"
    if not include_deleted:
        sql = "SELECT * FROM jobs WHERE status != 'deleted' ORDER BY id DESC"
    with connect() as connection:
        rows = connection.execute(sql).fetchall()
    return [_job(row) for row in rows]


def get_job(job_id):
    with connect() as connection:
        row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return _job(row) if row else None


def add_job(title, company, location="", url="", seek_id="", tech_stack=None, requirements=""):
    title = (title or "").strip()
    company = (company or "").strip()
    if not title or not company:
        raise ValueError("Title and company are required.")
    now = _now()
    try:
        with connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO jobs (
                    seek_id, title, company, location, url, tech_stack, requirements,
                    status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'new', ?, ?)
                """,
                (
                    _blank(seek_id),
                    title,
                    company,
                    _blank(location),
                    _blank(url),
                    json.dumps(tech_stack or []),
                    requirements or "",
                    now,
                    now,
                ),
            )
            job_id = cursor.lastrowid
    except sqlite3.IntegrityError as error:
        raise ValueError("That Seek id is already stored.") from error
    return get_job(job_id)


def set_status(job_id, status):
    if status not in STATUSES:
        raise ValueError("Unknown status.")
    with connect() as connection:
        cursor = connection.execute(
            "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
            (status, _now(), job_id),
        )
        if cursor.rowcount == 0:
            return None
    return get_job(job_id)


def upsert_scraped(jobs):
    """Insert scraped ads. A Seek id that is already stored is left unchanged."""
    now = _now()
    with connect() as connection:
        for job in jobs:
            seek_id = _blank(job.get("seek_id") or job.get("id"))
            title = (job.get("title") or "").strip()
            company = (job.get("company") or "").strip()
            if not seek_id or not title or not company:
                continue
            connection.execute(
                """
                INSERT INTO jobs (
                    seek_id, title, company, location, url, tech_stack, requirements,
                    status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'new', ?, ?)
                ON CONFLICT(seek_id) DO NOTHING
                """,
                (
                    seek_id,
                    title,
                    company,
                    _blank(job.get("location")),
                    _blank(job.get("url")),
                    json.dumps(job.get("tech_stack") or []),
                    job.get("requirements") or "",
                    now,
                    now,
                ),
            )


def save_requirements(job_id, requirements, tech_stack):
    text = (requirements or "").strip()
    if not text:
        raise ValueError("Add the requirements.")
    with connect() as connection:
        cursor = connection.execute(
            """
            UPDATE jobs
            SET requirements = ?, tech_stack = ?, updated_at = ?
            WHERE id = ?
            """,
            (text, json.dumps(tech_stack or []), _now(), job_id),
        )
        if cursor.rowcount == 0:
            return None
    return get_job(job_id)
