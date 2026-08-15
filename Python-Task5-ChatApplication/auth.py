"""Password hashing and input validation helpers."""

import hashlib
import hmac
import re
import secrets

from config import MAX_ROOM_NAME_LENGTH, MAX_USERNAME_LENGTH


def hash_password(password: str) -> str:
    """Return a salted PBKDF2 hash suitable for SQLite storage."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, expected = stored_hash.split("$", 1)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, AttributeError):
        return False


def validate_username(username: str) -> str | None:
    if not 3 <= len(username) <= MAX_USERNAME_LENGTH:
        return f"Username must be 3-{MAX_USERNAME_LENGTH} characters."
    if not re.fullmatch(r"[A-Za-z0-9_]+", username):
        return "Username may contain only letters, numbers, and underscores."
    return None


def validate_password(password: str) -> str | None:
    if len(password) < 6:
        return "Password must be at least 6 characters."
    return None


def validate_room_name(name: str) -> str | None:
    if not name or not name.strip():
        return "Room name cannot be empty."
    if len(name.strip()) > MAX_ROOM_NAME_LENGTH:
        return f"Room name must be at most {MAX_ROOM_NAME_LENGTH} characters."
    return None
