"""Registered lifecycle separates prospective controls, actual facts and publication."""

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_composite_subject_service
from src.api.main import app
from src.api.services.composite_subject_application import CompositeSubjectApplicationService
from src.core.composite_eligibility.source import MonthlyEligibilitySourceResolution
from src.core.composite_eligibility.staged_subject import subject_key
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from tests.composite_staged_eligibility_helpers import (
    BASE,
    HEADERS,
    CHECKER,
    PROSPECTIVE,
    OBSERVED,
    SyntheticEvidenceVerifier,
    lifecycle_material,
    final_definition,
)


@pytest.fixture
def lifecycle_api():
    _, subject, policy, approved_policy, evaluation, approval, _, _ = lifecycle_material()
    repository = InMemoryDpmCompositeRepository()
    state = {"now": PROSPECTIVE, "candidate_calls": 0, "observation_calls": 0}

    class SyntheticCandidateSource:
        def resolve(self, request):
            state["candidate_calls"] += 1
            assert request.registry_binding == subject.universe.registry_binding
            return subject.universe

    class SyntheticObservationSource:
        def resolve(self, request):
            state["observation_calls"] += 1
            assert request.owner_service == subject.universe.observation_owner
            return MonthlyEligibilitySourceResolution(
                evaluation.observations, owner_service=subject.universe.observation_owner
            )

    service = CompositeSubjectApplicationService(
        repository=repository,
        candidates=SyntheticCandidateSource(),
        observations=SyntheticObservationSource(),
        verifier=SyntheticEvidenceVerifier(),
        clock=lambda: state["now"],
    )
    prior = app.dependency_overrides.copy()
    app.dependency_overrides[get_composite_subject_service] = lambda: service
    try:
        with TestClient(app) as client:
            yield (
                client,
                repository,
                service,
                state,
                subject,
                policy,
                approved_policy,
                evaluation,
                approval,
            )
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(prior)


def subject_body(subject):
    return subject.model_dump(
        mode="json",
        include={
            "display_name",
            "strategy_code",
            "reporting_currency",
            "inception_date",
            "termination_date",
            "eligibility_policy_version",
            "month",
            "correlation_id",
        },
    ) | {"registry_binding": subject.universe.registry_binding.model_dump(mode="json")}


def policy_body(subject, policy):
    return {
        "expected_subject_content_hash": subject.content_hash,
        "layers": [layer.model_dump(mode="json") for layer in policy.proposal.policy.layers],
        "attachments": [binding.model_dump(mode="json") for binding in policy.proposal.attachments],
    }


def approval_body(proposal):
    return {"expected_proposal_content_hash": proposal.content_hash}


