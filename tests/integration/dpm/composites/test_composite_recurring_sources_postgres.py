"""Configured recurring monthly source behavior over registered HTTP and owned PostgreSQL."""

import json
from datetime import date, timedelta

from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from src.core.common.canonical import hash_canonical_payload
from src.api.services.composite_monthly_eligibility import (
    CompositeMonthlyEligibilityApplicationService,
    MonthlyProposalRequest,
    MonthlyApprovalRequest,
)
from tests.composite_monthly_eligibility_helpers import (
    command,
    retained_repository,
    source_snapshot,
    prospective_proposal_body,
)
from tests.composite_staged_eligibility_helpers import HEADERS
from tests.integration.dpm.composites.test_composite_configured_sources_postgres import (
    synthetic_sources,
)
from tests.integration.dpm.network_runtime import disposable_database, native_api
from tests.unit.dpm.infrastructure.test_composite_monthly_source_assembly import assembly_material
from tests.composite_recurring_economic_cases import economic_cases
from src.core.composite_universe import DpmCompositeUniverseAttestation
from src.core.composite_eligibility.policy import month_window
from tests.composite_recurring_economic_cases import transition_cases


BASE = "/api/v1/rebalance/composites/synthetic-composite/definitions/synthetic-definition/monthly-eligibility"
RUNTIME_HEADERS = HEADERS | {
    "X-Service-Identity": "synthetic-recurring-source-proof",
    "X-Capabilities": "manage.write",
    "X-Correlation-Id": "synthetic-recurring-source-proof",
}


def seed_recurring(repository, *, coverage_from="2026-09-01"):
    snapshot = source_snapshot()
    seed, universe = retained_repository(snapshot, coverage_from=coverage_from)
    scope = {
        "tenant_id": snapshot.tenant_id,
        "composite_id": snapshot.composite_id,
        "definition_version": snapshot.definition_version,
    }
    repository.save_definition(definition=seed.get_definition(**scope))
    repository.save_membership_revision(
        revision=seed.get_membership_revision(**scope, membership_revision="synthetic-membership")
    )
    repository.save_universe_attestation(attestation=universe)
    return universe


def retained_policy(repository, universe, *, month="2026-09"):
    """Explicit prospective synthetic fixture history; runtime clocks are not overridden."""
    scope = {
        "tenant_id": "synthetic-tenant",
        "composite_id": "synthetic-composite",
        "definition_version": "synthetic-definition",
    }
    first, _ = month_window(month)
    previous = date.fromisoformat(first) - timedelta(days=1)
    instant = previous.replace(day=20).isoformat() + "T01:00:00.000000Z"
    service = CompositeMonthlyEligibilityApplicationService(
        repository=repository, clock=lambda: instant
    )
    policy_body = prospective_proposal_body(universe)
    policy_body["layers"][0]["effective_from"] = first
    proposal = service.propose_policy(
        **scope,
        month=month,
        proposal_revision=f"recurring.policy.{month}.r1",
        actor_id="synthetic-maker",
        command=MonthlyProposalRequest.model_validate(policy_body),
    )
    return service.approve_policy(
        **scope,
        month=month,
        proposal_revision=proposal.proposal_revision,
        actor_id="synthetic-checker",
        command=MonthlyApprovalRequest(expected_proposal_content_hash=proposal.content_hash),
    )


def recurring_body(policy, universe):
    return {
        "month": "2026-09",
        "policy_approval_content_hash": policy.content_hash,
        "parent_membership_revision": "synthetic-membership",
        "parent_membership_content_hash": universe.membership_content_hash,
        "attestation_version": universe.attestation_version,
        "universe_content_hash": universe.content_hash,
        "target_membership_revision": "recurring.membership.r1",
        "correlation_id": "synthetic-recurring-source-proof",
    }


