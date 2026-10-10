"""Registered present-admission routes retain original history without caller trust or clocks."""

from dataclasses import replace

from fastapi.testclient import TestClient

from src.api.dependencies import get_composite_monthly_eligibility_service, get_composite_repository
from src.api.main import app
from src.api.services.composite_monthly_eligibility import (
    CompositeMonthlyEligibilityApplicationService,
)
from src.api.composition.composite_source_service import build_composite_monthly_service
from src.core.composite_eligibility.source import MonthlyEligibilitySourceResolution
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from tests.composite_historical_policy_helpers import historical_contract_material
from tests.composite_monthly_amendment_helpers import seed_complete_monthly_root
from tests.composite_monthly_eligibility_helpers import BASE, HEADERS


def test_registered_historical_admission_evaluation_and_retained_default_unavailable_replay():
    port, expected, _, root, _, _ = historical_contract_material()
    port.calls.clear()
    original = InMemoryDpmCompositeRepository()
    scope, _, _ = seed_complete_monthly_root(
        original, parent_decided_at="2026-08-01T00:00:00.000000Z"
    )
    repository = InMemoryDpmCompositeRepository()
    repository.save_definition(definition=original.get_definition(**scope))
    repository.save_membership_revision(
        revision=original.get_membership_revision(
            **scope, membership_revision=root.parent_membership_revision
        )
    )
    repository.save_universe_attestation(attestation=root.universe)
    now = [expected.proposed_at]

    class Source:
        def resolve(self, request):
            return MonthlyEligibilitySourceResolution(
                observations=root.observations,
                owner_service="synthetic-source",
                source_assembly_evidence=root.source_assembly_evidence,
            )

    configuration = CompositeMonthlyEligibilityApplicationService(
        repository=repository, source=Source(), clock=lambda: now[0]
    )
    policy_url = BASE + "/policies/2026-09/proposals/" + expected.proposal_revision
    proposal_url = policy_url + "/historical-admission"
    body = {"reference": port.mapping.reference.model_dump(mode="json")}
    maker = HEADERS | {"X-Actor-Id": expected.proposed_by}
    checker = HEADERS | {"X-Actor-Id": "controlled-admission-checker"}
    prior = app.dependency_overrides.copy()
    app.dependency_overrides[get_composite_repository] = lambda: repository
    app.dependency_overrides[get_composite_monthly_eligibility_service] = lambda: configuration
    try:
        with TestClient(app) as client:
            denied = client.put(proposal_url, headers=maker, json=body)
            assert denied.status_code == 503, denied.text
            assert (
                denied.json()["detail"]["code"]
                == "COMPOSITE_HISTORICAL_POLICY_ADMISSION_UNAVAILABLE"
            )
            assert (
                repository.get_monthly_policy_proposal(
                    **scope, month="2026-09", proposal_revision=expected.proposal_revision
                )
                is None
            )
            for injected in (
                {"original_approved_at": port.mapping.original_approved_at},
                {"trust": {}},
                {"raw_original_base64": port.mapping.raw_original_base64},
            ):
                assert (
                    client.put(proposal_url, headers=maker, json=body | injected).status_code == 422
                )
            configuration = replace(configuration, historical_admission=port)
            proposed = client.put(proposal_url, headers=maker, json=body)
            assert proposed.status_code == 200, proposed.text
            assert proposed.json() == expected.model_dump(mode="json")
            assert client.get(policy_url, headers=maker).json() == proposed.json()
            assert (
                client.put(
                    proposal_url,
                    headers=maker,
                    json=body | {"reference": body["reference"] | {"revision": "different"}},
                ).status_code
                == 409
            )
            approval_body = {"expected_proposal_content_hash": proposed.json()["content_hash"]}
            assert (
                client.put(policy_url + "/approval", headers=maker, json=approval_body).status_code
                == 422
            )
            assert (
                client.put(
                    policy_url + "/approval",
                    headers=checker | {"X-Role": "DPM_REVIEWER"},
                    json=approval_body,
                ).status_code
                == 403
            )
            now[0] = "2026-10-10T01:01:00.000000Z"
            approved = client.put(policy_url + "/approval", headers=checker, json=approval_body)
            assert approved.status_code == 200, approved.text
            assert approved.json()["product_version"] == "v2"
            assert approved.json()["approved_at"] != port.mapping.original_approved_at
            assert (
                client.get(BASE + "/policies/2026-09/approval", headers=maker).json()
                == approved.json()
            )
            command = dict(
                month="2026-09",
                policy_approval_content_hash=approved.json()["content_hash"],
                parent_membership_revision=root.parent_membership_revision,
                parent_membership_content_hash=root.parent_membership_content_hash,
                attestation_version=root.universe.attestation_version,
                universe_content_hash=root.universe.content_hash,
                target_membership_revision=root.target_membership_revision,
                correlation_id=root.correlation_id,
            )
            evaluation_url = BASE + "/evaluations/" + root.evaluation_revision
            evaluation_maker = HEADERS | {"X-Actor-Id": root.proposed_by}
            evaluation_checker = HEADERS | {"X-Actor-Id": "controlled-evaluation-checker"}
            now[0] = root.proposed_at
            evaluated = client.put(evaluation_url, headers=evaluation_maker, json=command)
            assert evaluated.status_code == 200, evaluated.text
            assert evaluated.json()["product_version"] == "v3"
            now[0] = "2026-10-10T01:03:00.000000Z"
            checked_body = {"expected_proposal_content_hash": evaluated.json()["content_hash"]}
            checked = client.put(
                evaluation_url + "/approval", headers=evaluation_checker, json=checked_body
            )
            assert checked.status_code == 200, checked.text
            binding = dict(
                product_name=checked.json()["product_name"],
                product_version="v3",
                revision=root.evaluation_revision,
                digest=checked.json()["content_hash"],
            )
            resolver = BASE.removesuffix("/monthly-eligibility") + "/eligibility-evidence/resolve"
            resolved = client.post(resolver, headers=maker, json=binding)
            assert resolved.status_code == 200, resolved.text
            assert resolved.json()["product_version"] == "v3"
            assert (
                resolved.json()["approval"]["proposal"]["policy_approval"]["verification"][
                    "mapping"
                ]["raw_original_base64"]
                == port.mapping.raw_original_base64
            )
            calls = len(port.calls)
            configuration = replace(
                configuration,
                historical_admission=build_composite_monthly_service(
                    repository
                ).historical_admission,
            )
            for url, request, identity, expected_wire in (
                (proposal_url, body, maker, proposed.json()),
                (policy_url + "/approval", approval_body, checker, approved.json()),
                (evaluation_url, command, evaluation_maker, evaluated.json()),
                (evaluation_url + "/approval", checked_body, evaluation_checker, checked.json()),
            ):
                replay = client.put(url, headers=identity, json=request)
                assert replay.status_code == 200, replay.text
                assert replay.json() == expected_wire
            assert client.post(resolver, headers=maker, json=binding).json() == resolved.json()
            assert len(port.calls) == calls == 4
            assert len(repository._publications) == 2
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(prior)


def test_production_historical_configuration_cannot_enable_controlled_reference_adapter(
    monkeypatch,
):
    import pytest

    monkeypatch.setenv(
        "DPM_COMPOSITE_HISTORICAL_POLICY_ADMISSION_JSON",
        '{"signing_contract":"CONTROLLED_ED25519_RAW_BYTES_V1"}',
    )
    with pytest.raises(ValueError, match="validation error"):
        build_composite_monthly_service(InMemoryDpmCompositeRepository())
