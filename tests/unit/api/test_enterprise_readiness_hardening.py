from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
import pytest

from src.api.enterprise_readiness import (
    _attach_policy_version_header,
    _audit_identity_from_request,
    _authz_key_material_issue,
    _authorization_denied_response,
    _has_service_identity,
    _missing_capability_reason,
    _missing_required_headers,
    _missing_required_headers_reason,
    _missing_service_identity_reason,
    _normalized_headers,
    _policy_version_issue,
    _provided_capabilities,
    _secret_rotation_issue,
    _write_authorization_failure_reason,
    _write_authorization_required,
    authorize_write_request,
    build_enterprise_audit_middleware,
    is_feature_enabled,
    redact_sensitive,
    validate_enterprise_runtime_config,
    write_authorization_required,
)


def _request(
    *,
    method: str = "POST",
    path: str = "/write",
    headers: dict[str, str] | None = None,
) -> Request:
    raw_headers = [
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in (headers or {}).items()
    ]
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": raw_headers,
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
        }
    )


def _enterprise_app() -> FastAPI:
    app = FastAPI()
    app.middleware("http")(build_enterprise_audit_middleware())

    @app.post("/write")
    async def write() -> dict[str, str]:
        return {"status": "ok"}

    return app


def test_enterprise_config_handles_invalid_json_and_integer_env(monkeypatch) -> None:
    monkeypatch.setenv("ENTERPRISE_FEATURE_FLAGS_JSON", "{not-json")
    monkeypatch.setenv("ENTERPRISE_SECRET_ROTATION_DAYS", "not-an-int")

    assert is_feature_enabled("missing", "tenant", "role") is False
    assert validate_enterprise_runtime_config() == []


def test_enterprise_runtime_config_reports_missing_policy_version(monkeypatch) -> None:
    monkeypatch.setenv("ENTERPRISE_POLICY_VERSION", " ")

    assert validate_enterprise_runtime_config() == ["missing_policy_version"]


def test_enterprise_runtime_config_issue_helpers_are_bounded(monkeypatch) -> None:
    monkeypatch.setenv("ENTERPRISE_POLICY_VERSION", " ")
    monkeypatch.setenv("ENTERPRISE_SECRET_ROTATION_DAYS", "0")
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    monkeypatch.setenv("ENTERPRISE_PRIMARY_KEY_ID", "")

    assert _policy_version_issue() == "missing_policy_version"
    assert _secret_rotation_issue() == "secret_rotation_days_out_of_range"
    assert _authz_key_material_issue() == "missing_primary_key_id"

    monkeypatch.setenv("ENTERPRISE_POLICY_VERSION", "1.2.3")
    monkeypatch.setenv("ENTERPRISE_SECRET_ROTATION_DAYS", "90")
    monkeypatch.setenv("ENTERPRISE_PRIMARY_KEY_ID", "kid-active")

    assert _policy_version_issue() is None
    assert _secret_rotation_issue() is None
    assert _authz_key_material_issue() is None


def test_capability_rule_ignores_non_matching_method(monkeypatch) -> None:
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    monkeypatch.setenv("ENTERPRISE_CAPABILITY_RULES_JSON", '{"GET /write": "read"}')
    headers = {
        "X-Actor-Id": "actor",
        "X-Tenant-Id": "tenant",
        "X-Role": "operator",
        "X-Correlation-Id": "corr",
        "Authorization": "Bearer service-token",
    }

    assert authorize_write_request("POST", "/write", headers) == (True, None)


def test_write_authorization_policy_helpers_normalize_required_headers(monkeypatch) -> None:
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    headers = _normalized_headers(
        {
            "X-Actor-Id": "actor",
            "X-Tenant-Id": "tenant",
            "X-Capabilities": " rebalance.read, rebalance.write ,, ",
            "Authorization": "Bearer service-token",
        }
    )

    assert _write_authorization_required("POST")
    assert not _write_authorization_required("GET")
    assert _missing_required_headers(headers) == ["x-correlation-id", "x-role"]
    assert _has_service_identity(headers)
    assert _provided_capabilities(headers) == {"rebalance.read", "rebalance.write"}


def test_write_authorization_policy_helpers_detect_missing_service_identity() -> None:
    headers = _normalized_headers(
        {
            "X-Actor-Id": "actor",
            "X-Tenant-Id": "tenant",
            "X-Role": "operator",
            "X-Correlation-Id": "corr",
        }
    )

    assert _missing_required_headers(headers) == []
    assert not _has_service_identity(headers)
    assert _provided_capabilities(headers) == set()


