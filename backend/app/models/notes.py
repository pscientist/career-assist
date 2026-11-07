from datetime import datetime, timezone

from app.models.db import connect


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _note(row):
    return {
        "id": row["id"],
        "note": row["note"] or "",
        "created_at": row["created_at"] or "",
    }


def list_notes(user_id):
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM interview_notes WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    return [_note(row) for row in rows]


def add_note(note, user_id):
    text = (note or "").strip()
    if not text:
        raise ValueError("Add a note.")
    created_at = _now()
    with connect() as connection:
        cursor = connection.execute(
            "INSERT INTO interview_notes (note, created_at, user_id) VALUES (?, ?, ?)",
            (text, created_at, user_id),
        )
        row = connection.execute(
            "SELECT * FROM interview_notes WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return _note(row)
