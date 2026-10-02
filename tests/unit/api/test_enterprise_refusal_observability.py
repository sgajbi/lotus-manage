from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from io import StringIO

from fastapi.testclient import TestClient

from src.api.dependencies import get_composite_membership_application_service
from src.api.main import app
from src.api.observability import HTTP_REQUESTS_TOTAL, JsonFormatter
from src.api.services.composite_membership_application import (
    DpmCompositeMembershipApplicationService,
)
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository

_PATH = "/api/v1/rebalance/composites/PB_GLOBAL_BALANCED_USD/definitions/2026.10"
_ROUTE_TEMPLATE = "/api/v1/rebalance/composites/{composite_id}/definitions/{definition_version}"
_TRACE_ID = "0123456789abcdef0123456789abcdef"


def _payload() -> dict[str, object]:
    return {
        "display_name": "Private Banking Global Balanced Composite",
        "strategy_code": "GLOBAL_BALANCED",
        "reporting_currency": "USD",
        "inception_date": "2024-01-01",
        "eligibility_policy_version": "composite-eligibility.v1",
        "source_authority": {"policy_version": "composite-source-authority.v1"},
        "correlation_id": "corr-definition-001",
    }


def _headers(*, correlation_id: str) -> dict[str, str]:
    return {
        "X-Tenant-Id": "tenant-sg",
        "X-Actor-Id": "pm-ops",
        "X-Role": "DPM_COMPOSITE_ADMIN",
        "X-Correlation-Id": correlation_id,
        "X-Request-Id": f"req-{correlation_id}",
        "X-Service-Identity": "lotus-gateway",
        "X-Capabilities": "composites:write",
        "traceparent": f"00-{_TRACE_ID}-0123456789abcdef-01",
    }


def _streamed_oversized_body() -> Iterator[bytes]:
    yield b"123"
    yield b"456"


def _counter_value(*, endpoint: str, status_family: str) -> float:
    return float(
        HTTP_REQUESTS_TOTAL.labels(
            method="PUT",
            endpoint=endpoint,
            status_family=status_family,
        )._value.get()
    )


def _assert_correlated_enterprise_response(
    response,
    *,
    correlation_id: str,
    status_code: int,
    detail: str,
) -> None:
    assert response.status_code == status_code
    assert response.headers["X-Correlation-Id"] == correlation_id
    assert response.headers["X-Request-Id"] == f"req-{correlation_id}"
    assert response.headers["X-Trace-Id"] == _TRACE_ID
    assert response.headers["traceparent"] == f"00-{_TRACE_ID}-0000000000000001-01"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Enterprise-Policy-Version"] == "test-policy-v1"
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == status_code
    assert body["detail"] == detail
    assert body["correlationId"] == correlation_id
    assert body["instance"] == _PATH


