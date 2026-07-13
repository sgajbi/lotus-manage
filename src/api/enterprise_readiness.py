import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger("enterprise_readiness")
MiddlewareNext = Callable[[Request], Awaitable[Response]]
MiddlewareCallable = Callable[[Request, MiddlewareNext], Awaitable[Response]]

_SERVICE_NAME = "lotus-manage"
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_REQUIRED_HEADERS = {"x-actor-id", "x-tenant-id", "x-role", "x-correlation-id"}
_REDACT_FIELDS = {
    "password",
    "secret",
    "token",
    "authorization",
    "ssn",
    "account_number",
    "client_email",
}


@dataclass(frozen=True)
class _AuditIdentity:
    actor_id: str
    tenant_id: str
    role: str
    correlation_id: str | None


def _env_enabled(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _load_json_map(name: str) -> dict[str, Any]:
    raw = os.getenv(name, "{}")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def enterprise_policy_version() -> str:
    return os.getenv("ENTERPRISE_POLICY_VERSION", "1.0.0")


def validate_enterprise_runtime_config() -> list[str]:
    issues = _enterprise_runtime_config_issues()
    if issues and _env_enabled("ENTERPRISE_ENFORCE_RUNTIME_CONFIG", "false"):
        raise RuntimeError(f"enterprise_runtime_config_invalid:{','.join(issues)}")
    return issues


def _enterprise_runtime_config_issues() -> list[str]:
    issue_candidates = (
        _policy_version_issue(),
        _secret_rotation_issue(),
        _authz_key_material_issue(),
    )
    return [issue for issue in issue_candidates if issue is not None]


def _policy_version_issue() -> str | None:
    if enterprise_policy_version().strip():
        return None
    return "missing_policy_version"


def _secret_rotation_issue() -> str | None:
    rotation_days = _env_int("ENTERPRISE_SECRET_ROTATION_DAYS", 90)
    if 0 < rotation_days <= 90:
        return None
    return "secret_rotation_days_out_of_range"


def _authz_key_material_issue() -> str | None:
    if not _env_enabled("ENTERPRISE_ENFORCE_AUTHZ", "false"):
        return None
    if os.getenv("ENTERPRISE_PRIMARY_KEY_ID", "").strip():
        return None
    return "missing_primary_key_id"


def load_feature_flags() -> dict[str, dict[str, dict[str, bool]]]:
    return _load_json_map("ENTERPRISE_FEATURE_FLAGS_JSON")


def load_capability_rules() -> dict[str, str]:
    rules = _load_json_map("ENTERPRISE_CAPABILITY_RULES_JSON")
    return {str(key): str(value) for key, value in rules.items() if isinstance(key, str)}


def is_feature_enabled(feature_key: str, tenant_id: str, role: str) -> bool:
    flags = load_feature_flags()
    feature = flags.get(feature_key, {})
    tenant = feature.get(tenant_id, {})
    explicit = tenant.get(role)
    if isinstance(explicit, bool):
        return explicit
    tenant_default = tenant.get("*")
    if isinstance(tenant_default, bool):
        return tenant_default
    global_default = feature.get("*", {}).get("*")
    return bool(global_default) if isinstance(global_default, bool) else False


def _required_capability(method: str, path: str) -> str | None:
    method = method.upper()
    for key, capability in load_capability_rules().items():
        prefix = f"{method} "
        if key.upper().startswith(prefix) and path.startswith(key[len(prefix) :]):
            return capability
    return None


def authorize_write_request(
    method: str, path: str, headers: dict[str, str]
) -> tuple[bool, str | None]:
    if not _write_authorization_required(method):
        return True, None

    normalized = _normalized_headers(headers)
    failure_reason = _write_authorization_failure_reason(
        method=method,
        path=path,
        headers=normalized,
    )
    if failure_reason is not None:
        return False, failure_reason
    return True, None


def _write_authorization_failure_reason(
    *,
    method: str,
    path: str,
    headers: dict[str, str],
) -> str | None:
    for reason in (
        _missing_required_headers_reason(headers),
        _missing_service_identity_reason(headers),
        _missing_capability_reason(method=method, path=path, headers=headers),
    ):
        if reason is not None:
            return reason
    return None


def _missing_required_headers_reason(headers: dict[str, str]) -> str | None:
    missing = _missing_required_headers(headers)
    if missing:
        return f"missing_headers:{','.join(missing)}"
    return None


def _missing_service_identity_reason(headers: dict[str, str]) -> str | None:
    if not _has_service_identity(headers):
        return "missing_service_identity"
    return None


def _missing_capability_reason(
    *,
    method: str,
    path: str,
    headers: dict[str, str],
) -> str | None:
    required_capability = _required_capability(method, path)
    if required_capability and required_capability not in _provided_capabilities(headers):
        return f"missing_capability:{required_capability}"
    return None


def _write_authorization_required(method: str) -> bool:
    return write_authorization_required(method)


def write_authorization_required(method: str) -> bool:
    return method.upper() in _WRITE_METHODS and _env_enabled(
        "ENTERPRISE_ENFORCE_AUTHZ",
        "false",
    )


def _normalized_headers(headers: dict[str, str]) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in headers.items()}


