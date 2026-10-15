"""Current-clock registered first-subject history from empty business custody."""

import base64

from copy import deepcopy
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from functools import partial

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.api.dependencies import get_composite_subject_service
from src.api.main import app
from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.observations import MonthlyEligibilityObservations
from src.core.composite_eligibility.source import MonthlyEligibilitySourceResolution
from src.core.composite_eligibility.staged_controls import (
    EVALUATION_APPROVAL_ADAPTER,
    STAGED_CONTROL_ADAPTER,
)
from src.core.composite_eligibility.staged_publication import decode_subject_receipt
from src.core.composite_eligibility.staged_subject import subject_key
from src.core.composite_repository import DpmCompositeConflictError
from src.core.composite_eligibility.historical_policy import UnavailableHistoricalPolicyAdmission
from src.api.services.composite_subject_requests import (
    SubjectHistoricalPolicyRequest,
    SubjectApprovalRequest,
    SubjectEvaluationRequest,
    SubjectFinalizationRequest,
)
from tests.composite_historical_subject_helpers import empty_historical_subject_service
from tests.composite_historical_subject_sources import configured_historical_subject_service
from tests.composite_staged_eligibility_helpers import BASE, HEADERS, CHECKER, final_definition
from tests.unit.api.test_composite_subject_lifecycle_routes import (
    subject_body,
    policy_body,
    retained_state,
)


@pytest.fixture
def historical_subject_api():
    service, repository, provider, subject, policy, evaluation = empty_historical_subject_service()
    prior = app.dependency_overrides.copy()
    app.dependency_overrides[get_composite_subject_service] = lambda: service
    try:
        with TestClient(app) as client:
            assert not repository._staged.subjects
            assert not repository._definitions
            yield client, service, repository, provider, subject, policy, evaluation
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(prior)