def test_write_authorization_failure_reason_helpers_preserve_denial_order(
    monkeypatch,
) -> None:
    monkeypatch.setenv("ENTERPRISE_CAPABILITY_RULES_JSON", '{"POST /write": "write"}')
    missing_headers = _normalized_headers({})
    missing_identity = _normalized_headers(
        {
            "X-Actor-Id": "actor",
            "X-Tenant-Id": "tenant",
            "X-Role": "operator",
            "X-Correlation-Id": "corr",
        }
    )
    missing_capability = _normalized_headers(
        {
            "X-Actor-Id": "actor",
            "X-Tenant-Id": "tenant",
            "X-Role": "operator",
            "X-Correlation-Id": "corr",
            "Authorization": "Bearer service-token",
            "X-Capabilities": "read",
        }
    )
    allowed = {**missing_capability, "x-capabilities": "read,write"}

    assert _missing_required_headers_reason(missing_headers).startswith("missing_headers:")
    assert _missing_service_identity_reason(missing_identity) == "missing_service_identity"
    assert (
        _missing_capability_reason(
            method="POST",
            path="/write",
            headers=missing_capability,
        )
        == "missing_capability:write"
    )
    assert _write_authorization_failure_reason(
        method="POST",
        path="/write",
        headers=missing_headers,
    ).startswith("missing_headers:")
    assert (
        _write_authorization_failure_reason(
            method="POST",
            path="/write",
            headers=missing_identity,
        )
        == "missing_service_identity"
    )
    assert (
        _write_authorization_failure_reason(
            method="POST",
            path="/write",
            headers=missing_capability,
        )
        == "missing_capability:write"
    )
    assert (
        _write_authorization_failure_reason(
            method="POST",
            path="/write",
            headers=allowed,
        )
        is None
    )


def test_enterprise_runtime_enforcement_reports_missing_identity(monkeypatch) -> None:
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    monkeypatch.setenv("ENTERPRISE_PRIMARY_KEY_ID", "")
    monkeypatch.setenv("ENTERPRISE_ENFORCE_RUNTIME_CONFIG", "true")

    with pytest.raises(RuntimeError, match="missing_primary_key_id"):
        validate_enterprise_runtime_config()


def test_write_authorization_requires_service_identity_after_required_headers(monkeypatch) -> None:
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    headers = {
        "X-Actor-Id": "actor",
        "X-Tenant-Id": "tenant",
        "X-Role": "operator",
        "X-Correlation-Id": "corr",
    }

    allowed, reason = authorize_write_request("POST", "/write", headers)

    assert allowed is False
    assert reason == "missing_service_identity"


def test_redaction_recurses_through_lists() -> None:
    assert redact_sensitive([{"token": "secret"}, {"safe": "value"}]) == [
        {"token": "***REDACTED***"},
        {"safe": "value"},
    ]


def test_enterprise_middleware_blocks_oversized_payload(monkeypatch) -> None:
    monkeypatch.setenv("ENTERPRISE_MAX_WRITE_PAYLOAD_BYTES", "5")
    client = TestClient(_enterprise_app())

    response = client.post("/write", content="too-large")

    assert response.status_code == 413
    assert response.json() == {"detail": "payload_too_large"}


def test_enterprise_middleware_rejects_invalid_content_length(monkeypatch) -> None:
    monkeypatch.setenv("ENTERPRISE_MAX_WRITE_PAYLOAD_BYTES", "5")
    client = TestClient(_enterprise_app())

    response = client.post(
        "/write",
        headers={
            "content-length": "not-a-number",
            "X-Actor-Id": "actor",
            "X-Tenant-Id": "tenant",
            "X-Role": "operator",
            "X-Correlation-Id": "corr",
            "X-Service-Identity": "lotus-manage",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "invalid_content_length"}


def test_enterprise_middleware_helpers_parse_size_and_audit_identity(monkeypatch) -> None:
    monkeypatch.setenv("ENTERPRISE_POLICY_VERSION", "2.1.0")
    request = _request(
        headers={
            "content-length": "6",
            "X-Actor-Id": "actor",
            "X-Tenant-Id": "tenant",
            "X-Role": "operator",
            "X-Correlation-Id": "corr",
        }
    )
    identity = _audit_identity_from_request(request)
    response = Response()
    denied_response = _authorization_denied_response("missing_service_identity")
    _attach_policy_version_header(response)

    assert identity.actor_id == "actor"
    assert identity.tenant_id == "tenant"
    assert identity.role == "operator"
    assert identity.correlation_id == "corr"
    assert write_authorization_required("POST") is False
    assert response.headers["X-Enterprise-Policy-Version"] == "2.1.0"
    assert denied_response.status_code == 403
    assert denied_response.media_type == "application/problem+json"


def test_enterprise_middleware_denies_and_audits_unauthorized_write(monkeypatch, caplog) -> None:
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    client = TestClient(_enterprise_app())

    with caplog.at_level("INFO", logger="enterprise_readiness"):
        response = client.post("/write")

    assert response.status_code == 403
    assert response.json()["detail"] == "authorization_policy_denied"
    assert response.json()["reasonCode"].startswith("missing_headers:")
    assert response.headers["content-type"].startswith("application/problem+json")
    assert any(record.getMessage() == "enterprise_audit_event" for record in caplog.records)
