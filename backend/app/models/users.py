import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timezone

from app.models.db import connect

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
    )
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    digest = hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
    )
    return hmac.compare_digest(digest, expected)


def _account(username):
    username = (username or "").strip()
    if not username:
        raise ValueError("Choose a username.")
    if len(username) > 40:
        raise ValueError("Use a username of 40 characters or fewer.")
    return username


def _password(password):
    password = password or ""
    if len(password) < 8:
        raise ValueError("Use at least 8 characters for the password.")
    return password


def _session(connection, user_id, username):
    token = secrets.token_urlsafe(32)
    connection.execute(
        "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
        (token, user_id, _now()),
    )
    return {"token": token, "username": username}


def register_user(username, password):
    username = _account(username)
    password = _password(password)
    try:
        with connect() as connection:
            cursor = connection.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, hash_password(password), _now()),
            )
            return _session(connection, cursor.lastrowid, username)
    except sqlite3.IntegrityError as error:
        raise ValueError("That username is already registered.") from error


def login_user(username, password):
    username = (username or "").strip()
    with connect() as connection:
        row = connection.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if row is None or not verify_password(password or "", row["password_hash"]):
            return None
        return _session(connection, row["id"], row["username"])


def user_for_token(token):
    if not token:
        return None
    with connect() as connection:
        row = connection.execute(
            """
            SELECT users.username
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()
    if row is None:
        return None
    return {"username": row["username"]}


def delete_session(token):
    if not token:
        return
    with connect() as connection:
        connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
