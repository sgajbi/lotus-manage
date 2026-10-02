"""The registered write path and the shipped JSON formatter share one audit contract."""

import io
import json
import logging
from datetime import datetime

from fastapi.testclient import TestClient

from src.api.dependencies import get_composite_membership_application_service
from src.api.enterprise_readiness import emit_audit_event, enterprise_policy_version
from src.api.main import app
from src.api.observability import JsonFormatter
from src.api.services.composite_membership_application import (
    DpmCompositeMembershipApplicationService,
)
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository


def _audit_stream() -> tuple[io.StringIO, logging.StreamHandler]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    return stream, handler


def test_registered_composite_writes_preserve_audit_identity_and_outcome(monkeypatch):
    monkeypatch.delenv("ENTERPRISE_ENFORCE_AUTHZ", raising=False)
    repository = InMemoryDpmCompositeRepository()
    dependency = get_composite_membership_application_service
    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[dependency] = lambda: DpmCompositeMembershipApplicationService(
        repository=repository
    )
    stream, handler = _audit_stream()
    audit_logger = logging.getLogger("enterprise_readiness")
    audit_logger.addHandler(handler)
    base = "/api/v1/rebalance/composites/PB_GLOBAL_BALANCED_USD/definitions/2026.10"
    payload = {
        "display_name": "Private Banking Global Balanced Composite",
        "strategy_code": "GLOBAL_BALANCED",
        "reporting_currency": "USD",
        "inception_date": "2024-01-01",
        "eligibility_policy_version": "composite-eligibility.v1",
        "source_authority": {"policy_version": "composite-source-authority.v1"},
        "correlation_id": "corr-definition-001",
    }
    headers = {
        "X-Actor-Id": "synthetic-audit-actor",
        "X-Tenant-Id": "synthetic-audit-tenant",
        "X-Role": "DPM_COMPOSITE_ADMIN",
        "X-Correlation-Id": "audit-definition-001",
    }
    try:
        with TestClient(app) as client:
            created = client.put(base, headers=headers, json=payload)
            replay = client.put(base, headers=headers, json=payload)
            denied = client.put(base, headers=headers | {"X-Role": "DPM_VIEWER"}, json=payload)
            conflict = client.put(
                base, headers=headers, json=payload | {"display_name": "Different composite"}
            )
        assert [response.status_code for response in (created, replay, denied, conflict)] == [
            200,
            200,
            403,
            409,
        ]
        assert replay.json() == created.json()
        assert conflict.json()["detail"]["code"] == "COMPOSITE_DEFINITION_IMMUTABLE_CONFLICT"
        events = [json.loads(line) for line in stream.getvalue().splitlines()]
        assert len(events) == 4
        for event, response, role in zip(
            events,
            (created, replay, denied, conflict),
            ("DPM_COMPOSITE_ADMIN", "DPM_COMPOSITE_ADMIN", "DPM_VIEWER", "DPM_COMPOSITE_ADMIN"),
            strict=True,
        ):
            assert event["logger"] == "enterprise_readiness"
            assert event["message"] == "enterprise_audit_event"
            assert event["audit"]["service"] == "lotus-manage"
            assert event["audit"]["action"] == f"PUT {base}"
            assert event["audit"]["actor_id"] == "synthetic-audit-actor"
            assert event["audit"]["tenant_id"] == "synthetic-audit-tenant"
            assert event["audit"]["role"] == role
            assert event["audit"]["correlation_id"] == "audit-definition-001"
            assert event["audit"]["policy_version"] == enterprise_policy_version()
            assert event["audit"]["metadata"] == {"status_code": response.status_code}
            datetime.fromisoformat(event["audit"]["timestamp_utc"])
    finally:
        audit_logger.removeHandler(handler)
        handler.close()
        app.dependency_overrides = original_overrides


def test_policy_denial_preserves_reason_and_asserted_identity(monkeypatch):
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    stream, handler = _audit_stream()
    audit_logger = logging.getLogger("enterprise_readiness")
    audit_logger.addHandler(handler)
    try:
        with TestClient(app) as client:
            denied = client.post(
                "/api/v1/rebalance/simulate",
                headers={"X-Actor-Id": "synthetic-actor", "X-Tenant-Id": "synthetic-tenant"},
                json={},
            )
        assert denied.status_code == 403
        (event,) = [json.loads(line) for line in stream.getvalue().splitlines()]
        assert event["audit"]["action"] == "DENY POST /api/v1/rebalance/simulate"
        assert event["audit"]["actor_id"] == "synthetic-actor"
        assert event["audit"]["tenant_id"] == "synthetic-tenant"
        assert event["audit"]["role"] == "unknown"
        assert event["audit"]["metadata"]["reason"].startswith("missing_headers:")
    finally:
        audit_logger.removeHandler(handler)
        handler.close()


def test_emitter_and_formatter_redact_metadata_without_serializing_unlisted_fields():
    stream, handler = _audit_stream()
    audit_logger = logging.getLogger("enterprise_readiness")
    audit_logger.addHandler(handler)
    try:
        emit_audit_event(
            action="PUT /synthetic",
            actor_id="synthetic-actor",
            tenant_id="synthetic-tenant",
            role="operator",
            correlation_id="synthetic-correlation",
            metadata={
                "status_code": 200,
                "authorization": "Bearer sensitive-token",
                "nested": {"password": "sensitive-password", "outcome": "accepted"},
            },
        )
        (event,) = [json.loads(line) for line in stream.getvalue().splitlines()]
        assert event["audit"]["metadata"] == {
            "status_code": 200,
            "authorization": "***REDACTED***",
            "nested": {"password": "***REDACTED***", "outcome": "accepted"},
        }
        assert "sensitive-token" not in stream.getvalue()
        assert "sensitive-password" not in stream.getvalue()
    finally:
        audit_logger.removeHandler(handler)
        handler.close()

    record = logging.LogRecord(
        "enterprise_readiness", logging.INFO, __file__, 1, "ordinary", (), None
    )
    record.audit = {"actor_id": "not-an-audit-event"}
    record.password = "must-not-serialize"
    ordinary = json.loads(JsonFormatter().format(record))
    assert "audit" not in ordinary
    assert "password" not in ordinary

    record.msg = "enterprise_audit_event"
    assert "audit" not in json.loads(JsonFormatter().format(record))
    record.audit = {
        "service": "lotus-manage",
        "action": "PUT /synthetic",
        "actor_id": "synthetic-actor",
        "tenant_id": "synthetic-tenant",
        "role": "operator",
        "correlation_id": "synthetic-correlation",
        "timestamp_utc": "2026-10-02T00:00:00+00:00",
        "policy_version": "enterprise-policy.v1",
        "metadata": {"authorization": "Bearer sensitive-token", "status_code": 200},
        "unexpected_secret": "must-not-serialize",
    }
    safe = json.loads(JsonFormatter().format(record))
    assert safe["audit"]["metadata"]["authorization"] == "***REDACTED***"
    assert "unexpected_secret" not in safe["audit"]
    assert "must-not-serialize" not in json.dumps(safe)
