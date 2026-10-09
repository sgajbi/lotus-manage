"""Registered amendment admission and immutable retries with explicit synthetic sources."""

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import (
    get_composite_monthly_eligibility_service,
    get_composite_repository,
)
from src.api.main import app
from src.api.services.composite_monthly_eligibility import (
    CompositeMonthlyEligibilityApplicationService,
)
from src.core.composite_eligibility.source import MonthlyEligibilitySourceResolution
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from tests.composite_monthly_amendment_helpers import (
    corrected_monthly_proposal,
    seed_complete_monthly_root,
)
from tests.composite_monthly_eligibility_helpers import BASE, HEADERS


@pytest.mark.parametrize("profile", ["v1", "v2"])
def test_registered_amendment_source_admission_versioned_resolution_and_retry(profile):
    repository = InMemoryDpmCompositeRepository()
    scope, original, parent = seed_complete_monthly_root(
        repository, definition_product_version=profile
    )
    material = corrected_monthly_proposal(original, parent, sequence=original.publication_sequence)
    repository.save_universe_attestation(attestation=material.universe)
    state = {"available": False, "calls": 0}

    class Source:
        def resolve(self, request):
            state["calls"] += 1
            assert request.source_cut_id == material.observations.source_cut_id
            return MonthlyEligibilitySourceResolution(
                observations=material.observations if state["available"] else None,
                owner_service="synthetic-source",
                source_assembly_evidence=material.source_assembly_evidence,
            )

    configuration = CompositeMonthlyEligibilityApplicationService(
        repository=repository, source=Source(), clock=lambda: material.proposed_at
    )
    command = {
        "month": material.evaluation.month,
        "policy_approval_content_hash": material.policy_approval.content_hash,
        "parent_membership_revision": material.parent_membership_revision,
        "parent_membership_content_hash": material.parent_membership_content_hash,
        "attestation_version": material.universe.attestation_version,
        "universe_content_hash": material.universe.content_hash,
        "target_membership_revision": material.target_membership_revision,
        "correlation_id": material.correlation_id,
        "amendment": material.amendment.model_dump(mode="json"),
    }
    headers = HEADERS | {"X-Actor-Id": material.proposed_by}
    checker = HEADERS | {"X-Actor-Id": "synthetic-route-independent-checker"}
    url = BASE + "/evaluations/" + material.evaluation_revision
    resolver = BASE.removesuffix("/monthly-eligibility") + "/eligibility-evidence/resolve"
    prior = app.dependency_overrides.copy()
    app.dependency_overrides[get_composite_repository] = lambda: repository
    app.dependency_overrides[get_composite_monthly_eligibility_service] = lambda: configuration
    try:
        with TestClient(app) as client:
            unavailable = client.put(url + "/source-amendment", headers=headers, json=command)
            assert unavailable.status_code == 503, unavailable.text
            assert (
                repository.get_monthly_evaluation_proposal(
                    **scope, evaluation_revision=material.evaluation_revision
                )
                is None
            )
            state["available"] = True
            proposed = client.put(url + "/source-amendment", headers=headers, json=command)
            assert proposed.status_code == 200, proposed.text
            assert proposed.json() == material.model_dump(mode="json")
            approval_request = {"expected_proposal_content_hash": material.content_hash}
            approved = client.put(url + "/approval", headers=checker, json=approval_request)
            assert approved.status_code == 200, approved.text
            binding = {
                "product_name": "CompositeMonthlyEvaluationApproval",
                "product_version": "v2",
                "revision": material.evaluation_revision,
                "digest": approved.json()["content_hash"],
            }
            receipt = client.post(resolver, headers=headers, json=binding)
            assert receipt.status_code == 200, receipt.text
            assert receipt.json()["product_version"] == "v2"
            assert receipt.json()["lineage"] == command["amendment"]
            wrong_version = client.post(
                resolver, headers=headers, json=binding | {"product_version": "v1"}
            )
            assert wrong_version.status_code == 422, wrong_version.text
            assert wrong_version.json()["detail"]["code"] == (
                "COMPOSITE_MONTHLY_EVIDENCE_BINDING_MISMATCH"
            )
            replay = client.put(url + "/source-amendment", headers=headers, json=command)
            assert replay.status_code == 200 and replay.json() == proposed.json()
            ordinary = client.put(
                url, headers=headers, json={k: v for k, v in command.items() if k != "amendment"}
            )
            assert ordinary.status_code == 409, ordinary.text
            changed = client.put(
                url + "/source-amendment",
                headers=headers,
                json=command | {"amendment": command["amendment"] | {"reason": "different"}},
            )
            assert changed.status_code == 409, changed.text
            approved_replay = client.put(url + "/approval", headers=checker, json=approval_request)
            assert approved_replay.status_code == 200
            assert approved_replay.json() == approved.json()
            old = repository.resolve_monthly_eligibility_evidence(
                **scope,
                evaluation_revision=original.approval.proposal.evaluation_revision,
                approval_content_hash=original.approval.content_hash,
            )
            assert old == original
            assert state["calls"] == 2
            assert len(repository._publications) == 3
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(prior)
