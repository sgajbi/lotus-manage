"""Registered read-only API with explicitly synthetic source ownership."""

import pytest
from fastapi.testclient import TestClient

from tests.composite_monthly_eligibility_helpers import (
    BASE,
    HEADERS,
    source_snapshot,
    retained_repository,
    command,
    prospective_proposal_body,
)
from src.api.dependencies import get_composite_monthly_eligibility_service
from src.api.main import app
from src.api.services.composite_monthly_eligibility import (
    CompositeMonthlyEligibilityApplicationService,
)
from src.core.composite_eligibility.source import MonthlyEligibilitySourceResolution


@pytest.fixture
def api():
    snapshot = source_snapshot()
    repository, attestation = retained_repository(snapshot)
    resolved = []

    class SyntheticSource:
        def resolve(self, request):
            resolved.append(request)
            return MonthlyEligibilitySourceResolution(snapshot, owner_service="synthetic-source")

    service = CompositeMonthlyEligibilityApplicationService(
        repository=repository,
        source=SyntheticSource(),
        clock=lambda: "2026-10-01T01:00:00.000000Z",
    )
    prior = app.dependency_overrides.copy()
    app.dependency_overrides[get_composite_monthly_eligibility_service] = lambda: service
    try:
        with TestClient(app) as client:
            yield client, repository, snapshot, attestation, resolved
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(prior)


def test_registered_simulation_pins_separate_cuts_without_publishing(api):
    client, repository, snapshot, attestation, resolved = api
    before = repository.list_publications(tenant_id=snapshot.tenant_id, after_sequence=0, limit=10)
    response = client.post(BASE + "/simulate", json=command(attestation), headers=HEADERS)
    assert response.status_code == 200, response.text
    wire = response.json()
    assert wire["included_count"] == 1
    assert wire["official_activation"] == "UNAVAILABLE"
    assert wire["population_verification"] == "UNVERIFIED"
    assert wire["universe_content_hash"] == attestation.content_hash
    assert wire["source_cut_id"] == snapshot.source_cut_id != attestation.source_cut_id
    assert resolved[0].scope.strategy_code == "synthetic-strategy"
    assert resolved[0].owner_service == "synthetic-source"
    assert resolved[0].expected_source_revision == snapshot.source_revision
    flow = wire["portfolios"][0]["assessments"][0]
    assert flow["numerator"] == "50"
    assert flow["ratio"] == "0.05"
    assert flow["outcome"] == "PASS"
    assert resolved[0].expected_content_hash == wire["input_content_hash"]
    assert (
        repository.list_publications(tenant_id=snapshot.tenant_id, after_sequence=0, limit=10)
        == before
    )


def test_default_source_refuses_with_no_write(api):
    client, repository, _, attestation, resolved = api
    service = CompositeMonthlyEligibilityApplicationService(repository=repository)
    app.dependency_overrides[get_composite_monthly_eligibility_service] = lambda: service
    response = client.post(BASE + "/simulate", json=command(attestation), headers=HEADERS)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "COMPOSITE_ELIGIBILITY_SOURCE_UNAVAILABLE"
    assert not resolved


@pytest.mark.parametrize("candidate_cash,changed", [("0.04", True), ("0.05", False)])
def test_registered_diff_pins_both_inputs_and_explains_cash_change(api, candidate_cash, changed):
    client, repository, snapshot, attestation, resolved = api
    body = command(attestation)
    body["baseline_layers"] = [dict(layer) for layer in body["layers"]]
    body["layers"][0]["cash_threshold"] = candidate_cash
    response = client.post(BASE + "/diff", json=body, headers=HEADERS)
    assert response.status_code == 200, response.text
    wire = response.json()
    assert wire["policy_content_changed"] == changed
    assert wire["changed_portfolio_count"] == int(changed)
    assert wire["baseline"]["evaluated_at"] == wire["candidate"]["evaluated_at"]
    assert wire["baseline"]["input_content_hash"] == wire["candidate"]["input_content_hash"]
    assert len(resolved) == 2
    assert (
        repository.list_membership_revisions(
            tenant_id=snapshot.tenant_id,
            composite_id=snapshot.composite_id,
            definition_version=snapshot.definition_version,
            limit=10,
            offset=0,
        ).count
        == 1
    )
    if changed:
        assert wire["differences"] == [
            {
                "portfolio_id": "synthetic-member",
                "baseline_status": "INCLUDED",
                "candidate_status": "EXCLUDED",
                "changed_rules": ["CASH"],
            }
        ]
    else:
        assert wire["differences"] == []


