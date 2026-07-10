from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.core.config import get_settings
from app.core.security import (
    SESSION_COOKIE_NAME,
    create_session_token,
    read_session_token,
    validate_auth_configuration,
    verify_password,
)
from app.schemas.auth_schema import AuthStatusResponse, LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_ATTEMPTS = 5
_attempts: dict[str, deque[float]] = defaultdict(deque)
_attempt_lock = Lock()


def require_authenticated_user(request: Request) -> str:
    settings = get_settings()
    if not settings.auth_enabled:
        return settings.auth_admin_username
    if not validate_auth_configuration(settings.auth_admin_password_hash, settings.auth_session_secret):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication is not configured")
    payload = read_session_token(
        request.cookies.get(SESSION_COOKIE_NAME, ""),
        settings.auth_session_secret or "",
    )
    if payload is None or payload.get("sub") != settings.auth_admin_username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return str(payload["sub"])


@router.get("/status", response_model=AuthStatusResponse)
def auth_status(request: Request) -> AuthStatusResponse:
    settings = get_settings()
    configured = validate_auth_configuration(settings.auth_admin_password_hash, settings.auth_session_secret)
    if not settings.auth_enabled:
        return AuthStatusResponse(
            enabled=False,
            configured=configured,
            authenticated=True,
            username=settings.auth_admin_username,
        )
    payload = None
    if configured:
        payload = read_session_token(
            request.cookies.get(SESSION_COOKIE_NAME, ""),
            settings.auth_session_secret or "",
        )
    authenticated = bool(payload and payload.get("sub") == settings.auth_admin_username)
    return AuthStatusResponse(
        enabled=True,
        configured=configured,
        authenticated=authenticated,
        username=settings.auth_admin_username if authenticated else None,
    )


@router.post("/login", response_model=AuthStatusResponse)
def login(request: Request, response: Response, payload: LoginRequest) -> AuthStatusResponse:
    settings = get_settings()
    configured = validate_auth_configuration(settings.auth_admin_password_hash, settings.auth_session_secret)
    if not settings.auth_enabled:
        return AuthStatusResponse(enabled=False, configured=configured, authenticated=True, username=settings.auth_admin_username)
    if not configured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication is not configured")

    client_key = resolve_client_key(request)
    enforce_login_rate_limit(client_key)
    username_valid = payload.username == settings.auth_admin_username
    password_valid = verify_password(payload.password, settings.auth_admin_password_hash or "")
    if not (username_valid and password_valid):
        record_failed_attempt(client_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    clear_failed_attempts(client_key)
    token = create_session_token(
        settings.auth_admin_username,
        settings.auth_session_secret or "",
        settings.auth_session_ttl_hours,
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.auth_session_ttl_hours * 3600,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )
    return AuthStatusResponse(enabled=True, configured=True, authenticated=True, username=settings.auth_admin_username)


@router.post("/logout", response_model=AuthStatusResponse)
def logout(response: Response) -> AuthStatusResponse:
    settings = get_settings()
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )
    return AuthStatusResponse(
        enabled=settings.auth_enabled,
        configured=validate_auth_configuration(settings.auth_admin_password_hash, settings.auth_session_secret),
        authenticated=not settings.auth_enabled,
        username=settings.auth_admin_username if not settings.auth_enabled else None,
    )


def enforce_login_rate_limit(client_key: str) -> None:
    now = monotonic()
    with _attempt_lock:
        attempts = _attempts[client_key]
        while attempts and now - attempts[0] > LOGIN_WINDOW_SECONDS:
            attempts.popleft()
        if len(attempts) >= LOGIN_MAX_ATTEMPTS:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="登录尝试过多，请稍后再试")


def record_failed_attempt(client_key: str) -> None:
    with _attempt_lock:
        _attempts[client_key].append(monotonic())


def clear_failed_attempts(client_key: str) -> None:
    with _attempt_lock:
        _attempts.pop(client_key, None)


def resolve_client_key(request: Request) -> str:
    settings = get_settings()
    if settings.trust_proxy_headers:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"
