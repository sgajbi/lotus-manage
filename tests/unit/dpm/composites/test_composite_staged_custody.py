"""Retained graph proof; synthetic receipts cannot certify economic authority."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest

from src.core.composite_eligibility.staged_subject import subject_key
from src.core.composite_eligibility.staged_subject import EligibilitySubject
from src.core.composite_eligibility.staged_controls import SubjectPolicyProposal, control_revision
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from tests.composite_staged_eligibility_helpers import finalization_material, lifecycle_material


def custody_state(repository):
    """All shared custody collections, excluding only the process lock."""
    return deepcopy(
        (
            repository._staged.subjects,
            repository._staged.receipts,
            repository._definitions,
            repository._monthly_proposals,
            repository._monthly_approvals,
            repository._monthly_evaluations,
            repository._monthly_evaluation_approvals,
            repository._membership_revisions,
            repository._universe_attestations,
            repository._publications,
            repository._last_sequence,
        )
    )


def retained_graph():
    repository = InMemoryDpmCompositeRepository()
    subject, controls, finalization = finalization_material()
    repository.save_eligibility_subject(subject=subject)
    for control in controls:
        repository.save_subject_control(control=control)
    return repository, subject, controls, finalization


def test_staging_does_not_publish_and_exact_finalization_is_atomic_and_replayable():
    repository, subject, controls, finalization = retained_graph()
    assert (
        repository.get_definition(
            tenant_id=subject.tenant_id,
            composite_id=subject.composite_id,
            definition_version=subject.definition_version,
        )
        is None
    )
    assert not repository.list_publications(
        tenant_id=subject.tenant_id, after_sequence=0, limit=10
    ).items
    assert repository.get_eligibility_finalization(key=subject_key(subject)) is None
    with ThreadPoolExecutor(max_workers=4) as workers:
        receipts = list(
            workers.map(
                lambda _: repository.finalize_eligibility_subject(finalization=finalization),
                range(8),
            )
        )
    assert all(receipt == receipts[0] for receipt in receipts)
    receipt = receipts[0]
    assert receipt.publication_sequence == 1
    assert receipt.completeness == "UNVERIFIED"
    assert receipt.finalization.evaluation_approval.publication_posture == "NOT_PUBLISHED"
    assert receipt.finalization.official_activation == "UNAVAILABLE"
    assert repository.get_eligibility_finalization(key=subject_key(subject)) == receipt
    assert (
        len(
            repository.list_publications(
                tenant_id=subject.tenant_id, after_sequence=0, limit=10
            ).items
        )
        == 1
    )
    assert receipt.membership_content_hash == controls[-1].membership_content_hash
    assert receipt.universe_content_hash == controls[-1].universe_content_hash


@pytest.mark.parametrize(
    "removed", ["subject", "approval", "definition", "membership", "universe", "publication"]
)
def test_receipt_is_not_proof_without_every_retained_canonical_record(removed):
    repository, subject, controls, finalization = retained_graph()
    repository.finalize_eligibility_subject(finalization=finalization)
    stores = {
        "subject": repository._staged.subjects,
        "approval": repository._monthly_evaluation_approvals,
        "definition": repository._definitions,
        "membership": repository._membership_revisions,
        "universe": repository._universe_attestations,
        "publication": repository._publications,
    }
    stores[removed].clear()  # Deliberate corruption, never an operator cleanup path.
    with pytest.raises(ValueError, match="RECEIPT_INTEGRITY_CONFLICT"):
        repository.get_eligibility_finalization(key=subject_key(subject))


def test_missing_retained_predecessor_prevents_control_and_finalization_writes():
    repository = InMemoryDpmCompositeRepository()
    subject, controls, finalization = finalization_material()
    repository.save_eligibility_subject(subject=subject)
    with pytest.raises(ValueError, match="RETAINED_CONTROL_MISMATCH"):
        repository.save_subject_control(control=controls[-1])
    with pytest.raises(ValueError, match="RETAINED_CONTROL_MISMATCH"):
        repository.finalize_eligibility_subject(finalization=finalization)
    assert repository.get_eligibility_finalization(key=subject_key(subject)) is None
    assert not repository._definitions
    assert not repository._membership_revisions
    assert not repository._universe_attestations
    assert not repository._publications


def test_subject_reservation_replay_and_conflicting_content_preserve_all_custody():
    repository, subject, _, finalization = retained_graph()
    before = custody_state(repository)
    repository.save_eligibility_subject(subject=subject)
    assert custody_state(repository) == before
    changed = EligibilitySubject.model_validate(
        subject.model_dump(mode="json")
        | {"display_name": "different-business-content", "content_hash": ""}
    )
    with pytest.raises(ValueError, match="^COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT$"):
        repository.save_eligibility_subject(subject=changed)
    another = EligibilitySubject.model_validate(
        subject.model_dump(mode="json") | {"subject_revision": "other-subject", "content_hash": ""}
    )
    with pytest.raises(ValueError, match="^COMPOSITE_SUBJECT_DEFINITION_RESERVED_CONFLICT$"):
        repository.save_eligibility_subject(subject=another)
    with pytest.raises(ValueError, match="^COMPOSITE_SUBJECT_DEFINITION_RESERVED_CONFLICT$"):
        repository.save_definition(definition=finalization.definition)
    assert custody_state(repository) == before
    receipt = repository.finalize_eligibility_subject(finalization=finalization)
    after = custody_state(repository)
    repository.save_definition(definition=finalization.definition)
    assert custody_state(repository) == after
    assert repository.get_eligibility_finalization(key=subject_key(subject)) == receipt


@pytest.mark.parametrize("index", range(4))
def test_all_staged_controls_replay_before_and_after_publication_without_mutation(index):
    repository, subject, controls, finalization = retained_graph()
    control = controls[index]
    before = custody_state(repository)
    repository.save_subject_control(control=control)
    assert custody_state(repository) == before
    assert (
        repository.get_subject_control(
            key=subject_key(subject), kind=control.product_name, revision=control_revision(control)
        )
        == control
    )
    assert (
        repository.get_subject_control(
            key=subject_key(subject), kind=control.product_name, revision="absent-revision"
        )
        is None
    )
    assert (
        repository.get_subject_control(
            key=(*subject_key(subject)[:3], "absent-subject"),
            kind=control.product_name,
            revision=control_revision(control),
        )
        is None
    )
    repository.finalize_eligibility_subject(finalization=finalization)
    after = custody_state(repository)
    repository.save_subject_control(control=control)
    assert custody_state(repository) == after


def test_control_missing_subject_or_changed_retained_subject_never_writes():
    repository = InMemoryDpmCompositeRepository()
    subject, controls, _ = finalization_material()
    before = custody_state(repository)
    with pytest.raises(ValueError, match="^COMPOSITE_SUBJECT_NOT_FOUND$"):
        repository.save_subject_control(control=controls[0])
    assert custody_state(repository) == before
    changed = EligibilitySubject.model_validate(
        subject.model_dump(mode="json") | {"display_name": "other-content", "content_hash": ""}
    )
    repository.save_eligibility_subject(subject=changed)
    before = custody_state(repository)
    with pytest.raises(ValueError, match="^COMPOSITE_SUBJECT_RETAINED_SUBJECT_MISMATCH$"):
        repository.save_subject_control(control=controls[0])
    assert custody_state(repository) == before


def test_changed_control_revision_is_refused_after_finalization_and_content_before_it():
    repository, _, controls, finalization = retained_graph()
    wire = controls[0].model_dump(mode="json")
    wire["proposal"].update(proposed_at="2026-08-21T00:00:00.000000Z", content_hash="")
    wire["content_hash"] = ""
    changed = SubjectPolicyProposal.model_validate(wire)
    before = custody_state(repository)
    with pytest.raises(ValueError, match="^COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT$"):
        repository.save_subject_control(control=changed)
    assert custody_state(repository) == before
    repository.finalize_eligibility_subject(finalization=finalization)
    wire["proposal"].update(proposal_revision="another-policy", content_hash="")
    changed = SubjectPolicyProposal.model_validate(wire)
    after = custody_state(repository)
    with pytest.raises(ValueError, match="^COMPOSITE_SUBJECT_ALREADY_FINALIZED_CONFLICT$"):
        repository.save_subject_control(control=changed)
    assert custody_state(repository) == after


@pytest.mark.parametrize("occupied", ["subject", "definition", "membership", "universe"])
def test_finalization_refuses_preexisting_conflicts_before_any_publication_write(occupied):
    repository, subject, _, finalization = retained_graph()
    _, _, _, _, _, _, membership, universe = lifecycle_material()
    if occupied == "subject":
        repository._staged.subjects.clear()  # Deliberate missing retained graph.
    elif occupied == "definition":
        repository._definitions[subject_key(subject)[:3]] = finalization.definition
    elif occupied == "membership":
        repository._membership_revisions[
            (*subject_key(subject)[:3], membership.membership_revision)
        ] = membership
    else:
        repository._universe_attestations[
            (
                *subject_key(subject)[:3],
                membership.membership_revision,
                universe.attestation_version,
            )
        ] = universe
    before = custody_state(repository)
    code = {
        "subject": "COMPOSITE_SUBJECT_RETAINED_SUBJECT_MISMATCH",
        "definition": "COMPOSITE_SUBJECT_DEFINITION_RESERVED_CONFLICT",
    }.get(occupied, "COMPOSITE_ELIGIBILITY_TARGET_REVISION_EXISTS")
    with pytest.raises(ValueError, match=f"^{code}$"):
        repository.finalize_eligibility_subject(finalization=finalization)
    assert custody_state(repository) == before
    assert not repository._publications
    assert not repository._staged.receipts


def test_staged_records_are_not_exposed_as_legacy_monthly_controls():
    repository, subject, controls, _ = retained_graph()
    before = custody_state(repository)
    scope = dict(
        tenant_id=subject.tenant_id,
        composite_id=subject.composite_id,
        definition_version=subject.definition_version,
    )
    assert (
        repository.get_monthly_policy_proposal(
            **scope, month=subject.month, proposal_revision=control_revision(controls[0])
        )
        is None
    )
    assert repository.get_monthly_policy_approval(**scope, month=subject.month) is None
    assert (
        repository.get_monthly_evaluation_proposal(
            **scope, evaluation_revision=control_revision(controls[2])
        )
        is None
    )
    assert (
        repository.get_monthly_evaluation_approval(
            **scope, evaluation_revision=control_revision(controls[3])
        )
        is None
    )
    assert custody_state(repository) == before


def test_receipt_reader_rejects_valid_publication_reindexed_under_wrong_sequence():
    from src.core.composite_publication import publication_from_revision

    repository, subject, _, finalization = retained_graph()
    receipt = repository.finalize_eligibility_subject(finalization=finalization)
    member = next(iter(repository._membership_revisions.values()))
    publication = repository._publications[receipt.publication_sequence]
    repository._publications[receipt.publication_sequence] = publication_from_revision(
        revision=member,
        sequence=receipt.publication_sequence + 1,
        published_at=publication.published_at,
    )
    before = custody_state(repository)
    with pytest.raises(ValueError, match="^COMPOSITE_SUBJECT_RECEIPT_INTEGRITY_CONFLICT$"):
        repository.get_eligibility_finalization(key=subject_key(subject))
    assert custody_state(repository) == before
