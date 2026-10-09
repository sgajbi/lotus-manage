"""Least-privilege reader admission and mutation isolation on actual middleware."""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.composite_read_authority import GRANTS_ENV, IDENTITY_HEADERS
from src.api.enterprise_readiness import authorize_write_request, build_enterprise_audit_middleware

ROOT = "/api/v1/rebalance/composites/composite-A/definitions/v2"
RESOLVER = ROOT + "/eligibility-evidence/resolve"
MEMBERSHIP = ROOT + "/membership/revision-1"
EVALUATION = ROOT + "/monthly-eligibility/evaluations/evaluation-1"
GRANT = {"service_identity": "report-reader", "actor_id": "report-actor", "tenant_id": "tenant-A"}
HEADERS = {
    "x-service-identity": "report-reader",
    "x-actor-id": "report-actor",
    "x-tenant-id": "tenant-A",
    "x-role": "REPORT_COMPOSITE_READER",
    "x-capabilities": "manage.read",
    "x-correlation-id": "controlled-read-proof",
}


@pytest.fixture(autouse=True)
def configured_reader(monkeypatch):
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    monkeypatch.setenv(GRANTS_ENV, json.dumps([GRANT]))
    monkeypatch.setenv(
        "ENTERPRISE_CAPABILITY_RULES_JSON",
        json.dumps(
            {
                "POST /api/v1": "manage.write",
                "PUT /api/v1": "manage.write",
                "PATCH /api/v1": "manage.write",
                "DELETE /api/v1": "manage.write",
            }
        ),
    )


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", RESOLVER),
        ("GET", MEMBERSHIP),
        ("GET", MEMBERSHIP + "/universe-attestations/evaluation-1"),
        ("GET", ROOT + "/membership/parent-1"),
        ("GET", EVALUATION),
        ("GET", "/api/v1/rebalance/composites/publications/2"),
    ],
)
def test_reader_exact_custody_operations_precede_broad_write_rule(method, path):
    assert authorize_write_request(method, path, HEADERS) == (True, None)


@pytest.mark.parametrize(
    "method,path",
    [
        ("PUT", ROOT),
        ("PUT", MEMBERSHIP),
        ("PUT", ROOT + "/monthly-eligibility/policies/proposal-1"),
        ("PUT", ROOT + "/monthly-eligibility/evaluations/evaluation-1/approval"),
        ("POST", "/api/v1/rebalance/simulate"),
        ("DELETE", ROOT),
        ("PATCH", MEMBERSHIP),
        ("POST", RESOLVER + "/extra"),
        ("POST", RESOLVER + "/"),
        ("POST", RESOLVER.replace("v2", "..")),
        ("POST", RESOLVER.replace("composite-A", "encoded%2Fsegment")),
        ("GET", MEMBERSHIP + "/extra"),
        ("POST", MEMBERSHIP),
        ("GET", EVALUATION + "/approval"),
        ("GET", EVALUATION + "/extra"),
        ("POST", EVALUATION),
    ],
)
def test_read_service_cannot_mutate_or_use_near_matching_paths(method, path):
    allowed, reason = authorize_write_request(method, path, HEADERS)
    assert not allowed
    assert reason == "composite_read_operation_forbidden"


@pytest.mark.parametrize(
    "name,value",
    [
        ("x-service-identity", "foreign-service"),
        ("x-actor-id", "foreign-actor"),
        ("x-tenant-id", "foreign-tenant"),
        ("x-role", "DPM_COMPOSITE_ADMIN"),
        ("x-capabilities", "manage.write"),
        ("x-capabilities", "manage.read,manage.write"),
        ("x-role", "REPORT_COMPOSITE_READER,DPM_COMPOSITE_ADMIN"),
    ],
)
@pytest.mark.parametrize("method,path", [("POST", RESOLVER), ("GET", MEMBERSHIP)])
def test_read_service_scope_and_privilege_assertions_fail_closed(name, value, method, path):
    assert authorize_write_request(method, path, HEADERS | {name: value})[0] is False


@pytest.mark.parametrize("name", IDENTITY_HEADERS)
def test_missing_reader_assertion_refuses(name):
    headers = dict(HEADERS)
    del headers[name]
    assert authorize_write_request("POST", RESOLVER, headers)[0] is False


@pytest.mark.parametrize(
    "configuration",
    [
        "",
        "invalid",
        "{}",
        "null",
        "[]",
        '[{"service_identity":"report-reader"}]',
        json.dumps([GRANT, GRANT]),
        json.dumps([GRANT | {"tenant_id": "tenant A"}]),
        json.dumps([GRANT | {"extra": "unrecognized"}]),
    ],
)
def test_invalid_or_absent_enrollment_never_supplies_read_authority(monkeypatch, configuration):
    monkeypatch.setenv(GRANTS_ENV, configuration)
    assert authorize_write_request("POST", RESOLVER, HEADERS)[0] is False


def test_enrolled_reader_cannot_impersonate_writer_with_asserted_write_capability():
    headers = HEADERS | {"x-role": "DPM_COMPOSITE_ADMIN", "x-capabilities": "manage.write"}
    assert authorize_write_request("PUT", ROOT, headers)[0] is False
    writer = headers | {"x-service-identity": "existing-writer"}
    assert authorize_write_request("PUT", ROOT, writer) == (True, None)
    assert authorize_write_request("POST", RESOLVER, writer) == (True, None)


def _app():
    app = FastAPI()
    app.middleware("http")(build_enterprise_audit_middleware())

    @app.api_route(RESOLVER, methods=["POST"])
    @app.api_route(MEMBERSHIP, methods=["GET"])
    def read():
        return {"read": True}

    return app


@pytest.mark.parametrize("name", IDENTITY_HEADERS)
@pytest.mark.parametrize("reader_first", [True, False])
def test_duplicate_headers_refuse_before_custody_lookup(name, reader_first):
    headers = [(key, value) for key, value in HEADERS.items() if key != name]
    pair = [(name, HEADERS[name]), (name, "foreign")]
    headers.extend(pair if reader_first else pair[::-1])
    with TestClient(_app()) as client:
        response = client.post(RESOLVER, headers=headers, json={})
    assert response.status_code == 403


def test_http_encoded_path_refuses_and_reads_emit_existing_audit_envelope(caplog):
    with TestClient(_app()) as client, caplog.at_level("INFO", logger="enterprise_readiness"):
        assert client.get(MEMBERSHIP, headers=HEADERS).status_code == 200
        assert client.post(RESOLVER, headers=HEADERS, json={}).status_code == 200
        assert client.post(RESOLVER.replace("v2", "%76%32"), headers=HEADERS).status_code == 403
    audits = [record.audit for record in caplog.records if hasattr(record, "audit")]
    assert [audit["action"] for audit in audits] == [
        "GET " + MEMBERSHIP,
        "POST " + RESOLVER,
        "DENY POST " + RESOLVER,
    ]
    assert all(audit["service"] == "lotus-manage" for audit in audits)
