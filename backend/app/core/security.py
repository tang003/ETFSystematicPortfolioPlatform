import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 600_000
SESSION_COOKIE_NAME = "etf_portfolio_session"


def hash_password(password: str, *, salt: str | None = None, iterations: int = PASSWORD_ITERATIONS) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")
    resolved_salt = salt or secrets.token_urlsafe(18)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), resolved_salt.encode("utf-8"), iterations)
    return f"{PASSWORD_ALGORITHM}${iterations}${resolved_salt}${_b64encode(digest)}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, expected = encoded_hash.split("$", 3)
        if algorithm != PASSWORD_ALGORITHM:
            return False
        iterations = int(iterations_text)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
        return hmac.compare_digest(_b64encode(actual), expected)
    except (TypeError, ValueError):
        return False


def create_session_token(username: str, secret: str, ttl_hours: int, *, role: str = "admin") -> str:
    now = int(time.time())
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + ttl_hours * 3600,
        "nonce": secrets.token_urlsafe(12),
    }
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = hmac.new(secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded_payload}.{_b64encode(signature)}"


def read_session_token(token: str, secret: str) -> dict[str, Any] | None:
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        expected = hmac.new(secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64encode(expected), encoded_signature):
            return None
        payload = json.loads(_b64decode(encoded_payload))
        if not isinstance(payload, dict) or int(payload.get("exp", 0)) <= int(time.time()):
            return None
        if not payload.get("sub"):
            return None
        return payload
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def validate_auth_configuration(password_hash: str | None, session_secret: str | None) -> bool:
    if not password_hash or not session_secret or len(session_secret) < 32:
        return False
    try:
        algorithm, iterations_text, salt, digest = password_hash.split("$", 3)
        return algorithm == PASSWORD_ALGORITHM and int(iterations_text) > 0 and bool(salt and digest)
    except (TypeError, ValueError):
        return False


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
