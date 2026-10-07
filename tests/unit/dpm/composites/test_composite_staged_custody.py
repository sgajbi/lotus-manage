"""Retained graph proof; synthetic receipts cannot certify economic authority."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from src.core.composite_eligibility.staged_subject import subject_key
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from tests.composite_staged_eligibility_helpers import finalization_material


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
