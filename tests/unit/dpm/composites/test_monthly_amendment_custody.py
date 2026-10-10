"""Source amendments preserve originals and serialize independent approvals atomically."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest

from src.core.composite_eligibility.monthly_amendment import MonthlyAmendmentProposal
from src.core.composite_eligibility.publication import build_monthly_publication
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from tests.composite_monthly_amendment_helpers import (
    corrected_monthly_proposal,
    seed_complete_monthly_root,
    retain_following_month,
)


@pytest.fixture
def correction():
    repository = InMemoryDpmCompositeRepository()
    scope, original, parent = seed_complete_monthly_root(repository, coverage_to="2026-10-31")
    proposal = corrected_monthly_proposal(original, parent, sequence=original.publication_sequence)
    repository.save_universe_attestation(attestation=proposal.universe)
    return repository, scope, original, parent, proposal


def approve(repository, parent, proposal):
    approval, member, _ = build_monthly_publication(
        proposal,
        parent,
        approved_by="synthetic-independent-checker",
        approved_at=proposal.proposed_at,
    )
    repository.save_monthly_evaluation_approval(approval=approval)
    return approval, member


def resolve(repository, scope, approval):
    return repository.resolve_monthly_eligibility_evidence(
        **scope,
        evaluation_revision=approval.proposal.evaluation_revision,
        approval_content_hash=approval.content_hash,
    )


def test_two_corrections_retain_all_receipts_and_original_root(correction):
    repository, scope, original, parent, first = correction
    repository.save_monthly_evaluation_proposal(proposal=first)
    checked, member = approve(repository, parent, first)
    second_receipt = resolve(repository, scope, checked)
    second = corrected_monthly_proposal(
        second_receipt,
        member,
        sequence=second_receipt.publication_sequence,
        cash="50",
        revision=3,
    )
    repository.save_universe_attestation(attestation=second.universe)
    repository.save_monthly_evaluation_proposal(proposal=second)
    third_checked, _ = approve(repository, member, second)
    third_receipt = resolve(repository, scope, third_checked)
    assert [
        item.approval.proposal.evaluation.included_count
        for item in (original, second_receipt, third_receipt)
    ] == [1, 0, 1]
    assert third_receipt.lineage.original_approval_binding.digest == original.approval.content_hash
    assert third_receipt.lineage.predecessor_receipt_binding.digest == second_receipt.content_hash
    for receipt in (original, second_receipt, third_receipt):
        assert resolve(repository, scope, receipt.approval) == receipt
        repository.save_monthly_evaluation_proposal(proposal=receipt.approval.proposal)
        repository.save_monthly_evaluation_approval(approval=receipt.approval)
    assert len(repository._publications) == 4


@pytest.mark.parametrize("claim", ["receipt", "sequence", "original"])
def test_invalid_authority_claims_leave_all_custody_unchanged(correction, claim):
    repository, _, _, _, proposal = correction
    wire = proposal.model_dump(mode="json")
    if claim == "receipt":
        wire["amendment"]["predecessor_receipt_binding"]["digest"] = "sha256:" + "a" * 64
        code = "PREDECESSOR_RECEIPT_MISMATCH"
    elif claim == "original":
        wire["amendment"]["original_approval_binding"]["digest"] = "sha256:" + "a" * 64
        code = "ORIGINAL_MISMATCH"
    else:
        wire["amendment"]["expected_current_publication_sequence"] += 1
        code = "STALE_PROJECTION"
    wire["content_hash"] = ""
    invalid = MonthlyAmendmentProposal.model_validate(wire)
    before = deepcopy(
        (
            repository._monthly_evaluations,
            repository._monthly_evaluation_approvals,
            repository._membership_revisions,
            repository._universe_attestations,
            repository._publications,
        )
    )
    with pytest.raises(ValueError, match=code):
        repository.save_monthly_evaluation_proposal(proposal=invalid)
    assert (
        repository._monthly_evaluations,
        repository._monthly_evaluation_approvals,
        repository._membership_revisions,
        repository._universe_attestations,
        repository._publications,
    ) == before


def test_competing_source_corrections_publish_one_winner(correction):
    repository, scope, original, parent, first = correction
    second = corrected_monthly_proposal(
        original, parent, sequence=original.publication_sequence, cash="200", revision=3
    )
    for proposal in (first, second):
        repository.save_universe_attestation(attestation=proposal.universe)
        repository.save_monthly_evaluation_proposal(proposal=proposal)

    def compete(proposal):
        try:
            return approve(repository, parent, proposal)[0]
        except ValueError as error:
            assert "STALE_AUTHORITY" in str(error)
            return None

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(compete, (first, second)))
    winners = [item for item in results if item is not None]
    assert len(winners) == 1
    assert resolve(repository, scope, winners[0]).product_version == "v2"
    assert resolve(repository, scope, original.approval) == original
    assert len(repository._publications) == 3
    assert len(repository._monthly_evaluation_approvals) == 2


def test_earlier_month_correction_refuses_an_actual_later_approved_month(correction):
    repository, _, original, parent, _ = correction
    following = retain_following_month(repository, original, parent)
    proposal = corrected_monthly_proposal(original, following, sequence=repository._last_sequence)
    repository.save_universe_attestation(attestation=proposal.universe)
    before = deepcopy(repository._publications)
    with pytest.raises(ValueError, match="DEPENDENT_MONTH_UNSUPPORTED"):
        repository.save_monthly_evaluation_proposal(proposal=proposal)
    assert repository._publications == before


def test_bounded_history_refuses_another_correction_without_blocking_exact_retry(
    correction, monkeypatch
):
    import src.core.composite_eligibility.monthly_authority as authority

    repository, scope, _, parent, first = correction
    # Exercise a genuine retained chain at a small test bound; production remains64.
    assert authority.MAX_MONTHLY_AUTHORITY_RECORDS == 64
    monkeypatch.setattr(authority, "MAX_MONTHLY_AUTHORITY_RECORDS", 2)
    repository.save_monthly_evaluation_proposal(proposal=first)
    checked, member = approve(repository, parent, first)
    receipt = resolve(repository, scope, checked)
    second = corrected_monthly_proposal(
        receipt, member, sequence=receipt.publication_sequence, cash="50", revision=3
    )
    repository.save_universe_attestation(attestation=second.universe)
    before = deepcopy(repository._publications)
    with pytest.raises(ValueError, match="HISTORY_LIMIT"):
        repository.save_monthly_evaluation_proposal(proposal=second)
    assert repository._publications == before
    repository.save_monthly_evaluation_proposal(proposal=first)
    repository.save_monthly_evaluation_approval(approval=checked)
    assert resolve(repository, scope, checked) == receipt
    import src.core.composite_eligibility.monthly_evidence as evidence

    assert evidence.MAX_MONTHLY_AUTHORITY_RECORDS == 64
    monkeypatch.setattr(evidence, "MAX_MONTHLY_AUTHORITY_RECORDS", 1)
    with pytest.raises(ValueError, match="CUSTODY_INTEGRITY_CONFLICT"):
        evidence.require_monthly_receipt_lineage(receipt, lambda binding: None)


def test_amendment_cannot_predate_selected_approval_or_current_parent():
    from src.core.composite_eligibility.monthly_authority import require_source_correction

    repository = InMemoryDpmCompositeRepository()
    _, original, parent = seed_complete_monthly_root(
        repository, approved_at="2026-10-03T02:00:00.000000Z"
    )
    proposal = corrected_monthly_proposal(
        original,
        parent,
        sequence=original.publication_sequence,
        proposed_at_override="2026-10-02T01:00:00.000000Z",
    )
    repository.save_universe_attestation(attestation=proposal.universe)
    with pytest.raises(ValueError, match="CLOCK_MISMATCH"):
        require_source_correction(proposal, original.approval)
    with pytest.raises(ValueError, match="CLOCK_MISMATCH"):
        repository.save_monthly_evaluation_proposal(proposal=proposal)
    with pytest.raises(ValueError, match="CLOCK_MISMATCH"):
        build_monthly_publication(
            proposal, parent, approved_by="synthetic-checker", approved_at=proposal.proposed_at
        )


@pytest.mark.parametrize("mutation", ["window", "parent", "revision", "assembly", "marker"])
def test_amendment_model_refuses_incomplete_or_reused_projection_claims(correction, mutation):
    _, _, original, _, proposal = correction
    wire = proposal.model_dump(mode="json")
    if mutation == "window":
        wire["amendment"]["affected_from"] = "2026-09-02"
        code = "WINDOW_MISMATCH"
    elif mutation == "parent":
        wire["amendment"]["projection_parent_membership_binding"]["digest"] = "sha256:" + "f" * 64
        code = "PROJECTION_PARENT_MISMATCH"
    elif mutation == "revision":
        wire["evaluation_revision"] = original.approval.proposal.evaluation_revision
        code = "REVISION_REUSED"
    else:
        wire.pop(
            "source_assembly_evidence" if mutation == "assembly" else "publication_evidence_version"
        )
        code = "SOURCE_EVIDENCE_REQUIRED"
    wire["content_hash"] = ""
    with pytest.raises(ValueError, match=code):
        MonthlyAmendmentProposal.model_validate(wire)


def test_new_monthly_decoders_refuse_unknown_contract_versions():
    from src.core.composite_eligibility.monthly_amendment import (
        decode_monthly_approval,
        decode_monthly_proposal,
    )

    for decode in (decode_monthly_approval, decode_monthly_proposal):
        with pytest.raises(ValueError, match="VERSION_UNSUPPORTED"):
            decode({"product_version": "v5"})


def test_amended_receipt_requires_its_retained_predecessor_graph(correction):
    repository, scope, original, parent, proposal = correction
    repository.save_monthly_evaluation_proposal(proposal=proposal)
    checked, _ = approve(repository, parent, proposal)
    assert resolve(repository, scope, checked).product_version == "v2"
    # Deliberate loss of the ordinary approval; retained projection alone is insufficient.
    repository._monthly_evaluation_approvals.pop(
        (scope["tenant_id"], scope["composite_id"], original.approval.proposal.evaluation.month)
    )
    with pytest.raises(ValueError, match="CUSTODY_INTEGRITY_CONFLICT"):
        resolve(repository, scope, checked)


def test_actual_staged_finalization_cannot_accept_ordinary_amendment_authority():
    from tests.composite_monthly_amendment_staged_helpers import staged_root_amendment

    repository = InMemoryDpmCompositeRepository()
    proposal, parent = staged_root_amendment(repository)
    before = deepcopy(repository._publications)
    with pytest.raises(ValueError, match="STAGED_ROOT_UNSUPPORTED"):
        approve(repository, parent, proposal)
    assert repository._publications == before


def test_amendment_receipt_refuses_missing_parent_publication(correction):
    repository, scope, original, parent, proposal = correction
    repository.save_monthly_evaluation_proposal(proposal=proposal)
    checked, _ = approve(repository, parent, proposal)
    receipt = resolve(repository, scope, checked)
    retained = repository._publications.pop(original.publication_sequence)
    with pytest.raises(ValueError, match="CUSTODY_INTEGRITY_CONFLICT"):
        resolve(repository, scope, checked)
    repository._publications[retained.sequence] = retained
    assert resolve(repository, scope, checked) == receipt


def test_retained_amendment_revision_cannot_acquire_different_claims(correction):
    repository, _, _, _, proposal = correction
    repository.save_monthly_evaluation_proposal(proposal=proposal)
    wire = proposal.model_dump(mode="json")
    wire["amendment"]["reason"] = "Another individually valid correction reason"
    changed = MonthlyAmendmentProposal.model_validate(wire | {"content_hash": ""})
    with pytest.raises(ValueError, match="PROPOSAL_IMMUTABLE_CONFLICT"):
        repository.save_monthly_evaluation_proposal(proposal=changed)
    repository.save_monthly_evaluation_proposal(proposal=proposal)
