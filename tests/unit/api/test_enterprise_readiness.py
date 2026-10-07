import json
import pytest

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.api.enterprise_readiness import (
    authorize_write_request,
    emit_audit_event,
    is_feature_enabled,
    redact_sensitive,
    validate_enterprise_runtime_config,
    build_enterprise_audit_middleware,
    risk_authority_policy,
)
from src.api.dependencies import get_risk_authority_context


def _risk_pilot_environment(monkeypatch):
    for name, value in {
        "ENTERPRISE_ENFORCE_AUTHZ": "true",
        "ENTERPRISE_POLICY_VERSION": "synthetic-policy-v1",
        "PRINCIPAL_RESOLUTION_POSTURE": "header-trust",
        "ENVIRONMENT": "local",
        "APP_PERSISTENCE_PROFILE": "LOCAL",
        "DPM_RISK_CONSUMER_SERVICE_IDENTITY": "manage-local-consumer",
        "DPM_RISK_REQUIRED_CAPABILITIES_JSON": json.dumps(
            {
                "concentration": "risk.concentration",
                "regime_scenario": "risk.regime",
                "risk_event_cohort": "risk.cohort",
            }
        ),
        "ENTERPRISE_CAPABILITY_RULES_JSON": json.dumps({"POST /probe": "manage.write"}),
    }.items():
        monkeypatch.setenv(name, value)


@pytest.mark.parametrize(
    "name,value",
    [
        ("DPM_RISK_REQUIRED_CAPABILITIES_JSON", "{}"),
        ("DPM_RISK_REQUIRED_CAPABILITIES_JSON", "[1]"),
        ("DPM_RISK_REQUIRED_CAPABILITIES_JSON", "not-json"),
        ("DPM_RISK_CONSUMER_SERVICE_IDENTITY", ""),
        ("ENTERPRISE_POLICY_VERSION", ""),
        ("PRINCIPAL_RESOLUTION_POSTURE", "verified"),
        ("PRINCIPAL_RESOLUTION_POSTURE", ""),
        ("ENVIRONMENT", "production"),
        ("ENVIRONMENT", ""),
        ("APP_PERSISTENCE_PROFILE", "PRODUCTION"),
        ("ENTERPRISE_ENFORCE_AUTHZ", "false"),
    ],
)
def test_risk_policy_refuses_unqualified_deployment(monkeypatch, name, value):
    _risk_pilot_environment(monkeypatch)
    assert risk_authority_policy() is not None
    monkeypatch.setenv(name, value)
    assert risk_authority_policy() is None


@pytest.mark.parametrize("capability", ["", 42, "risk.read,risk.write", "risk read", " risk.read"])
def test_risk_policy_rejects_malformed_mapping(monkeypatch, capability):
    _risk_pilot_environment(monkeypatch)
    mapping = {
        "concentration": capability,
        "regime_scenario": "risk.regime",
        "risk_event_cohort": "risk.cohort",
    }
    monkeypatch.setenv("DPM_RISK_REQUIRED_CAPABILITIES_JSON", json.dumps(mapping))
    assert risk_authority_policy() is None


def test_risk_context_uses_admitted_claims_without_credentials_or_elevation(monkeypatch):
    _risk_pilot_environment(monkeypatch)
    probe = FastAPI()
    probe.middleware("http")(build_enterprise_audit_middleware())

    @probe.post("/probe")
    def admitted(request: Request):
        context = get_risk_authority_context(request)
        return context.model_dump(mode="json") if context is not None else None

    headers = {
        "X-Actor-Id": "operator-A",
        "X-Tenant-Id": "tenant-A",
        "X-Role": "PM",
        "X-Correlation-Id": "corr-A",
        "Authorization": "Bearer never-forward-this",
        "X-Service-Identity": "caller-chosen-not-forwarded",
        "X-Capabilities": "manage.write,risk.cohort",
    }
    with TestClient(probe) as client:
        response = client.post("/probe", headers=headers)
        assert response.status_code == 200
        context = response.json()
        assert context["actor_id"] == "operator-A"
        assert context["tenant_id"] == "tenant-A"
        assert context["service_identity"] == "manage-local-consumer"
        assert context["authority_basis"] == "caller_asserted_header_trust"
        assert context["grants"] == [
            {"operation": "risk_event_cohort", "capability": "risk.cohort"}
        ]
        assert "never-forward-this" not in response.text
        assert "expires" not in response.text
        assert client.post("/probe", headers={**headers, "X-Actor-Id": "unknown"}).json() is None
        assert client.post("/probe", headers={**headers, "X-Tenant-Id": "   "}).status_code == 403
        assert (
            client.post("/probe", headers={**headers, "X-Capabilities": "risk.cohort"}).status_code
            == 403
        )
        monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "false")
        assert client.post("/probe", headers=headers).json() is None


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


def test_emit_audit_event_uses_manage_service_identity(caplog):
    with caplog.at_level("INFO", logger="enterprise_readiness"):
        emit_audit_event(
            action="POST /rebalance/simulate",
            actor_id="operator-1",
            tenant_id="tenant-1",
            role="operator",
            correlation_id="corr-1",
            metadata={"status_code": 200},
        )

    assert caplog.records
    assert caplog.records[-1].audit["service"] == "lotus-manage"
