from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint

from app.api.auth_api import get_authenticated_user
from app.core.database import SessionLocal
from app.models.audit import AuditLog

AUDITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
SKIPPED_PREFIXES = ("/api/auth/",)


def should_audit_request(request: Request) -> bool:
    return (
        request.method.upper() in AUDITED_METHODS
        and request.url.path.startswith("/api/")
        and not any(request.url.path.startswith(prefix) for prefix in SKIPPED_PREFIXES)
    )


async def audit_http_request(request: Request, call_next: RequestResponseEndpoint) -> Response:
    if not should_audit_request(request):
        return await call_next(request)

    request_id = request.headers.get("x-request-id") or uuid4().hex
    start = perf_counter()
    status_code: int | None = None
    error_message: str | None = None
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["x-request-id"] = request_id
        return response
    except Exception as exc:
        status_code = 500
        error_message = exc.__class__.__name__
        raise
    finally:
        duration_ms = int((perf_counter() - start) * 1000)
        record_audit_log(
            request=request,
            request_id=request_id,
            status_code=status_code,
            duration_ms=duration_ms,
            error_message=error_message,
        )


def record_audit_log(
    *,
    request: Request,
    request_id: str,
    status_code: int | None,
    duration_ms: int,
    error_message: str | None = None,
) -> None:
    user = None
    try:
        user = get_authenticated_user(request)
    except Exception:
        user = None

    detail = {"query": dict(request.query_params)}
    if error_message:
        detail["error"] = error_message

    db = SessionLocal()
    try:
        db.add(
            AuditLog(
                actor_username=user.username if user else None,
                actor_role=user.role if user else None,
                method=request.method.upper(),
                path=request.url.path,
                action=resolve_action(request.method.upper(), request.url.path),
                status_code=status_code,
                duration_ms=duration_ms,
                client_ip=resolve_client_ip(request),
                request_id=request_id,
                detail=detail,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def resolve_action(method: str, path: str) -> str:
    normalized = path.removeprefix("/api/").strip("/")
    head = normalized.split("/", 1)[0] or "api"
    return f"{method.lower()}_{head.replace('-', '_')}"


def resolve_client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[-1].strip()
    return request.client.host if request.client else None