def test_registered_full_lifecycle_is_prospective_then_actual_and_finalizes_once(lifecycle_api):
    client, repository, _, state, subject, policy, approved_policy, evaluation, approval = (
        lifecycle_api
    )
    checker = HEADERS | {"X-Actor-Id": CHECKER}
    policy_url = BASE + "/policies/synthetic.policy.r1"
    evaluation_url = BASE + "/evaluations/synthetic.evaluation.r1"
    assert client.put(
        BASE, json=subject_body(subject), headers=HEADERS
    ).json() == subject.model_dump(mode="json")
    assert client.put(
        policy_url, json=policy_body(subject, policy), headers=HEADERS
    ).json() == policy.model_dump(mode="json")
    response = client.put(policy_url + "/approval", json=approval_body(policy), headers=checker)
    assert response.status_code == 200, response.text
    assert response.json() == approved_policy.model_dump(mode="json")
    assert not repository._definitions
    assert not repository._publications
    state["now"] = OBSERVED
    evaluation_body = {
        "policy_proposal_revision": policy.proposal.proposal_revision,
        "policy_approval_content_hash": approved_policy.content_hash,
        "target_membership_revision": evaluation.target_membership_revision,
        "source_cut_id": evaluation.observation_binding.source_cut_id,
        "source_revision": evaluation.observation_binding.source_watermark,
        "source_content_hash": evaluation.observation_binding.content_hash,
    }
    response = client.put(evaluation_url, json=evaluation_body, headers=HEADERS)
    assert response.status_code == 200, response.text
    assert response.json() == evaluation.model_dump(mode="json")
    # The same existing rules retain independently checked +150/-100 flow = 5%.
    assessments = response.json()["evaluation"]["portfolios"][0]["assessments"]
    flow = next(item for item in assessments if item["rule"] == "SIGNIFICANT_FLOW")
    assert (flow["numerator"], flow["denominator"], flow["ratio"], flow["outcome"]) == (
        "50",
        "1000",
        "0.05",
        "PASS",
    )
    response = client.put(
        evaluation_url + "/approval", json=approval_body(evaluation), headers=checker
    )
    assert response.status_code == 200, response.text
    assert response.json() == approval.model_dump(mode="json")
    assert not repository._definitions
    assert not repository._publications
    definition = final_definition(subject, approval)
    final_body = {
        "evaluation_revision": evaluation.evaluation_revision,
        "expected_approval_content_hash": approval.content_hash,
        "definition": definition.model_dump(
            mode="json",
            exclude={
                "product_name",
                "tenant_id",
                "composite_id",
                "definition_version",
                "created_by",
            },
        ),
    }
    response = client.put(BASE + "/finalization", json=final_body, headers=checker)
    assert response.status_code == 200, response.text
    receipt = response.json()
    assert receipt["publication_sequence"] == 1
    assert receipt["completeness"] == "UNVERIFIED"
    assert client.get(BASE + "/finalization", headers=HEADERS).json() == receipt
    assert client.put(BASE + "/finalization", json=final_body, headers=checker).json() == receipt
    # Fresh default service replays retained controls without external sources/verifier.
    app.dependency_overrides[get_composite_subject_service] = lambda: (
        CompositeSubjectApplicationService(repository=repository)
    )
    assert client.put(
        BASE, json=subject_body(subject), headers=HEADERS
    ).json() == subject.model_dump(mode="json")
    assert client.put(
        evaluation_url, json=evaluation_body, headers=HEADERS
    ).json() == evaluation.model_dump(mode="json")
    assert client.put(BASE + "/finalization", json=final_body, headers=checker).json() == receipt
    assert state["candidate_calls"] == state["observation_calls"] == 1
    assert len(repository._publications) == 1


def test_default_candidate_source_refuses_without_reservation(lifecycle_api):
    client, repository, _, _, subject, *_ = lifecycle_api
    app.dependency_overrides[get_composite_subject_service] = lambda: (
        CompositeSubjectApplicationService(repository=repository)
    )
    response = client.put(BASE, json=subject_body(subject), headers=HEADERS)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "COMPOSITE_SUBJECT_UNIVERSE_UNAVAILABLE"
    assert repository.get_eligibility_subject(key=subject_key(subject)) is None


def test_independent_checker_and_unavailable_verifier_cannot_be_bypassed(lifecycle_api):
    client, repository, _, _, subject, policy, *_ = lifecycle_api
    repository.save_eligibility_subject(subject=subject)
    repository.save_subject_control(control=policy)
    url = BASE + "/policies/synthetic.policy.r1/approval"
    assert client.put(url, json=approval_body(policy), headers=HEADERS).status_code == 403
    assert (
        client.put(
            url,
            json=approval_body(policy),
            headers=HEADERS | {"X-Actor-Id": CHECKER, "X-Role": "DPM_COMPOSITE_OPERATOR"},
        ).status_code
        == 403
    )
    app.dependency_overrides[get_composite_subject_service] = lambda: (
        CompositeSubjectApplicationService(repository=repository, clock=lambda: PROSPECTIVE)
    )
    response = client.put(
        url, json=approval_body(policy), headers=HEADERS | {"X-Actor-Id": CHECKER}
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "COMPOSITE_SUBJECT_VERIFICATION_UNAVAILABLE"
    assert not repository._monthly_approvals
    assert not repository._publications


@pytest.mark.parametrize(
    "override", ["tenant_id", "created_by", "created_at", "members", "observations", "qualified"]
)
def test_subject_request_rejects_caller_owned_scope_facts_time_and_qualification(
    lifecycle_api, override
):
    client, repository, _, _, subject, *_ = lifecycle_api
    response = client.put(
        BASE, json=subject_body(subject) | {override: "caller-choice"}, headers=HEADERS
    )
    assert response.status_code == 422
    assert repository.get_eligibility_subject(key=subject_key(subject)) is None
