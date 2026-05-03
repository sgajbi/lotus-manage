from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.api.enterprise_readiness import (
    authorize_write_request,
    build_enterprise_audit_middleware,
    is_feature_enabled,
    redact_sensitive,
    validate_enterprise_runtime_config,
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


def test_enterprise_middleware_treats_invalid_content_length_as_zero(monkeypatch) -> None:
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

    assert response.status_code == 200


def test_enterprise_middleware_denies_and_audits_unauthorized_write(monkeypatch, caplog) -> None:
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    client = TestClient(_enterprise_app())

    with caplog.at_level("INFO", logger="enterprise_readiness"):
        response = client.post("/write")

    assert response.status_code == 403
    assert response.json()["detail"] == "authorization_policy_denied"
    assert any(record.getMessage() == "enterprise_audit_event" for record in caplog.records)