def put(client, path, body, *, checker=False):
    response = client.put(
        path, json=body, headers=HEADERS | ({"X-Actor-Id": CHECKER} if checker else {})
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_empty_scope_signed_configured_sources_retain_complete_assembly(monkeypatch):
    with configured_historical_subject_service(monkeypatch) as material:
        service, repository, provider, subject, policy, evaluation, state = material
        prior = app.dependency_overrides.copy()
        app.dependency_overrides[get_composite_subject_service] = lambda: service
        try:
            with TestClient(app) as client:
                assert not repository._definitions and not repository._staged.subjects
                controls, definition, receipt, _ = finalized((client, *material[:6]))
                assert controls[2]["source_assembly_evidence"]["assembly"] == state["assembly"]
                assert (
                    controls[2]["source_assembly_evidence"]["verification"]["posture"]
                    == "SYNTHETIC_NON_CERTIFYING"
                )
                assert state["calls"].count("candidates") == 1
                assert state["calls"].count("observations") == 1
                assert state["calls"].count("historical") == 4
                assert len(repository._publications) == 1
                assert receipt["product_version"] == "v3"
                assert (
                    definition.source_authority.payload.eligibility_evaluation_binding.product_version
                    == "v2"
                )
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(prior)


def admitted_policy(fixture):
    client, _, _, provider, source_subject, *_ = fixture
    subject = put(client, BASE, subject_body(source_subject))
    body = {
        "expected_subject_content_hash": subject["content_hash"],
        "reference": provider.mapping.reference.model_dump(mode="json"),
    }
    path = BASE + "/policies/historical.policy.r1"
    proposal = put(client, path + "/historical-admission", body)
    approval = put(
        client,
        path + "/approval",
        {"expected_proposal_content_hash": proposal["content_hash"]},
        checker=True,
    )
    return subject, path, body, proposal, approval


def evaluated(fixture):
    subject, path, body, proposal, approval = admitted_policy(fixture)
    client, _, _, _, _, _, source_evaluation = fixture
    binding = source_evaluation.observation_binding
    command = {
        "policy_proposal_revision": proposal["proposal"]["proposal_revision"],
        "policy_approval_content_hash": approval["content_hash"],
        "target_membership_revision": "historical.membership.r1",
        "source_cut_id": binding.source_cut_id,
        "source_revision": binding.source_watermark,
        "source_content_hash": binding.content_hash,
    }
    url = BASE + "/evaluations/historical.evaluation.r1"
    evaluation = put(client, url, command)
    return subject, path, body, proposal, approval, url, command, evaluation


def finalized(fixture, *, publish=True):
    subject, path, body, policy, approved_policy, url, command, evaluation = evaluated(fixture)
    client, service, repository, _, _, _, _ = fixture
    approval = put(
        client,
        url + "/approval",
        {"expected_proposal_content_hash": evaluation["content_hash"]},
        checker=True,
    )
    typed = EVALUATION_APPROVAL_ADAPTER.validate_python(approval)
    native_subject = service.subject(
        (
            subject["tenant_id"],
            subject["composite_id"],
            subject["definition_version"],
            subject["subject_revision"],
        )
    )
    definition = final_definition(native_subject, typed)
    final_body = {
        "evaluation_revision": evaluation["evaluation_revision"],
        "expected_approval_content_hash": approval["content_hash"],
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
    assert not repository._definitions and not repository._publications
    if not publish:
        return [policy, approved_policy, evaluation, approval], definition, None, final_body
    receipt = put(client, BASE + "/finalization", final_body, checker=True)
    return [policy, approved_policy, evaluation, approval], definition, receipt, final_body


def test_empty_scope_current_clock_historical_first_publication_and_offline_replay(
    historical_subject_api,
):
    client, service, repository, provider, source_subject, source_policy, _ = historical_subject_api
    # The ordinary prospective guard remains in force on the current runtime clock.
    current_subject = put(client, BASE, subject_body(source_subject))
    native_subject = service.subject(subject_key(source_subject))
    ordinary = client.put(
        BASE + "/policies/ordinary",
        headers=HEADERS,
        json=policy_body(native_subject, source_policy),
    )
    assert ordinary.status_code == 403
    assert (
        ordinary.json()["detail"]["code"] == "COMPOSITE_ELIGIBILITY_RETROSPECTIVE_POLICY_FORBIDDEN"
    )
    controls, definition, receipt, final_body = finalized(historical_subject_api)
    assert [item["product_version"] for item in controls] == ["v2"] * 4
    assert receipt["product_version"] == receipt["finalization"]["product_version"] == "v3"
    assert receipt["completeness"] == "UNVERIFIED"
    assert receipt["finalization"]["official_activation"] == "UNAVAILABLE"
    historical = controls[0]["proposal"]["verification"]["mapping"]
    assert historical["raw_original_base64"] == provider.mapping.raw_original_base64
    assert historical["original_credential"] == provider.mapping.original_credential
    assert historical["original_approved_at"] < "2026-09-01"
    assert controls[0]["proposal"]["proposed_at"] >= current_subject["created_at"]
    assert (
        controls[3]["approved_at"]
        >= controls[2]["proposed_at"]
        >= controls[1]["approval"]["approved_at"]
    )
    assert [item.operation for item in provider.calls] == [
        "POLICY_PROPOSAL",
        "POLICY_APPROVAL",
        "EVALUATION_PROPOSAL",
        "EVALUATION_APPROVAL",
    ]
    assert len(repository._publications) == 1
    binding = definition.source_authority.payload.eligibility_evaluation_binding.model_dump(
        mode="json"
    )
    resolver = "/api/v1/rebalance/composites/synthetic-composite/definitions/synthetic-definition/eligibility-evidence/resolve"
    before = retained_state(repository)
    # Recompose an unavailable service around retained custody, without the original source ports.
    offline = replace(service, historical_admission=UnavailableHistoricalPolicyAdmission())
    provider.available = False
    app.dependency_overrides[get_composite_subject_service] = lambda: offline
    assert client.post(resolver, headers=HEADERS, json=binding).json() == receipt
    assert client.get(BASE + "/finalization", headers=HEADERS).json() == receipt
    assert put(client, BASE + "/finalization", final_body, checker=True) == receipt
    assert decode_subject_receipt(receipt).model_dump(mode="json") == receipt
    assert retained_state(repository) == before


@pytest.mark.parametrize("change", ["subject", "reference", "unavailable", "self", "stale"])
def test_historical_subject_refusals_preserve_control_custody(historical_subject_api, change):
    client, service, repository, provider, source_subject, _, source_evaluation = (
        historical_subject_api
    )
    subject = put(client, BASE, subject_body(source_subject))
    body = {
        "expected_subject_content_hash": subject["content_hash"],
        "reference": provider.mapping.reference.model_dump(mode="json"),
    }
    path = BASE + "/policies/historical.policy.r1"
    if change == "subject":
        body["expected_subject_content_hash"] = "sha256:" + "0" * 64
    elif change == "reference":
        body["reference"]["artifact_id"] = "wrong-artifact"
    elif change == "unavailable":
        provider.available = False
    before = retained_state(repository)
    if change in {"self", "stale"}:
        proposal = put(client, path + "/historical-admission", body)
        before = retained_state(repository)
        response = client.put(
            path + "/approval",
            headers=HEADERS if change == "self" else HEADERS | {"X-Actor-Id": CHECKER},
            json={
                "expected_proposal_content_hash": proposal["content_hash"]
                if change == "self"
                else "sha256:" + "0" * 64
            },
        )
    else:
        response = client.put(path + "/historical-admission", headers=HEADERS, json=body)
    assert response.status_code in {403, 409, 422, 503}, response.text
    assert retained_state(repository) == before


@pytest.mark.parametrize(
    "change",
    ["nested-hash", "mixed-policy", "mixed-evaluation", "mixed-receipt", "intent", "proof"],
)
def test_historical_subject_strict_versions_and_nested_proofs(historical_subject_api, change):
    controls, _, receipt, _ = finalized(historical_subject_api)
    wire = deepcopy(receipt if change == "mixed-receipt" else controls[3])
    if change == "nested-hash":
        wire["proposal"]["policy_approval"]["approval"]["content_hash"] = "sha256:" + "0" * 64
    elif change == "mixed-policy":
        wire["proposal"]["policy_approval"]["product_version"] = "v1"
    elif change == "mixed-evaluation":
        wire["proposal"]["product_version"] = "v1"
    elif change == "mixed-receipt":
        wire["product_version"] = "v1"
    elif change == "intent":
        wire["operation_verification"]["request"]["intent_digest"] = "sha256:" + "0" * 64
    else:
        wire["operation_verification"]["verifier_credential"] = "AAAA"
    with pytest.raises((ValueError, ValidationError)):
        decode_subject_receipt(
            wire
        ) if change == "mixed-receipt" else STAGED_CONTROL_ADAPTER.validate_python(wire)


def test_concurrent_current_historical_admissions_and_checker_keep_one_immutable_winner(
    historical_subject_api, monkeypatch
):
    client, service, repository, provider, source_subject, _, source_evaluation = (
        historical_subject_api
    )
    created = put(client, BASE, subject_body(source_subject))
    key = subject_key(source_subject)
    command = SubjectHistoricalPolicyRequest(
        expected_subject_content_hash=created["content_hash"],
        reference=provider.mapping.reference,
    )
    original_verify = provider.verify
    barrier = Barrier(2)

    def synchronized(request):
        proof = original_verify(request)
        barrier.wait(timeout=10)
        return proof

    monkeypatch.setattr(provider, "verify", synchronized)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                service.propose_historical_policy, key, "concurrent", HEADERS["X-Actor-Id"], command
            )
            for _ in range(2)
        ]
        proposals = [future.result(timeout=20) for future in futures]
    assert proposals[0] == proposals[1]
    approve = SubjectApprovalRequest(expected_proposal_content_hash=proposals[0].content_hash)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(service.approve_policy, key, "concurrent", CHECKER, approve)
            for _ in range(2)
        ]
        approvals = [future.result(timeout=20) for future in futures]
    assert approvals[0] == approvals[1]
    assert approvals[0].proposal == proposals[0]
    source = source_evaluation.observation_binding
    evaluate = SubjectEvaluationRequest(
        policy_proposal_revision="concurrent",
        policy_approval_content_hash=approvals[0].content_hash,
        target_membership_revision="concurrent-membership",
        source_cut_id=source.source_cut_id,
        source_revision=source.source_watermark,
        source_content_hash=source.content_hash,
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                service.evaluate, key, "concurrent-evaluation", HEADERS["X-Actor-Id"], evaluate
            )
            for _ in range(2)
        ]
        evaluations = [future.result(timeout=20) for future in futures]
    assert evaluations[0] == evaluations[1]
    approve_evaluation = SubjectApprovalRequest(
        expected_proposal_content_hash=evaluations[0].content_hash
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                service.approve_evaluation,
                key,
                "concurrent-evaluation",
                CHECKER,
                approve_evaluation,
            )
            for _ in range(2)
        ]
        evaluation_approvals = [future.result(timeout=20) for future in futures]
    assert evaluation_approvals[0] == evaluation_approvals[1]
    assert evaluation_approvals[0].proposal == evaluations[0]
    with pytest.raises(ValueError, match="COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT"):
        service.evaluate(
            key,
            "concurrent-evaluation",
            HEADERS["X-Actor-Id"],
            evaluate.model_copy(update={"target_membership_revision": "changed-target"}),
        )
    assert not repository._definitions and not repository._publications


