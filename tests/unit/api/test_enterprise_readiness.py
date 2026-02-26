import json

from src.api.enterprise_readiness import (
    authorize_write_request,
    is_feature_enabled,
    redact_sensitive,
    validate_enterprise_runtime_config,
)


def test_feature_flags_resolution_by_tenant_and_role(monkeypatch):
    monkeypatch.setenv(
        "ENTERPRISE_FEATURE_FLAGS_JSON",
        json.dumps({"workflow.write": {"tenant-01": {"operator": True, "*": False}}}),
    )
    assert is_feature_enabled("workflow.write", "tenant-01", "operator") is True
    assert is_feature_enabled("workflow.write", "tenant-01", "viewer") is False


def test_redaction_masks_sensitive_fields():
    payload = {"authorization": "Bearer t", "details": {"password": "x", "safe": 1}}
    redacted = redact_sensitive(payload)
    assert redacted["authorization"] == "***REDACTED***"
    assert redacted["details"]["password"] == "***REDACTED***"
    assert redacted["details"]["safe"] == 1


def test_authorize_write_request_enforces_required_headers_when_enabled(monkeypatch):
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    allowed, reason = authorize_write_request("POST", "/rebalance", {})
    assert allowed is False
    assert reason.startswith("missing_headers:")


def test_authorize_write_request_enforces_capability_rules(monkeypatch):
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    monkeypatch.setenv(
        "ENTERPRISE_CAPABILITY_RULES_JSON",
        json.dumps({"POST /rebalance": "rebalance.write"}),
    )
    headers = {
        "X-Actor-Id": "a1",
        "X-Tenant-Id": "t1",
        "X-Role": "operator",
        "X-Correlation-Id": "c1",
        "X-Service-Identity": "dpm",
        "X-Capabilities": "rebalance.read",
    }
    denied, denied_reason = authorize_write_request("POST", "/rebalance/run", headers)
    assert denied is False
    assert denied_reason == "missing_capability:rebalance.write"

    headers["X-Capabilities"] = "rebalance.read,rebalance.write"
    allowed, allowed_reason = authorize_write_request("POST", "/rebalance/run", headers)
    assert allowed is True
    assert allowed_reason is None


def test_validate_enterprise_runtime_config_reports_rotation_issue(monkeypatch):
    monkeypatch.setenv("ENTERPRISE_SECRET_ROTATION_DAYS", "120")
    issues = validate_enterprise_runtime_config()
    assert "secret_rotation_days_out_of_range" in issues