def test_composed_app_observes_and_correlates_every_early_enterprise_refusal(
    monkeypatch,
    caplog,
) -> None:
    repository = InMemoryDpmCompositeRepository()
    app.dependency_overrides[get_composite_membership_application_service] = lambda: (
        DpmCompositeMembershipApplicationService(repository=repository)
    )
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    monkeypatch.setenv("ENTERPRISE_POLICY_VERSION", "test-policy-v1")
    monkeypatch.setenv(
        "ENTERPRISE_CAPABILITY_RULES_JSON",
        json.dumps({"PUT /api/v1/rebalance/composites": "composites:write"}),
    )
    unmatched_4xx_before = _counter_value(endpoint="unmatched", status_family="4xx")
    route_2xx_before = _counter_value(endpoint=_ROUTE_TEMPLATE, status_family="2xx")

    try:
        with caplog.at_level(logging.INFO), TestClient(app) as client:
            missing_role_headers = _headers(correlation_id="corr-missing-role")
            missing_role_headers.pop("X-Role")
            missing_role = client.put(_PATH, headers=missing_role_headers, json=_payload())

            missing_service_headers = _headers(correlation_id="corr-missing-service")
            missing_service_headers.pop("X-Service-Identity")
            missing_service = client.put(_PATH, headers=missing_service_headers, json=_payload())

            missing_capability_headers = _headers(correlation_id="corr-missing-capability")
            missing_capability_headers.pop("X-Capabilities")
            missing_capability = client.put(
                _PATH,
                headers=missing_capability_headers,
                json=_payload(),
            )

            invalid_length_headers = _headers(correlation_id="corr-invalid-length")
            invalid_length_headers["content-length"] = "not-a-number"
            invalid_length = client.put(_PATH, headers=invalid_length_headers, content=b"")

            monkeypatch.setenv("ENTERPRISE_MAX_WRITE_PAYLOAD_BYTES", "5")
            declared_oversized_headers = _headers(correlation_id="corr-declared-oversized")
            declared_oversized_headers["content-length"] = "6"
            declared_oversized = client.put(
                _PATH,
                headers=declared_oversized_headers,
                content=b"123456",
            )
            streamed_oversized = client.put(
                _PATH,
                headers=_headers(correlation_id="corr-streamed-oversized"),
                content=_streamed_oversized_body(),
            )

            refused_page = repository.list_definitions(tenant_id="tenant-sg", limit=10, offset=0)
            assert refused_page.count == 0

            monkeypatch.setenv("ENTERPRISE_MAX_WRITE_PAYLOAD_BYTES", "4096")
            accepted = client.put(
                _PATH,
                headers=_headers(correlation_id="corr-accepted"),
                json=_payload(),
            )
    finally:
        app.dependency_overrides.clear()

    refusal_expectations = (
        (missing_role, "corr-missing-role", 403, "authorization_policy_denied"),
        (missing_service, "corr-missing-service", 403, "authorization_policy_denied"),
        (missing_capability, "corr-missing-capability", 403, "authorization_policy_denied"),
        (invalid_length, "corr-invalid-length", 400, "invalid_content_length"),
        (declared_oversized, "corr-declared-oversized", 413, "payload_too_large"),
        (streamed_oversized, "corr-streamed-oversized", 413, "payload_too_large"),
    )
    for response, correlation_id, status_code, detail in refusal_expectations:
        _assert_correlated_enterprise_response(
            response,
            correlation_id=correlation_id,
            status_code=status_code,
            detail=detail,
        )

    assert accepted.status_code == 200
    assert accepted.headers["X-Correlation-Id"] == "corr-accepted"
    assert accepted.headers["X-Enterprise-Policy-Version"] == "test-policy-v1"
    assert repository.list_definitions(tenant_id="tenant-sg", limit=10, offset=0).count == 1

    completion_records = [
        record
        for record in caplog.records
        if record.name == "http.access" and record.getMessage() == "request.completed"
    ]
    assert len(completion_records) == 7
    refusal_records = [
        record for record in completion_records if record.extra_fields["status_family"] == "4xx"
    ]
    assert len(refusal_records) == 6
    assert {record.extra_fields["endpoint"] for record in refusal_records} == {"unmatched"}
    assert completion_records[-1].extra_fields["endpoint"] == _ROUTE_TEMPLATE
    assert completion_records[-1].extra_fields["status_family"] == "2xx"

    assert _counter_value(endpoint="unmatched", status_family="4xx") == (unmatched_4xx_before + 6)
    assert _counter_value(endpoint=_ROUTE_TEMPLATE, status_family="2xx") == route_2xx_before + 1

    denial_audits = [
        record
        for record in caplog.records
        if record.name == "enterprise_readiness"
        and record.getMessage() == "enterprise_audit_event"
        and record.audit["action"].startswith("DENY ")
    ]
    assert len(denial_audits) == 3
    assert {record.audit["metadata"]["reason"] for record in denial_audits} == {
        "missing_headers:x-role",
        "missing_service_identity",
        "missing_capability:composites:write",
    }


def test_generated_correlation_id_reconciles_missing_header_denial_audit_and_completion(
    monkeypatch,
    caplog,
) -> None:
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    monkeypatch.setenv("ENTERPRISE_POLICY_VERSION", "test-policy-v1")
    headers = _headers(correlation_id="unused")
    headers.pop("X-Correlation-Id")
    completion_stream = StringIO()
    completion_handler = logging.StreamHandler(completion_stream)
    completion_handler.setFormatter(JsonFormatter())
    completion_logger = logging.getLogger("http.access")
    completion_logger.addHandler(completion_handler)

    try:
        with caplog.at_level(logging.INFO), TestClient(app) as client:
            response = client.put(_PATH, headers=headers, json=_payload())
    finally:
        completion_logger.removeHandler(completion_handler)

    assert response.status_code == 403
    generated_correlation_id = response.headers["X-Correlation-Id"]
    assert generated_correlation_id.startswith("corr_")
    assert response.json()["correlationId"] == generated_correlation_id

    denial_audit = next(
        record
        for record in caplog.records
        if record.name == "enterprise_readiness"
        and record.getMessage() == "enterprise_audit_event"
        and record.audit["action"].startswith("DENY ")
    )
    completion = next(
        json.loads(line)
        for line in completion_stream.getvalue().splitlines()
        if json.loads(line)["message"] == "request.completed"
    )
    assert denial_audit.audit["metadata"]["reason"] == "missing_headers:x-correlation-id"
    assert denial_audit.audit["correlation_id"] == generated_correlation_id
    assert completion["correlation_id"] == generated_correlation_id