def test_source_exception_does_not_publish_unapproved_error_text(api):
    client, repository, _, attestation, _ = api

    class BrokenSource:
        def resolve(self, request):
            raise ValueError("COMPOSITE_PRIVATE_ACCOUNT_1234")

    service = CompositeMonthlyEligibilityApplicationService(
        repository=repository, source=BrokenSource()
    )
    app.dependency_overrides[get_composite_monthly_eligibility_service] = lambda: service
    response = client.post(BASE + "/simulate", json=command(attestation), headers=HEADERS)
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "COMPOSITE_ELIGIBILITY_INPUT_INVALID",
        "message": "COMPOSITE_ELIGIBILITY_INPUT_INVALID",
    }


def test_registered_policy_control_is_independent_immutable_and_never_activates(api):
    client, repository, snapshot, attestation, _ = api
    proposal_url = BASE + "/policies/2026-11/proposals/synthetic-r1"
    body = prospective_proposal_body(attestation)
    assert client.get(BASE + "/policies/2026-11/approval", headers=HEADERS).status_code == 404
    proposal = client.put(proposal_url, json=body, headers=HEADERS)
    assert proposal.status_code == 200, proposal.text
    wire = proposal.json()
    assert wire["proposed_by"] == HEADERS["X-Actor-Id"]
    assert wire["proposed_at"] == "2026-10-01T01:00:00.000000Z"
    assert client.put(proposal_url, json=body, headers=HEADERS).json() == wire
    assert client.get(proposal_url, headers=HEADERS).json() == wire
    approval_body = {"expected_proposal_content_hash": wire["content_hash"]}
    assert (
        client.put(proposal_url + "/approval", json=approval_body, headers=HEADERS).status_code
        == 422
    )
    checker = HEADERS | {"X-Actor-Id": "synthetic-checker"}
    approval = client.put(proposal_url + "/approval", json=approval_body, headers=checker)
    assert approval.status_code == 200, approval.text
    approved = approval.json()
    assert approved["proposal"] == wire
    assert approved["approved_by"] == "synthetic-checker"
    assert approved["official_activation"] == "UNAVAILABLE"
    assert (
        client.put(proposal_url + "/approval", json=approval_body, headers=checker).json()
        == approved
    )
    assert client.get(BASE + "/policies/2026-11/approval", headers=HEADERS).json() == approved
    assert client.get(proposal_url, headers=HEADERS | {"X-Tenant-Id": "foreign"}).status_code == 404
    assert (
        len(
            repository.list_publications(
                tenant_id=snapshot.tenant_id, after_sequence=0, limit=10
            ).items
        )
        == 1
    )


