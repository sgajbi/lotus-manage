"""Normal composition: signed HTTPS admission, PostgreSQL custody and provider-off replay."""

import json

import psycopg
import pytest

from src.core.composite_eligibility.monthly_evidence import HistoricalMonthlyPublicationReceipt
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from tests.composite_historical_policy_helpers import historical_contract_material
from tests.composite_monthly_amendment_helpers import (
    seed_complete_monthly_root,
    corrected_monthly_proposal,
)
from tests.composite_monthly_eligibility_helpers import BASE, HEADERS
from tests.integration.dpm.composites.historical_provider import historical_provider, utc_now
from tests.integration.dpm.composites.test_composite_configured_sources_postgres import (
    synthetic_sources,
)
from tests.integration.dpm.composites.test_composite_monthly_amendment_http_postgres import (
    amendment_command,
)
from tests.integration.dpm.network_runtime import disposable_database, native_api


MAKER = HEADERS | {
    "X-Service-Identity": "synthetic-historical-transport-proof",
    "X-Capabilities": "manage.write",
    "X-Actor-Id": "synthetic-historical-maker",
    "X-Correlation-Id": "historical-transport",
}
CHECKER = MAKER | {"X-Actor-Id": "synthetic-historical-checker"}
RESOLVER = BASE.removesuffix("/monthly-eligibility") + "/eligibility-evidence/resolve"


def put(client, url, command, *, checker=False):
    response = client.put(url, headers=CHECKER if checker else MAKER, json=command)
    assert response.status_code == 200, response.text
    return response.json()


def resolve(client, approval):
    binding = dict(
        product_name=approval["product_name"],
        product_version=approval["product_version"],
        revision=approval["proposal"]["evaluation_revision"],
        digest=approval["content_hash"],
    )
    response = client.post(RESOLVER, headers=MAKER, json=binding)
    assert response.status_code == 200, response.text
    return binding, response.json()


def assert_failed_admissions_leave_custody_unchanged(client, dsn, url, body, state):
    with psycopg.connect(dsn) as connection:
        before = connection.execute(
            "SELECT (SELECT count(*) FROM dpm_composite_monthly_policy_proposals), "
            "(SELECT count(*) FROM dpm_composite_monthly_evaluation_proposals), "
            "(SELECT count(*) FROM dpm_composite_membership_publications)"
        ).fetchone()
        for failure in ("signature", "duplicate", "revoked", "unavailable"):
            state["failure"] = failure
            refused = client.put(url, headers=MAKER, json=body)
            expected_status = 503 if failure == "unavailable" else 422
            expected_code = (
                "COMPOSITE_HISTORICAL_POLICY_ADMISSION_UNAVAILABLE"
                if failure == "unavailable"
                else "COMPOSITE_HISTORICAL_POLICY_RESPONSE_INVALID"
            )
            assert refused.status_code == expected_status, refused.text
            assert refused.json()["detail"]["code"] == expected_code
            state.setdefault("refusals", []).append(
                {"failure": failure, "status": refused.status_code, "body": refused.json()}
            )
            assert (
                connection.execute(
                    "SELECT (SELECT count(*) FROM dpm_composite_monthly_policy_proposals), "
                    "(SELECT count(*) FROM dpm_composite_monthly_evaluation_proposals), "
                    "(SELECT count(*) FROM dpm_composite_membership_publications)"
                ).fetchone()
                == before
            )
        state["failure"] = None


def admit_root(client, root, reference):
    policy_url = BASE + "/policies/2026-09/proposals/provider-admission-r1"
    body = {"reference": reference.model_dump(mode="json")}
    proposal = put(client, policy_url + "/historical-admission", body)
    approval_body = {"expected_proposal_content_hash": proposal["content_hash"]}
    approved = put(client, policy_url + "/approval", approval_body, checker=True)
    evaluation_url = BASE + "/evaluations/" + root.evaluation_revision
    command = dict(
        month="2026-09",
        policy_approval_content_hash=approved["content_hash"],
        parent_membership_revision=root.parent_membership_revision,
        parent_membership_content_hash=root.parent_membership_content_hash,
        attestation_version=root.universe.attestation_version,
        universe_content_hash=root.universe.content_hash,
        target_membership_revision=root.target_membership_revision,
        correlation_id=root.correlation_id,
    )
    evaluated = put(client, evaluation_url, command)
    checked_body = {"expected_proposal_content_hash": evaluated["content_hash"]}
    checked = put(client, evaluation_url + "/approval", checked_body, checker=True)
    binding, receipt = resolve(client, checked)
    replays = [
        (policy_url + "/historical-admission", body, False, proposal),
        (policy_url + "/approval", approval_body, True, approved),
        (evaluation_url, command, False, evaluated),
        (evaluation_url + "/approval", checked_body, True, checked),
    ]
    return replays, binding, receipt


