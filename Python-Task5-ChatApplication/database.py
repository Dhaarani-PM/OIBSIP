"""SQLite persistence layer. Each operation opens its own short-lived connection."""

import os
import sqlite3
from datetime import datetime

from auth import hash_password, verify_password
from config import DATABASE_PATH, HISTORY_LIMIT


def _connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database() -> None:
    with _connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                is_private INTEGER NOT NULL DEFAULT 0,
                password_hash TEXT,
                owner_username TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(room_id) REFERENCES rooms(id)
            );
        """)
        # Existing databases from earlier versions receive these columns without
        # losing rooms or message history. Existing rooms remain public.
        existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(rooms)")}
        if "is_private" not in existing_columns:
            conn.execute("ALTER TABLE rooms ADD COLUMN is_private INTEGER NOT NULL DEFAULT 0")
        if "password_hash" not in existing_columns:
            conn.execute("ALTER TABLE rooms ADD COLUMN password_hash TEXT")
        if "owner_username" not in existing_columns:
            conn.execute("ALTER TABLE rooms ADD COLUMN owner_username TEXT")
        conn.execute("INSERT OR IGNORE INTO rooms (name, created_at) VALUES (?, ?)", ("General", _now()))


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def register_user(username: str, password: str) -> tuple[bool, str]:
    try:
        with _connection() as conn:
            conn.execute("INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                         (username, hash_password(password), _now()))
        return True, "Registration successful. You can now log in."
    except sqlite3.IntegrityError:
        return False, "That username is already registered."


def authenticate_user(username: str, password: str) -> bool:
    with _connection() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE username = ?", (username,)).fetchone()
    return bool(row and verify_password(password, row["password_hash"]))


def list_rooms() -> list[dict]:
    with _connection() as conn:
        rows = conn.execute("SELECT name, is_private, owner_username FROM rooms ORDER BY name COLLATE NOCASE").fetchall()
    return [{"name": row["name"], "is_private": bool(row["is_private"]), "owner_username": row["owner_username"]} for row in rows]


def create_room(name: str, owner_username: str, password: str | None = None) -> tuple[bool, str]:
    try:
        with _connection() as conn:
            conn.execute(
                "INSERT INTO rooms (name, is_private, password_hash, owner_username, created_at) VALUES (?, ?, ?, ?, ?)",
                (name.strip(), bool(password), hash_password(password) if password else None, owner_username, _now()),
            )
        return True, "Room created."
    except sqlite3.IntegrityError:
        return False, "A room with that name already exists."


def get_room(name: str) -> dict | None:
    with _connection() as conn:
        row = conn.execute(
            "SELECT name, is_private, password_hash, owner_username FROM rooms WHERE name = ? COLLATE NOCASE", (name,)
        ).fetchone()
    return dict(row) if row else None


def verify_room_password(room: dict, password: str) -> bool:
    """Validate only on the server; password hashes never leave SQLite."""
    return not room["is_private"] or verify_password(password, room["password_hash"] or "")


def save_message(room: str, username: str, message: str) -> str:
    timestamp = _now()
    with _connection() as conn:
        room_id = conn.execute("SELECT id FROM rooms WHERE name = ? COLLATE NOCASE", (room,)).fetchone()["id"]
        conn.execute("INSERT INTO messages (room_id, username, message, timestamp) VALUES (?, ?, ?, ?)",
                     (room_id, username, message, timestamp))
    return timestamp


def get_history(room: str) -> list[dict]:
    with _connection() as conn:
        rows = conn.execute("""
            SELECT username, message, timestamp FROM messages
            WHERE room_id = (SELECT id FROM rooms WHERE name = ? COLLATE NOCASE)
            ORDER BY id DESC LIMIT ?
        """, (room, HISTORY_LIMIT)).fetchall()
    return [dict(row) for row in reversed(rows)]


def delete_room(name: str, owner_username: str) -> tuple[bool, str]:
    """Atomically remove an owned room and all of its persisted messages."""
    with _connection() as conn:
        room = conn.execute(
            "SELECT id FROM rooms WHERE name = ? COLLATE NOCASE AND owner_username = ?",
            (name, owner_username),
        ).fetchone()
        if not room:
            return False, "Only this room's creator can delete it."
        conn.execute("DELETE FROM messages WHERE room_id = ?", (room["id"],))
        conn.execute("DELETE FROM rooms WHERE id = ?", (room["id"],))
    return True, "Room deleted."