@pytest.mark.parametrize("change", ["signature", "expiry", "raw", "scope", "purpose", "qualified"])
def test_historical_subject_revalidates_signed_original_and_current_admission_before_write(
    historical_subject_api, monkeypatch, change
):
    client, _, repository, provider, source_subject, *_ = historical_subject_api
    created = put(client, BASE, subject_body(source_subject))
    original = provider.verify
    if change == "qualified":
        provider.trust = provider.trust.model_copy(update={"posture": "QUALIFIED_RECEIPT"})

    def modified(request):
        proof = original(request)
        if change == "signature":
            return proof.model_copy(
                update={"verifier_credential": base64.b64encode(bytes(64)).decode()}
            )
        if change == "expiry":
            return proof.model_copy(update={"expires_at": proof.checked_at})
        if change == "raw":
            return proof.model_copy(
                update={"mapping": proof.mapping.model_copy(update={"raw_original_base64": "AAAA"})}
            )
        if change == "scope":
            altered = proof.request.model_copy(
                update={"scope": proof.request.scope.model_copy(update={"tenant_id": "foreign"})}
            )
            return proof.model_copy(update={"request": altered})
        if change == "purpose":
            return proof.model_copy(
                update={
                    "request": proof.request.model_copy(update={"purpose": "ELIGIBILITY_POLICY"})
                }
            )
        unsigned = proof.model_dump(
            mode="json", exclude={"content_hash", "verifier_credential"}
        ) | {"posture": "QUALIFIED_RECEIPT"}
        credential = base64.b64encode(
            provider.verifier.sign(hash_canonical_payload(unsigned).encode())
        ).decode()
        return type(proof).model_validate(unsigned | {"verifier_credential": credential})

    monkeypatch.setattr(provider, "verify", modified)
    before = retained_state(repository)
    response = client.put(
        BASE + "/policies/rejected/historical-admission",
        headers=HEADERS,
        json={
            "expected_subject_content_hash": created["content_hash"],
            "reference": provider.mapping.reference.model_dump(mode="json"),
        },
    )
    assert response.status_code == (503 if change == "qualified" else 422), response.text
    if change == "qualified":
        assert (
            response.json()["detail"]["code"]
            == "COMPOSITE_SUBJECT_HISTORICAL_POLICY_POSTURE_UNAVAILABLE"
        )
    assert retained_state(repository) == before