def correct_root(client, repository, scope, receipt, source_state, provider):
    original = HistoricalMonthlyPublicationReceipt.model_validate(receipt)
    parent = repository.get_membership_revision(
        **scope, membership_revision=original.approval.proposal.target_membership_revision
    )
    material = corrected_monthly_proposal(
        original,
        parent,
        sequence=original.publication_sequence,
        proposed_at_override=utc_now(),
        historical_verifier=provider,
    )
    repository.save_universe_attestation(attestation=material.universe)
    source_state["assembly"] = material.source_assembly_evidence.assembly.model_dump(mode="json")
    url = BASE + "/evaluations/" + material.evaluation_revision
    command = amendment_command(material)
    proposed = put(client, url + "/source-amendment", command)
    approval_body = {"expected_proposal_content_hash": proposed["content_hash"]}
    approved = put(client, url + "/approval", approval_body, checker=True)
    binding, corrected = resolve(client, approved)
    assert corrected["product_version"] == "v4"
    assert (
        corrected["approval"]["proposal"]["policy_approval"]
        == receipt["approval"]["proposal"]["policy_approval"]
    )
    return (
        [
            (url + "/source-amendment", command, False, proposed),
            (url + "/approval", approval_body, True, approved),
        ],
        binding,
        corrected,
    )


@pytest.mark.parametrize("profile", ["v1", "v2"])
def test_composed_historical_https_admission_correction_and_offline_exact_replay(
    tmp_path, monkeypatch, profile
):
    material = historical_contract_material(definition_product_version=profile)
    root = material[3]
    baseline = InMemoryDpmCompositeRepository()
    scope, _, _ = seed_complete_monthly_root(
        baseline,
        parent_decided_at="2026-08-01T00:00:00.000000Z",
        definition_product_version=profile,
    )
    with (
        disposable_database() as dsn,
        synthetic_sources(monkeypatch) as (sources, source_state),
        historical_provider(tmp_path, monkeypatch, material[0].mapping) as (
            historical,
            state,
            provider,
        ),
    ):
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        repository.save_definition(definition=baseline.get_definition(**scope))
        repository.save_membership_revision(
            revision=baseline.get_membership_revision(
                **scope, membership_revision=root.parent_membership_revision
            )
        )
        repository.save_universe_attestation(attestation=root.universe)
        source_state["assembly"] = root.source_assembly_evidence.assembly.model_dump(mode="json")
        with native_api(dsn, composite_config=sources, historical_config=historical) as (client, _):
            policy_url = (
                BASE + "/policies/2026-09/proposals/provider-admission-r1/historical-admission"
            )
            body = {"reference": provider.mapping.reference.model_dump(mode="json")}
            assert_failed_admissions_leave_custody_unchanged(client, dsn, policy_url, body, state)
            replays, binding, original = admit_root(client, root, provider.mapping.reference)
            corrections, corrected_binding, corrected = correct_root(
                client, repository, scope, original, source_state, provider
            )
            assert original["product_version"] == "v3"
            for receipt in (original, corrected):
                mapping = receipt["approval"]["proposal"]["policy_approval"]["verification"][
                    "mapping"
                ]
                assert mapping == provider.mapping.model_dump(mode="json")
                assert receipt["completeness"] == "UNVERIFIED"
            assert {call["operation"] for call in state["calls"]} == {
                "POLICY_PROPOSAL",
                "POLICY_APPROVAL",
                "EVALUATION_PROPOSAL",
                "EVALUATION_APPROVAL",
            }
            (tmp_path / "composed-historical-custody.json").write_text(
                json.dumps(
                    {
                        "replays": replays + corrections,
                        "original": original,
                        "corrected": corrected,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        state["failure"] = "unavailable"
        source_state["deny"] = True
        calls, source_calls = len(state["calls"]), len(source_state["calls"])
        with native_api(dsn) as (fresh, _):
            for url, command, checker, expected in replays + corrections:
                assert put(fresh, url, command, checker=checker) == expected
            for locator, expected in ((binding, original), (corrected_binding, corrected)):
                response = fresh.post(RESOLVER, headers=MAKER, json=locator)
                assert response.status_code == 200, response.text
                assert response.json() == expected
                foreign = fresh.post(
                    RESOLVER, headers=MAKER | {"X-Tenant-Id": "foreign-tenant"}, json=locator
                )
                assert foreign.status_code != 200
        assert len(state["calls"]) == calls and len(source_state["calls"]) == source_calls
