import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timezone

from app.models.db import connect

_PBKDF2_ROUNDS = 200_000


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2${salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    try:
        scheme, salt_hex, digest_hex = stored.split("$", 2)
        if scheme != "pbkdf2":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return hmac.compare_digest(digest, expected)


def _account(username):
    username = (username or "").strip()
    if not username:
        raise ValueError("Choose a username.")
    if len(username) > 40:
        raise ValueError("Use a username of 40 characters or fewer.")
    return username


def _name(name):
    name = (name or "").strip()
    if not name:
        raise ValueError("Add your name.")
    return name


def _password(password):
    password = password or ""
    if len(password) < 8:
        raise ValueError("Use at least 8 characters for the password.")
    return password


def _session(connection, user_id, username, name):
    token = secrets.token_urlsafe(32)
    connection.execute(
        "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
        (token, user_id, _now()),
    )
    return {"token": token, "username": username, "name": name}


def register_user(name, username, password):
    name = _name(name)
    username = _account(username)
    password = _password(password)
    try:
        with connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (username, name, password_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (username, name, hash_password(password), _now()),
            )
            return _session(connection, cursor.lastrowid, username, name)
    except sqlite3.IntegrityError as error:
        raise ValueError("That username is already registered.") from error


def login_user(username, password):
    username = (username or "").strip()
    with connect() as connection:
        row = connection.execute(
            "SELECT id, username, name, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if row is None or not verify_password(password or "", row["password_hash"]):
            return None
        return _session(connection, row["id"], row["username"], row["name"] or "")


def user_for_token(token):
    if not token:
        return None
    with connect() as connection:
        row = connection.execute(
            """
            SELECT users.id, users.username, users.name
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()
    if row is None:
        return None
    return {"id": row["id"], "username": row["username"], "name": row["name"] or ""}


def delete_session(token):
    if not token:
        return
    with connect() as connection:
        connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