@pytest.mark.parametrize("change", ["missing-member", "future-source"])
def test_historical_first_projection_refuses_incomplete_or_future_source(
    historical_subject_api, change
):
    client, service, repository, _, source_subject, _, source_evaluation = historical_subject_api
    _, _, _, policy, approved = admitted_policy(historical_subject_api)
    wire = source_evaluation.observations.model_dump(mode="json")
    if change == "missing-member":
        wire["portfolios"] = []
    else:
        wire["source_generated_at"] = "2999-01-01T00:00:00.000000Z"
    snapshot = MonthlyEligibilityObservations.model_validate(wire)

    class Source:
        def resolve(self, request):
            return MonthlyEligibilitySourceResolution(
                snapshot, owner_service=source_subject.universe.observation_owner
            )

    app.dependency_overrides[get_composite_subject_service] = lambda: replace(
        service, observations=Source()
    )
    body = {
        "policy_proposal_revision": policy["proposal"]["proposal_revision"],
        "policy_approval_content_hash": approved["content_hash"],
        "target_membership_revision": "refused-membership",
        "source_cut_id": snapshot.source_cut_id,
        "source_revision": snapshot.source_revision,
        "source_content_hash": hash_canonical_payload(snapshot.model_dump(mode="json")),
    }
    before = retained_state(repository)
    url = BASE + "/evaluations/refused"
    response = client.put(url, headers=HEADERS, json=body)
    if change == "missing-member":
        assert response.status_code == 200, response.text
        assert response.json()["evaluation"]["declared_universe_coverage"] == "INCOMPLETE"
        before = retained_state(repository)
        response = client.put(
            url + "/approval",
            headers=HEADERS | {"X-Actor-Id": CHECKER},
            json={"expected_proposal_content_hash": response.json()["content_hash"]},
        )
    assert response.status_code == 422, response.text
    assert retained_state(repository) == before
    assert not repository._publications and not repository._definitions


