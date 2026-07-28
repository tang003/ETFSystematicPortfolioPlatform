from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.core.config import get_settings
from app.core.security import SESSION_COOKIE_NAME, create_session_token, hash_password, read_session_token, verify_password
from app.main import create_app
from app.api import auth_api
from app.api.auth_api import get_authenticated_user, require_researcher_user, resolve_client_key


def test_password_hash_round_trip() -> None:
    encoded = hash_password("a-strong-test-password", salt="fixed-test-salt", iterations=10_000)

    assert verify_password("a-strong-test-password", encoded)
    assert not verify_password("incorrect-password", encoded)


def test_session_token_round_trip() -> None:
    token = create_session_token("admin", "x" * 48, 1)

    payload = read_session_token(token, "x" * 48)

    assert payload is not None
    assert payload["sub"] == "admin"


def test_session_token_rejects_wrong_secret_and_tampering() -> None:
    token = create_session_token("admin", "x" * 48, 1)

    assert read_session_token(token, "y" * 48) is None
    assert read_session_token(f"{token}changed", "x" * 48) is None


def test_protected_api_requires_login(monkeypatch) -> None:
    password = "a-strong-test-password"
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_ADMIN_USERNAME", "operator")
    monkeypatch.setenv(
        "AUTH_ADMIN_PASSWORD_HASH",
        hash_password(password, salt="api-test-salt", iterations=10_000),
    )
    monkeypatch.setenv("AUTH_SESSION_SECRET", "s" * 48)
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    get_settings.cache_clear()

    try:
        with TestClient(create_app()) as client:
            assert client.get("/api/assets").status_code == 401
            assert client.post("/api/auth/login", json={"username": "operator", "password": "wrong"}).status_code == 401

            login_response = client.post(
                "/api/auth/login",
                json={"username": "operator", "password": password},
            )
            assert login_response.status_code == 200
            assert login_response.json()["authenticated"] is True
            assert login_response.json()["role"] == "admin"
            assert client.get("/api/assets").status_code == 200

            assert client.post("/api/auth/logout").status_code == 200
            assert client.get("/api/assets").status_code == 401
    finally:
        get_settings.cache_clear()


def test_admin_only_api_rejects_non_admin_role(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_ADMIN_USERNAME", "operator")
    monkeypatch.setenv(
        "AUTH_ADMIN_PASSWORD_HASH",
        hash_password("a-strong-test-password", salt="role-test-salt", iterations=10_000),
    )
    monkeypatch.setenv("AUTH_SESSION_SECRET", "s" * 48)
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    get_settings.cache_clear()

    try:
        with TestClient(create_app()) as client:
            token = create_session_token("operator", "s" * 48, 1, role="viewer")
            client.cookies.set("etf_portfolio_session", token)

            assert client.get("/api/assets").status_code == 200
            response = client.get("/api/settings/maintenance")
            assert response.status_code == 403
            assert response.json()["detail"] == "Admin permission required"
    finally:
        get_settings.cache_clear()


def test_researcher_write_api_rejects_viewer_role(monkeypatch) -> None:
    class Request:
        cookies = {SESSION_COOKIE_NAME: create_session_token("operator", "s" * 48, 1, role="viewer")}

    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_ADMIN_USERNAME", "operator")
    monkeypatch.setenv(
        "AUTH_ADMIN_PASSWORD_HASH",
        hash_password("a-strong-test-password", salt="viewer-write-salt", iterations=10_000),
    )
    monkeypatch.setenv("AUTH_SESSION_SECRET", "s" * 48)
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    get_settings.cache_clear()

    try:
        with pytest.raises(HTTPException) as exc:
            require_researcher_user(Request())
        assert exc.value.status_code == 403
        assert exc.value.detail == "Researcher permission required"
    finally:
        get_settings.cache_clear()


def test_disabled_database_user_session_is_rejected(monkeypatch) -> None:
    @dataclass
    class DisabledUser:
        username: str = "researcher01"
        role: str = "researcher"
        is_active: bool = False

    class Request:
        cookies = {SESSION_COOKIE_NAME: create_session_token("researcher01", "s" * 48, 1, role="researcher")}

    class DummySession:
        def close(self) -> None:
            pass

    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_ADMIN_USERNAME", "operator")
    monkeypatch.setenv(
        "AUTH_ADMIN_PASSWORD_HASH",
        hash_password("a-strong-test-password", salt="disabled-user-salt", iterations=10_000),
    )
    monkeypatch.setenv("AUTH_SESSION_SECRET", "s" * 48)
    get_settings.cache_clear()
    monkeypatch.setattr(auth_api, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr(auth_api, "get_user_by_username", lambda db, username: DisabledUser())

    try:
        with pytest.raises(HTTPException) as exc:
            get_authenticated_user(Request())
        assert exc.value.status_code == 401
    finally:
        get_settings.cache_clear()


def test_resolve_client_key_uses_rightmost_forwarded_for_when_proxy_trusted(monkeypatch) -> None:
    class Client:
        host = "127.0.0.1"

    class Request:
        headers = {"x-forwarded-for": "198.51.100.10, 203.0.113.20"}
        client = Client()

    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    get_settings.cache_clear()
    try:
        assert resolve_client_key(Request()) == "203.0.113.20"
    finally:
        get_settings.cache_clear()