def test_registered_recurring_simulation_uses_configured_verified_monthly_source(monkeypatch):
    headers = RUNTIME_HEADERS
    with disposable_database() as dsn, synthetic_sources(monkeypatch) as (configuration, state):
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        universe = seed_recurring(repository)
        policy = retained_policy(repository, universe)
        body = recurring_body(policy, universe)
        url = BASE + "/evaluations/recurring.evaluation.r1"
        with native_api(dsn, composite_config=configuration) as (client, _):
            response = client.post(BASE + "/simulate", json=command(universe), headers=headers)
            assert response.status_code == 200, response.text
            result = response.json()
            assert result["official_activation"] == "UNAVAILABLE"
            assert result["population_verification"] == "UNVERIFIED"
            assessments = result["portfolios"][0]["assessments"]
            assert [(item["rule"], item["outcome"]) for item in assessments] == [
                ("SIGNIFICANT_FLOW", "PASS"),
                ("CASH", "PASS"),
                ("READINESS", "PASS"),
            ]
            assert assessments[0]["ratio"] == "0.05"
            evaluated = client.put(url, json=body, headers=headers)
            assert evaluated.status_code == 200, evaluated.text
            proposal = evaluated.json()
            evidence = proposal["source_assembly_evidence"]
            assert evidence["assembly"]["observations"] == proposal["observations"]
            assert len(evidence["assembly"]["inputs"]) == 5
            assert evidence["verification"]["posture"] == "SYNTHETIC_NON_CERTIFYING"
            approval_body = {"expected_proposal_content_hash": proposal["content_hash"]}
            self_approval = client.put(url + "/approval", json=approval_body, headers=headers)
            assert self_approval.status_code == 422, self_approval.text
            assert (
                self_approval.json()["detail"]["code"]
                == "COMPOSITE_ELIGIBILITY_SELF_APPROVAL_FORBIDDEN"
            )
            checker = headers | {"X-Actor-Id": "synthetic-checker"}
            approved = client.put(url + "/approval", json=approval_body, headers=checker)
            assert approved.status_code == 200, approved.text
            approval = approved.json()
            assert approval["proposal"] == proposal
            assert approval["official_activation"] == "UNAVAILABLE"
            future = client.put(
                BASE + "/evaluations/unapproved.future.month",
                json={**body, "month": "2026-10"},
                headers=headers,
            )
            assert future.status_code == 404, future.text
            assert (
                future.json()["detail"]["code"] == "COMPOSITE_ELIGIBILITY_APPROVED_POLICY_NOT_FOUND"
            )
        calls = list(state["calls"])
        assert calls == ["observations", "verification"] * 2
        with native_api(dsn) as (client, _):
            response = client.post(BASE + "/simulate", json=command(universe), headers=headers)
            assert response.status_code == 503, response.text
            replay = client.put(url, json=body, headers=headers)
            assert replay.status_code == 200 and replay.json() == proposal, replay.text
            replayed_approval = client.put(url + "/approval", json=approval_body, headers=checker)
            assert replayed_approval.status_code == 200, replayed_approval.text
            assert replayed_approval.json() == approval
            publications = client.get("/api/v1/rebalance/composites/publications", headers=headers)
            assert publications.status_code == 200, publications.text
            assert len(publications.json()["items"]) == 2
        assert state["calls"] == calls


def test_registered_recurring_source_refusals_never_retain_proposal_or_publication(monkeypatch):
    with disposable_database() as dsn, synthetic_sources(monkeypatch) as (configuration, state):
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        universe = seed_recurring(repository)
        policy = retained_policy(repository, universe)
        body = recurring_body(policy, universe)
        url = BASE + "/evaluations/refused.source.r1"
        with native_api(dsn, composite_config=configuration) as (client, _):
            for mutation, expected_code in (
                ("forged", "COMPOSITE_ELIGIBILITY_INPUT_INVALID"),
                ("mixed_cut", "COMPOSITE_ELIGIBILITY_INPUT_INVALID"),
                ("stale_revision", "COMPOSITE_ELIGIBILITY_SOURCE_REVISION_MISMATCH"),
                ("verifier_unavailable", "COMPOSITE_SOURCE_TRANSPORT_UNAVAILABLE"),
            ):
                _, assembly = assembly_material()
                state["forge_observations"] = mutation == "forged"
                state["deny"] = mutation == "verifier_unavailable"
                if mutation == "mixed_cut":
                    assembly["inputs"][0]["source_cut_id"] = "mixed-cut"
                if mutation == "stale_revision":
                    assembly["observations"]["source_revision"] = "stale.source.r1"
                    assembly["compatibility_binding"]["digest"] = hash_canonical_payload(
                        {"observations": assembly["observations"], "inputs": assembly["inputs"]}
                    )
                state["assembly"] = assembly
                refused = client.put(url, json=body, headers=RUNTIME_HEADERS)
                assert refused.status_code == (503 if state["deny"] else 422), refused.text
                assert refused.json()["detail"]["code"] == expected_code
                assert (
                    repository.get_monthly_evaluation_proposal(
                        tenant_id="synthetic-tenant",
                        composite_id="synthetic-composite",
                        definition_version="synthetic-definition",
                        evaluation_revision="refused.source.r1",
                    )
                    is None
                )
                publications = client.get(
                    "/api/v1/rebalance/composites/publications", headers=RUNTIME_HEADERS
                )
                assert publications.status_code == 200, publications.text
                assert len(publications.json()["items"]) == 1
            state["deny"] = state["forge_observations"] = False
            state.pop("assembly")
            recovered = client.put(url, json=body, headers=RUNTIME_HEADERS)
            assert recovered.status_code == 200, recovered.text