def test_missing_subject_and_retained_historical_intent_cannot_be_taken_over(
    historical_subject_api,
):
    client, _, repository, provider, source_subject, *_ = historical_subject_api
    url = BASE + "/policies/replay/historical-admission"
    body = {
        "expected_subject_content_hash": source_subject.content_hash,
        "reference": provider.mapping.reference.model_dump(mode="json"),
    }
    missing = client.put(url, headers=HEADERS, json=body)
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "COMPOSITE_SUBJECT_NOT_FOUND"
    assert not provider.calls and not repository._staged.subjects
    subject = put(client, BASE, subject_body(source_subject))
    body["expected_subject_content_hash"] = subject["content_hash"]
    proposed = put(client, url, body)
    before = retained_state(repository)
    calls = len(provider.calls)
    provider.available = False
    assert put(client, url, body) == proposed
    for identity, command in (
        (HEADERS | {"X-Actor-Id": "different-maker"}, body),
        (HEADERS, body | {"reference": body["reference"] | {"revision": "other-original"}}),
    ):
        refused = client.put(url, headers=identity, json=command)
        assert refused.status_code == 409, refused.text
        assert refused.json()["detail"]["code"] == "COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT"
    assert len(provider.calls) == calls
    assert retained_state(repository) == before


@pytest.mark.parametrize(
    "stage", ["policy", "policy-approval", "evaluation", "evaluation-approval"]
)
def test_historical_control_store_conflict_without_winner_preserves_prior_custody(
    historical_subject_api, monkeypatch, stage
):
    client, service, repository, provider, source_subject, _, source_evaluation = (
        historical_subject_api
    )
    subject = put(client, BASE, subject_body(source_subject))
    key = subject_key(source_subject)
    policy = SubjectHistoricalPolicyRequest(
        expected_subject_content_hash=subject["content_hash"], reference=provider.mapping.reference
    )
    action = partial(
        service.propose_historical_policy, key, "atomic", HEADERS["X-Actor-Id"], policy
    )
    if stage != "policy":
        proposed = action()
        action = partial(
            service.approve_policy,
            key,
            "atomic",
            CHECKER,
            SubjectApprovalRequest(expected_proposal_content_hash=proposed.content_hash),
        )
    if stage in {"evaluation", "evaluation-approval"}:
        approved = action()
        source = source_evaluation.observation_binding
        command = SubjectEvaluationRequest(
            policy_proposal_revision="atomic",
            policy_approval_content_hash=approved.content_hash,
            target_membership_revision="atomic-membership",
            source_cut_id=source.source_cut_id,
            source_revision=source.source_watermark,
            source_content_hash=source.content_hash,
        )
        action = partial(service.evaluate, key, "atomic-evaluation", HEADERS["X-Actor-Id"], command)
    if stage == "evaluation-approval":
        evaluation = action()
        action = partial(
            service.approve_evaluation,
            key,
            "atomic-evaluation",
            CHECKER,
            SubjectApprovalRequest(expected_proposal_content_hash=evaluation.content_hash),
        )
    failure = DpmCompositeConflictError("controlled-storage-conflict-without-winner")

    def refuse(**kwargs):
        raise failure

    before = retained_state(repository)
    monkeypatch.setattr(repository, "save_subject_control", refuse)
    with pytest.raises(DpmCompositeConflictError) as refused:
        action()
    assert refused.value is failure
    assert retained_state(repository) == before
    assert not repository._definitions and not repository._publications