def _missing_required_headers(headers: dict[str, str]) -> list[str]:
    return sorted(header for header in _REQUIRED_HEADERS if not headers.get(header))


def _has_service_identity(headers: dict[str, str]) -> bool:
    return bool(headers.get("x-service-identity") or headers.get("authorization"))


def _provided_capabilities(headers: dict[str, str]) -> set[str]:
    return {part.strip() for part in headers.get("x-capabilities", "").split(",") if part.strip()}


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in _REDACT_FIELDS:
                out[key] = "***REDACTED***"
            else:
                out[key] = redact_sensitive(item)
        return out
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


def emit_audit_event(
    *,
    action: str,
    actor_id: str,
    tenant_id: str,
    role: str,
    correlation_id: str | None,
    metadata: dict[str, Any],
) -> None:
    logger.info(
        "enterprise_audit_event",
        extra={
            "audit": {
                "service": _SERVICE_NAME,
                "action": action,
                "actor_id": actor_id,
                "tenant_id": tenant_id,
                "role": role,
                "correlation_id": correlation_id or "",
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "policy_version": enterprise_policy_version(),
                "metadata": redact_sensitive(metadata),
            }
        },
    )


def _request_content_length(request: Request) -> int:
    try:
        return int(request.headers.get("content-length", "0"))
    except ValueError:
        return 0


def _write_payload_too_large(request: Request, *, max_write_payload_bytes: int) -> bool:
    return (
        request.method in _WRITE_METHODS
        and _request_content_length(request) > max_write_payload_bytes
    )


def _audit_identity_from_request(request: Request) -> _AuditIdentity:
    return _AuditIdentity(
        actor_id=request.headers.get("X-Actor-Id", "unknown"),
        tenant_id=request.headers.get("X-Tenant-Id", "default"),
        role=request.headers.get("X-Role", "unknown"),
        correlation_id=request.headers.get("X-Correlation-Id"),
    )


def _emit_denied_write_audit(request: Request, *, reason: str | None) -> None:
    identity = _audit_identity_from_request(request)
    emit_audit_event(
        action=f"DENY {request.method} {request.url.path}",
        actor_id=identity.actor_id,
        tenant_id=identity.tenant_id,
        role=identity.role,
        correlation_id=identity.correlation_id,
        metadata={"reason": reason},
    )


def _authorization_denied_response(reason: str | None) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": "Forbidden",
            "status": 403,
            "detail": "authorization_policy_denied",
            "reasonCode": reason or "authorization_policy_denied",
            "correlationId": "",
            "instance": "",
        },
    )


def _attach_policy_version_header(response: Response) -> None:
    response.headers["X-Enterprise-Policy-Version"] = enterprise_policy_version()


def _emit_write_audit_if_needed(request: Request, response: Response) -> None:
    if request.method not in _WRITE_METHODS:
        return
    identity = _audit_identity_from_request(request)
    emit_audit_event(
        action=f"{request.method} {request.url.path}",
        actor_id=identity.actor_id,
        tenant_id=identity.tenant_id,
        role=identity.role,
        correlation_id=identity.correlation_id,
        metadata={"status_code": response.status_code},
    )


def build_enterprise_audit_middleware() -> MiddlewareCallable:
    async def middleware(request: Request, call_next: MiddlewareNext) -> Response:
        max_write_payload_bytes = _env_int("ENTERPRISE_MAX_WRITE_PAYLOAD_BYTES", 1_048_576)
        if _write_payload_too_large(
            request,
            max_write_payload_bytes=max_write_payload_bytes,
        ):
            return JSONResponse(status_code=413, content={"detail": "payload_too_large"})

        authorized, reason = authorize_write_request(
            request.method, request.url.path, dict(request.headers)
        )
        if not authorized:
            _emit_denied_write_audit(request, reason=reason)
            return _authorization_denied_response(reason)

        response = await call_next(request)
        _attach_policy_version_header(response)
        _emit_write_audit_if_needed(request, response)
        return response

    return middleware