def economic_universe(repository, original, name, assembly, *, parent=None):
    wire = original.model_dump(mode="json")
    wire["attestation_version"] = f"economic.{name}.u1"
    wire["content_hash"] = ""
    snapshot = assembly["observations"]
    if parent is not None:
        wire.update(
            membership_revision=parent.membership_revision,
            membership_content_hash=parent.content_hash,
        )
        first, last = month_window(snapshot["month"])
        wire.update(
            coverage_from=first, coverage_to=last, attested_at=snapshot["source_generated_at"]
        )
    for product in wire["source_products"]:
        if product["authority_scope"] == "POLICY_INPUT":
            product.update(
                source_cut_id=snapshot["source_cut_id"],
                source_watermark=snapshot["source_revision"],
                content_hash=hash_canonical_payload(snapshot),
            )
    universe = DpmCompositeUniverseAttestation.model_validate(wire)
    repository.save_universe_attestation(attestation=universe)
    return universe


def assert_economic_result(name, proposal, status, outcomes, flow_ratio):
    result = proposal["evaluation"]
    assert result["expected_count"] == 1
    assert result["observed_count"] == (0 if name == "expected_member_missing" else 1)
    assert result["population_verification"] == "UNVERIFIED"
    portfolio = result["portfolios"][0]
    assert portfolio["status"] == status, name
    assessments = portfolio["assessments"]
    assert [item["rule"] for item in assessments] == ["SIGNIFICANT_FLOW", "CASH", "READINESS"]
    assert tuple(item["outcome"] for item in assessments) == outcomes, name
    assert assessments[0]["ratio"] == flow_ratio, name
    if name == "net_and_cash_equality":
        assert assessments[0]["numerator"] == "50"
        assert assessments[1]["ratio"] == "0.05"
    if name == "cash_above":
        assert assessments[1]["ratio"] == "0.051"
    if name in {"duplicate_exact", "linked_reversal"}:
        assert assessments[0]["admitted_flow_count"] == 2
    if name == "multiple_failures":
        assert assessments[0]["failure_reasons"] == ["SIGNIFICANT_FLOW_THRESHOLD_BREACH"]
        assert assessments[1]["failure_reasons"] == ["CASH_THRESHOLD_BREACH"]
        assert assessments[2]["failure_reasons"] == ["READINESS_FUNDED_FAILED"]
        assert assessments[2]["unknown_reasons"] == ["READINESS_INVESTED_UNKNOWN"]


def test_registered_recurring_economic_matrix_retains_all_rules_and_replays(monkeypatch, tmp_path):
    with disposable_database() as dsn, synthetic_sources(monkeypatch) as (configuration, state):
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        original = seed_recurring(repository)
        policy = retained_policy(repository, original)
        records = []
        with native_api(dsn, composite_config=configuration) as (client, _):
            for name, assembly, status, outcomes, flow_ratio in economic_cases():
                universe = economic_universe(repository, original, name, assembly)
                state["assembly"] = assembly
                body = recurring_body(policy, universe)
                body["target_membership_revision"] = f"economic.{name}.m1"
                url = BASE + f"/evaluations/economic.{name}.r1"
                response = client.put(url, json=body, headers=RUNTIME_HEADERS)
                assert response.status_code == 200, (name, response.text)
                proposal = response.json()
                assert_economic_result(name, proposal, status, outcomes, flow_ratio)
                assert proposal["source_assembly_evidence"]["assembly"] == assembly
                records.append({"case": name, "url": url, "body": body, "proposal": proposal})
        calls = list(state["calls"])
        assert calls == ["observations", "verification"] * len(records)
        with native_api(dsn) as (client, _):
            for record in records:
                response = client.put(record["url"], json=record["body"], headers=RUNTIME_HEADERS)
                assert response.status_code == 200, response.text
                assert response.json() == record["proposal"]
            publications = client.get(
                "/api/v1/rebalance/composites/publications", headers=RUNTIME_HEADERS
            )
            assert publications.status_code == 200, publications.text
            assert len(publications.json()["items"]) == 1
        assert state["calls"] == calls
        (tmp_path / "recurring-economic-matrix.json").write_text(
            json.dumps(records, indent=2), encoding="utf-8"
        )