def test_competing_historical_evaluation_intents_do_not_return_the_wrong_winner(
    historical_subject_api, monkeypatch
):
    client, service, repository, _, source_subject, _, source_evaluation = historical_subject_api
    _, _, _, _, approval = admitted_policy(historical_subject_api)
    source = source_evaluation.observation_binding
    command = SubjectEvaluationRequest(
        policy_proposal_revision="historical.policy.r1",
        policy_approval_content_hash=approval["content_hash"],
        target_membership_revision="loser-membership",
        source_cut_id=source.source_cut_id,
        source_revision=source.source_watermark,
        source_content_hash=source.content_hash,
    )
    key = subject_key(source_subject)
    save = repository.save_subject_control
    winner = []

    def competing(control):
        # Interleave another fully admitted command immediately before this one's custody write.
        monkeypatch.setattr(repository, "save_subject_control", save)
        winner.append(
            service.evaluate(
                key,
                "race",
                HEADERS["X-Actor-Id"],
                command.model_copy(update={"target_membership_revision": "winner-membership"}),
            )
        )
        save(control=control)

    monkeypatch.setattr(repository, "save_subject_control", competing)
    with pytest.raises(DpmCompositeConflictError):
        service.evaluate(key, "race", HEADERS["X-Actor-Id"], command)
    assert len(winner) == 1
    assert (
        repository.get_subject_control(
            key=key, kind="CompositeSubjectEvaluationProposal", revision="race"
        )
        == winner[0]
    )
    assert winner[0].target_membership_revision == "winner-membership"
    assert not repository._definitions and not repository._publications


def test_historical_policy_outer_verification_cannot_promote_synthetic_history(
    historical_subject_api, monkeypatch
):
    client, service, repository, provider, source_subject, *_ = historical_subject_api
    subject = put(client, BASE, subject_body(source_subject))
    verify = service.verifier.verify

    def qualified(request):
        receipt = verify(request)
        return type(receipt).model_validate(
            receipt.model_dump(mode="json") | {"posture": "QUALIFIED_RECEIPT", "content_hash": ""}
        )

    monkeypatch.setattr(service.verifier, "verify", qualified)
    before = retained_state(repository)
    refused = client.put(
        BASE + "/policies/qualified/historical-admission",
        headers=HEADERS,
        json={
            "expected_subject_content_hash": subject["content_hash"],
            "reference": provider.mapping.reference.model_dump(mode="json"),
        },
    )
    assert refused.status_code == 503, refused.text
    assert (
        refused.json()["detail"]["code"]
        == "COMPOSITE_SUBJECT_HISTORICAL_POLICY_POSTURE_UNAVAILABLE"
    )
    assert retained_state(repository) == before


