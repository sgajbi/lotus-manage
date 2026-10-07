"""Registered lifecycle separates prospective controls, actual facts and publication."""

import pytest
from copy import deepcopy
from dataclasses import replace
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
    synthetic_verification,
)
from tests.composite_authority_helpers import rebind_definition
from src.core.composite_definition_versions import DpmCompositeDefinitionV2
from src.core.composite_eligibility.staged_publication import (
    SubjectFinalization,
    finalization_verification_requests,
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


def evaluation_body(policy, approved_policy, evaluation):
    return {
        "policy_proposal_revision": policy.proposal.proposal_revision,
        "policy_approval_content_hash": approved_policy.content_hash,
        "target_membership_revision": evaluation.target_membership_revision,
        "source_cut_id": evaluation.observation_binding.source_cut_id,
        "source_revision": evaluation.observation_binding.source_watermark,
        "source_content_hash": evaluation.observation_binding.content_hash,
    }


def retained_state(repository):
    return deepcopy(
        (
            repository._staged.subjects,
            repository._staged.receipts,
            repository._definitions,
            repository._staged.controls,
            repository._membership_revisions,
            repository._universe_attestations,
            repository._publications,
            repository._last_sequence,
        )
    )


@pytest.mark.parametrize(
    "case,code",
    [
        ("registry", "COMPOSITE_SUBJECT_REGISTRY_BINDING_MISMATCH"),
        ("future", "COMPOSITE_SUBJECT_FUTURE_UNIVERSE_GENERATION"),
        ("private-error", "COMPOSITE_SUBJECT_INPUT_INVALID"),
        ("scope-validation", "COMPOSITE_SUBJECT_UNIVERSE_SCOPE_MISMATCH"),
    ],
)
def test_registered_candidate_admission_refuses_rebinding_future_or_private_error_without_reservation(
    lifecycle_api, case, code
):
    client, repository, service, state, subject, *_ = lifecycle_api

    class CandidateSource:
        def resolve(self, request):
            if case == "private-error":
                raise ValueError("private-upstream-token-do-not-expose")
            return subject.universe

    app.dependency_overrides[get_composite_subject_service] = lambda: replace(
        service, candidates=CandidateSource()
    )
    body = subject_body(subject)
    if case == "registry":
        body["registry_binding"]["digest"] = "sha256:" + "0" * 64
    elif case == "future":
        state["now"] = "2026-08-19T00:00:00.000000Z"
    elif case == "scope-validation":
        body["reporting_currency"] = "EUR"
    before = retained_state(repository)
    response = client.put(BASE, json=body, headers=HEADERS)
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == code
    assert "private-upstream-token" not in response.text
    assert retained_state(repository) == before


def test_registered_finalization_replay_rejects_valid_changed_economic_source_revision(
    lifecycle_api,
):
    client, repository, _, _, subject, policy, approved_policy, evaluation, approval = lifecycle_api
    repository.save_eligibility_subject(subject=subject)
    for control in (policy, approved_policy, evaluation, approval):
        repository.save_subject_control(control=control)
    definition = final_definition(subject, approval)
    finalization = SubjectFinalization(
        subject=subject,
        evaluation_approval=approval,
        definition=definition,
        verifications=[
            synthetic_verification(request)
            for request in finalization_verification_requests(definition, subject)
        ],
    )
    receipt = repository.finalize_eligibility_subject(finalization=finalization)
    wire = definition.model_dump(mode="json")
    wire["source_authority"]["payload"]["selections"][0]["source_revision"] = (
        "changed-economic-revision"
    )
    changed = DpmCompositeDefinitionV2.model_validate(
        rebind_definition(wire, refresh_approval=True)
    )
    before = retained_state(repository)
    response = client.put(
        BASE + "/finalization",
        headers=HEADERS | {"X-Actor-Id": CHECKER},
        json={
            "evaluation_revision": evaluation.evaluation_revision,
            "expected_approval_content_hash": approval.content_hash,
            "definition": changed.model_dump(
                mode="json",
                exclude={
                    "product_name",
                    "tenant_id",
                    "composite_id",
                    "definition_version",
                    "created_by",
                },
            ),
        },
    )
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT"
    assert retained_state(repository) == before
    assert repository.get_eligibility_finalization(key=subject_key(subject)) == receipt


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


@pytest.mark.parametrize(
    "suffix,index",
    [
        ("", None),
        ("/policies/synthetic.policy.r1", 0),
        ("/policies/synthetic.policy.r1/approval", 1),
        ("/evaluations/synthetic.evaluation.r1", 2),
        ("/evaluations/synthetic.evaluation.r1/approval", 3),
    ],
)
def test_registered_exact_reads_isolate_tenant_and_do_not_publish(lifecycle_api, suffix, index):
    client, repository, _, _, subject, *controls = lifecycle_api
    response = client.get(BASE + suffix, headers=HEADERS)
    assert response.status_code == 404
    expected_code = (
        "COMPOSITE_SUBJECT_NOT_FOUND" if index is None else "COMPOSITE_SUBJECT_CONTROL_NOT_FOUND"
    )
    assert response.json()["detail"]["code"] == expected_code
    repository.save_eligibility_subject(subject=subject)
    for control in controls:
        repository.save_subject_control(control=control)
    before = retained_state(repository)
    response = client.get(BASE + suffix, headers=HEADERS)
    assert response.status_code == 200, response.text
    assert response.json() == (subject if index is None else controls[index]).model_dump(
        mode="json"
    )
    response = client.get(BASE + suffix, headers=HEADERS | {"X-Tenant-Id": "other-tenant"})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == expected_code
    assert retained_state(repository) == before


@pytest.mark.parametrize(
    "stage", ["subject", "policy", "policy-approval", "evaluation", "evaluation-approval"]
)
@pytest.mark.parametrize("changed", [False, True])
def test_registered_retained_replay_has_no_external_resolution_and_changed_actor_conflicts(
    lifecycle_api, stage, changed
):
    client, repository, _, state, subject, policy, approved_policy, evaluation, approval = (
        lifecycle_api
    )
    repository.save_eligibility_subject(subject=subject)
    for control in (policy, approved_policy, evaluation, approval):
        repository.save_subject_control(control=control)
    # All defaults are unavailable: successful replay must use retained custody.
    app.dependency_overrides[get_composite_subject_service] = lambda: (
        CompositeSubjectApplicationService(repository=repository)
    )
    url, body, expected, actor = {
        "subject": (BASE, subject_body(subject), subject, HEADERS["X-Actor-Id"]),
        "policy": (
            BASE + "/policies/synthetic.policy.r1",
            policy_body(subject, policy),
            policy,
            HEADERS["X-Actor-Id"],
        ),
        "policy-approval": (
            BASE + "/policies/synthetic.policy.r1/approval",
            approval_body(policy),
            approved_policy,
            CHECKER,
        ),
        "evaluation": (
            BASE + "/evaluations/synthetic.evaluation.r1",
            evaluation_body(policy, approved_policy, evaluation),
            evaluation,
            HEADERS["X-Actor-Id"],
        ),
        "evaluation-approval": (
            BASE + "/evaluations/synthetic.evaluation.r1/approval",
            approval_body(evaluation),
            approval,
            CHECKER,
        ),
    }[stage]
    before = retained_state(repository)
    response = client.put(
        url, json=body, headers=HEADERS | {"X-Actor-Id": "other-actor" if changed else actor}
    )
    assert response.status_code == (409 if changed else 200), response.text
    if changed:
        assert response.json()["detail"]["code"] == "COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT"
    else:
        assert response.json() == expected.model_dump(mode="json")
    assert retained_state(repository) == before
    assert state["candidate_calls"] == state["observation_calls"] == 0


@pytest.mark.parametrize(
    "stage", ["policy", "policy-approval", "evaluation", "evaluation-approval", "finalization"]
)
def test_registered_stale_hash_refuses_before_replay_or_resolution(lifecycle_api, stage):
    client, repository, _, state, subject, policy, approved_policy, evaluation, approval = (
        lifecycle_api
    )
    repository.save_eligibility_subject(subject=subject)
    for control in (policy, approved_policy, evaluation, approval):
        repository.save_subject_control(control=control)
    definition = final_definition(subject, approval)
    url, body, hash_field, actor = {
        "policy": (
            BASE + "/policies/synthetic.policy.r1",
            policy_body(subject, policy),
            "expected_subject_content_hash",
            HEADERS["X-Actor-Id"],
        ),
        "policy-approval": (
            BASE + "/policies/synthetic.policy.r1/approval",
            approval_body(policy),
            "expected_proposal_content_hash",
            CHECKER,
        ),
        "evaluation": (
            BASE + "/evaluations/synthetic.evaluation.r1",
            evaluation_body(policy, approved_policy, evaluation),
            "policy_approval_content_hash",
            HEADERS["X-Actor-Id"],
        ),
        "evaluation-approval": (
            BASE + "/evaluations/synthetic.evaluation.r1/approval",
            approval_body(evaluation),
            "expected_proposal_content_hash",
            CHECKER,
        ),
        "finalization": (
            BASE + "/finalization",
            {
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
            },
            "expected_approval_content_hash",
            CHECKER,
        ),
    }[stage]
    before = retained_state(repository)
    response = client.put(
        url, json=body | {hash_field: "sha256:" + "0" * 64}, headers=HEADERS | {"X-Actor-Id": actor}
    )
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "COMPOSITE_SUBJECT_STALE_CONTENT_CONFLICT"
    assert retained_state(repository) == before
    assert state["candidate_calls"] == state["observation_calls"] == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("target_membership_revision", "changed-target"),
        ("source_cut_id", "changed-cut"),
        ("source_revision", "changed-revision"),
        ("source_content_hash", "sha256:" + "0" * 64),
    ],
)
def test_registered_evaluation_replay_rejects_changed_frozen_selector(lifecycle_api, field, value):
    client, repository, _, state, subject, policy, approved_policy, evaluation, approval = (
        lifecycle_api
    )
    repository.save_eligibility_subject(subject=subject)
    for control in (policy, approved_policy, evaluation, approval):
        repository.save_subject_control(control=control)
    before = retained_state(repository)
    response = client.put(
        BASE + "/evaluations/synthetic.evaluation.r1",
        json=evaluation_body(policy, approved_policy, evaluation) | {field: value},
        headers=HEADERS,
    )
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT"
    assert retained_state(repository) == before
    assert state["observation_calls"] == 0


def test_registered_finalization_requires_original_checker_and_missing_receipt_is_not_success(
    lifecycle_api,
):
    client, repository, _, state, subject, policy, approved_policy, evaluation, approval = (
        lifecycle_api
    )
    repository.save_eligibility_subject(subject=subject)
    for control in (policy, approved_policy, evaluation, approval):
        repository.save_subject_control(control=control)
    before = retained_state(repository)
    response = client.get(BASE + "/finalization", headers=HEADERS)
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "COMPOSITE_SUBJECT_FINALIZATION_NOT_FOUND"
    definition = final_definition(subject, approval)
    response = client.put(
        BASE + "/finalization",
        headers=HEADERS | {"X-Actor-Id": "other-checker"},
        json={
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
        },
    )
    assert response.status_code == 403, response.text
    assert response.json()["detail"]["code"] == "COMPOSITE_SUBJECT_FINALIZER_FORBIDDEN"
    assert retained_state(repository) == before
    assert state["candidate_calls"] == state["observation_calls"] == 0