def test_registered_recurring_exclusion_history_requires_full_monthly_reentry(
    monkeypatch, tmp_path
):
    scope = {
        "tenant_id": "synthetic-tenant",
        "composite_id": "synthetic-composite",
        "definition_version": "synthetic-definition",
    }
    checker = RUNTIME_HEADERS | {"X-Actor-Id": "synthetic-checker"}
    membership_path = BASE.removesuffix("/monthly-eligibility") + "/membership/"
    with disposable_database() as dsn, synthetic_sources(monkeypatch) as (configuration, state):
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        original = seed_recurring(repository, coverage_from="2026-07-01")
        genesis = repository.get_membership_revision(
            **scope, membership_revision="synthetic-membership"
        )
        parent = genesis
        records = []
        with native_api(dsn, composite_config=configuration) as (client, _):
            for month, assembly, status, outcomes in transition_cases():
                universe = economic_universe(repository, original, month, assembly, parent=parent)
                # A prior month's independent policy approval grants no authority for this month.
                if records:
                    denied_body = {**records[-1]["body"], "month": month}
                    before = list(state["calls"])
                    denied = client.put(
                        BASE + f"/evaluations/transition.{month}.unapproved",
                        json=denied_body,
                        headers=RUNTIME_HEADERS,
                    )
                    assert denied.status_code == 404, denied.text
                    assert (
                        denied.json()["detail"]["code"]
                        == "COMPOSITE_ELIGIBILITY_APPROVED_POLICY_NOT_FOUND"
                    )
                    assert state["calls"] == before
                policy = retained_policy(repository, universe, month=month)
                state["assembly"] = assembly
                body = {
                    **recurring_body(policy, universe),
                    "month": month,
                    "parent_membership_revision": parent.membership_revision,
                    "target_membership_revision": f"transition.{month}.membership.r1",
                }
                url = BASE + f"/evaluations/transition.{month}.r1"
                response = client.put(url, json=body, headers=RUNTIME_HEADERS)
                assert response.status_code == 200, response.text
                proposal = response.json()
                assert_economic_result(month, proposal, status, outcomes, "0.05")
                assert proposal["source_assembly_evidence"]["assembly"] == assembly
                approval_body = {"expected_proposal_content_hash": proposal["content_hash"]}
                approved = client.put(url + "/approval", json=approval_body, headers=checker)
                assert approved.status_code == 200, approved.text
                approval = approved.json()
                parent = repository.get_membership_revision(
                    **scope, membership_revision=body["target_membership_revision"]
                )
                assert parent.content_hash == approval["membership_content_hash"]
                assert parent.supersedes_membership_revision == body["parent_membership_revision"]
                records.append(
                    {
                        "month": month,
                        "url": url,
                        "body": body,
                        "proposal": proposal,
                        "approval_body": approval_body,
                        "approval": approval,
                        "membership": parent.model_dump(mode="json"),
                    }
                )
            assert [(d.effective_from, d.effective_to, d.status) for d in parent.decisions] == [
                ("2026-07-01", "2026-07-31", "EXCLUDED"),
                ("2026-08-01", "2026-08-31", "EXCLUDED"),
                ("2026-09-01", "2026-09-30", "INCLUDED"),
            ]
            assert (
                repository.get_membership_revision(
                    **scope, membership_revision="synthetic-membership"
                )
                == genesis
            )
            assert [(d.effective_from, d.effective_to, d.status) for d in genesis.decisions] == [
                ("2026-07-01", "2026-09-30", "INCLUDED")
            ]
            for as_of, expected in (
                ("2026-07-31", "EXCLUDED"),
                ("2026-08-01", "EXCLUDED"),
                ("2026-08-31", "EXCLUDED"),
                ("2026-09-01", "INCLUDED"),
            ):
                resolved = client.get(
                    membership_path + parent.membership_revision + "/as-of",
                    params={"as_of_date": as_of},
                    headers=RUNTIME_HEADERS,
                )
                assert resolved.status_code == 200, resolved.text
                assert [decision["status"] for decision in resolved.json()["decisions"]] == [
                    expected
                ]
        calls = list(state["calls"])
        assert calls == ["observations", "verification"] * 3
        with native_api(dsn) as (client, _):
            for record in records:
                replay = client.put(record["url"], json=record["body"], headers=RUNTIME_HEADERS)
                assert replay.status_code == 200 and replay.json() == record["proposal"], (
                    replay.text
                )
                approved = client.put(
                    record["url"] + "/approval", json=record["approval_body"], headers=checker
                )
                assert approved.status_code == 200 and approved.json() == record["approval"], (
                    approved.text
                )
            publications = client.get(
                "/api/v1/rebalance/composites/publications", headers=RUNTIME_HEADERS
            )
            assert publications.status_code == 200 and len(publications.json()["items"]) == 4
        assert state["calls"] == calls
        (tmp_path / "recurring-transition-history.json").write_text(
            json.dumps(records, indent=2), encoding="utf-8"
        )