def test_published_historical_resolver_refuses_wrong_version_and_absent_monthly_graph(
    historical_subject_api,
):
    client, _, repository, *_ = historical_subject_api
    _, definition, _, _ = finalized(historical_subject_api)
    binding = definition.source_authority.payload.eligibility_evaluation_binding.model_dump(
        mode="json"
    )
    resolver = "/api/v1/rebalance/composites/synthetic-composite/definitions/synthetic-definition/eligibility-evidence/resolve"
    before = retained_state(repository)
    for product, status, code in (
        (
            "CompositeSubjectEvaluationApproval",
            422,
            "COMPOSITE_SUBJECT_ELIGIBILITY_BINDING_MISMATCH",
        ),
        ("CompositeMonthlyEvaluationApproval", 404, "COMPOSITE_MONTHLY_EVIDENCE_NOT_FOUND"),
    ):
        refused = client.post(
            resolver,
            headers=HEADERS,
            json=binding | {"product_name": product, "product_version": "v1"},
        )
        assert refused.status_code == status, refused.text
        assert refused.json()["detail"]["code"] == code
    assert retained_state(repository) == before


@pytest.mark.parametrize("failure_kind", ["clock", "storage"])
def test_historical_finalization_failure_cannot_publish_partial_custody(
    historical_subject_api, monkeypatch, failure_kind
):
    _, service, repository, _, source_subject, *_ = historical_subject_api
    controls, _, _, body = finalized(historical_subject_api, publish=False)
    if failure_kind == "clock":
        premature = final_definition(
            service.subject(subject_key(source_subject)),
            EVALUATION_APPROVAL_ADAPTER.validate_python(controls[3]),
            authority_approved_at=service.subject(subject_key(source_subject)).created_at,
        )
        body["definition"] = premature.model_dump(
            mode="json",
            exclude={
                "product_name",
                "tenant_id",
                "composite_id",
                "definition_version",
                "created_by",
            },
        )
        error = "COMPOSITE_ELIGIBILITY_CLOCK_MISMATCH"
    else:
        error = "controlled-finalization-store-conflict"

        def refused(**kwargs):
            raise DpmCompositeConflictError(error)

        monkeypatch.setattr(repository, "finalize_eligibility_subject", refused)
    before = retained_state(repository)
    with pytest.raises(ValueError, match=error):
        service.finalize(
            subject_key(source_subject), CHECKER, SubjectFinalizationRequest.model_validate(body)
        )
    assert retained_state(repository) == before
    assert not repository._definitions and not repository._publications


def test_historical_checker_role_and_corrupt_control_kind_refuse_without_mutation(
    historical_subject_api, monkeypatch
):
    client, _, repository, *_ = historical_subject_api
    _, path, _, proposed, _ = admitted_policy(historical_subject_api)
    before = retained_state(repository)
    denied = client.put(
        path + "/approval",
        headers=HEADERS | {"X-Actor-Id": CHECKER, "X-Role": "DPM_PORTFOLIO_MANAGER"},
        json={"expected_proposal_content_hash": proposed["content_hash"]},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "COMPOSITE_POLICY_APPROVAL_ROLE_FORBIDDEN"
    # A faulty custody adapter returning a valid control of the wrong kind must not leak it.
    retained = STAGED_CONTROL_ADAPTER.validate_python(proposed)
    monkeypatch.setattr(repository, "get_subject_control", lambda **kwargs: retained)
    corrupt = client.get(BASE + "/evaluations/incorrect-kind", headers=HEADERS)
    assert corrupt.status_code == 409, corrupt.text
    assert corrupt.json()["detail"]["code"] == "COMPOSITE_SUBJECT_CONTROL_INTEGRITY_CONFLICT"
    assert retained_state(repository) == before
