from datetime import datetime, timezone

from app.models.db import connect


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _achievement(row):
    return {
        "id": row["id"],
        "achievement": row["achievement"] or "",
        "created_at": row["created_at"] or "",
    }


def list_achievements(user_id):
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM achievements WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    return [_achievement(row) for row in rows]


def add_achievement(achievement, user_id):
    text = (achievement or "").strip()
    if not text:
        raise ValueError("Add an achievement.")
    created_at = _now()
    with connect() as connection:
        cursor = connection.execute(
            "INSERT INTO achievements (achievement, created_at, user_id) VALUES (?, ?, ?)",
            (text, created_at, user_id),
        )
        row = connection.execute(
            "SELECT * FROM achievements WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return _achievement(row)