def test_policy_mutation_stale_revision_and_conflicting_active_configuration_refuse(api):
    client, _, _, attestation, _ = api
    url = BASE + "/policies/2026-11/proposals/synthetic-r1"
    body = prospective_proposal_body(attestation)
    wire = client.put(url, json=body, headers=HEADERS).json()
    body["attachments"][0]["digest"] = "sha256:" + "c" * 64
    assert client.put(url, json=body, headers=HEADERS).status_code == 409
    checker = HEADERS | {"X-Actor-Id": "synthetic-checker"}
    stale = client.put(
        url + "/approval",
        headers=checker,
        json={"expected_proposal_content_hash": "sha256:" + "0" * 64},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "COMPOSITE_ELIGIBILITY_STALE_PROPOSAL"
    approved = client.put(
        url + "/approval",
        headers=checker,
        json={"expected_proposal_content_hash": wire["content_hash"]},
    )
    assert approved.status_code == 200
    alternative = BASE + "/policies/2026-11/proposals/synthetic-r2"
    candidate = client.put(alternative, json=body, headers=HEADERS).json()
    conflict = client.put(
        alternative + "/approval",
        headers=checker,
        json={"expected_proposal_content_hash": candidate["content_hash"]},
    )
    assert conflict.status_code == 409
    assert (
        client.get(BASE + "/policies/2026-11/approval", headers=HEADERS).json() == approved.json()
    )


def test_retrospective_policy_and_unauthorized_checker_refuse(api):
    client, repository, _, attestation, _ = api
    body = prospective_proposal_body(attestation)
    assert (
        client.put(BASE + "/policies/2026-09/proposals/r1", json=body, headers=HEADERS).status_code
        == 422
    )
    url = BASE + "/policies/2026-11/proposals/r1"
    wire = client.put(url, json=body, headers=HEADERS).json()
    expected = {"expected_proposal_content_hash": wire["content_hash"]}
    unauthorized = HEADERS | {"X-Actor-Id": "synthetic-checker", "X-Role": "DPM_PORTFOLIO_MANAGER"}
    assert client.put(url + "/approval", json=expected, headers=unauthorized).status_code == 403
    service = CompositeMonthlyEligibilityApplicationService(
        repository=repository, clock=lambda: "2026-11-01T00:00:00.000000Z"
    )
    app.dependency_overrides[get_composite_monthly_eligibility_service] = lambda: service
    expired = client.put(
        url + "/approval", json=expected, headers=HEADERS | {"X-Actor-Id": "synthetic-checker"}
    )
    assert expired.status_code == 422
    assert (
        expired.json()["detail"]["code"] == "COMPOSITE_ELIGIBILITY_RETROSPECTIVE_POLICY_FORBIDDEN"
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("proposed_by", "forged"),
        ("proposed_at", "2026-08-01T00:00:00.000000Z"),
        ("tenant_id", "foreign"),
    ],
)
def test_proposal_body_cannot_supply_custody_authority(api, field, value):
    client, _, _, attestation, _ = api
    response = client.put(
        BASE + "/policies/2026-11/proposals/r1",
        headers=HEADERS,
        json=prospective_proposal_body(attestation) | {field: value},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("tenant_id", "foreign"),
        ("portfolios", []),
        ("evaluated_at", "2099-01-01T00:00:00.000000Z"),
        ("official_activation", "APPROVED"),
    ],
)
def test_body_cannot_override_identity_source_clock_or_activation(api, field, value):
    client, _, _, attestation, resolved = api
    response = client.post(
        BASE + "/simulate", json=command(attestation) | {field: value}, headers=HEADERS
    )
    assert response.status_code == 422
    assert not resolved


@pytest.mark.parametrize(
    "headers,status",
    [
        ({}, 403),
        (HEADERS | {"X-Role": "DPM_COMPOSITE_CONSUMER"}, 403),
        (HEADERS | {"X-Tenant-Id": "foreign-tenant"}, 404),
    ],
)
def test_scope_and_role_refuse_before_source_resolution(api, headers, status):
    client, _, _, attestation, resolved = api
    response = client.post(BASE + "/simulate", json=command(attestation), headers=headers)
    assert response.status_code == status
    assert not resolved


def test_validate_uses_retained_strategy_and_refuses_foreign_layer(api):
    client, _, _, attestation, resolved = api
    body = {key: command(attestation)[key] for key in ("month", "layers")}
    response = client.post(BASE + "/validate", json=body, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["scope"]["strategy_code"] == "synthetic-strategy"
    body["layers"].append(body["layers"][0] | {"level": "TENANT", "tenant_id": "foreign"})
    assert client.post(BASE + "/validate", json=body, headers=HEADERS).status_code == 422
    assert not resolved


@pytest.mark.parametrize("name", ["X-Tenant-Id", "X-Actor-Id", "X-Role"])
@pytest.mark.parametrize("duplicate", [True, False])
def test_ambiguous_identity_headers_refuse_before_source(api, name, duplicate):
    client, _, _, attestation, resolved = api
    headers = list(HEADERS.items())
    if duplicate:
        headers.append((name, "foreign-identity"))
    else:
        headers = [
            (key, value + ",foreign-identity" if key == name else value) for key, value in headers
        ]
    response = client.post(BASE + "/simulate", json=command(attestation), headers=headers)
    assert response.status_code == 403
    assert not resolved


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("month", "2026-10", "COMPOSITE_ELIGIBILITY_SOURCE_MONTH_MISMATCH"),
        ("tenant_id", "foreign", "COMPOSITE_ELIGIBILITY_SOURCE_SCOPE_MISMATCH"),
        ("source_cut_id", "foreign", "COMPOSITE_ELIGIBILITY_SOURCE_CUT_MISMATCH"),
        ("reporting_currency", "EUR", "COMPOSITE_ELIGIBILITY_SOURCE_CURRENCY_MISMATCH"),
        ("source_revision", "mutated", "COMPOSITE_ELIGIBILITY_SOURCE_REVISION_MISMATCH"),
    ],
)
def test_source_response_cannot_substitute_pinned_material(api, field, value, code):
    client, _, snapshot, attestation, _ = api
    setattr(snapshot, field, value)
    response = client.post(BASE + "/simulate", json=command(attestation), headers=HEADERS)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == code
