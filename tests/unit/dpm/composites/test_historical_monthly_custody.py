"""The admitted policy uses the existing immutable root/source-correction authority chain."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Lock

import pytest

from src.api.services.composite_monthly_eligibility import (
    CompositeMonthlyEligibilityApplicationService,
    MonthlyApprovalRequest,
)
from src.api.services.composite_monthly_evaluation import (
    CompositeMonthlyEvaluationApplicationService,
)
from src.core.composite_eligibility.monthly_authority import (
    selected_monthly_approval,
    require_source_correction,
)
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from tests.composite_historical_policy_helpers import seed_historical_root, historical_approval_for
from tests.composite_monthly_amendment_helpers import corrected_monthly_proposal


def test_two_historical_corrections_preserve_original_raw_policy_and_all_selections():
    repository = InMemoryDpmCompositeRepository()
    port, scope, original, parent = seed_historical_root(repository)
    receipts = [original]
    for index, cash in ((2, "100"), (3, "50")):
        prior = receipts[-1]
        proposal = corrected_monthly_proposal(
            prior,
            parent,
            sequence=prior.publication_sequence,
            historical_verifier=port,
            revision=index,
            cash=cash,
        )
        repository.save_universe_attestation(attestation=proposal.universe)
        repository.save_monthly_evaluation_proposal(proposal=proposal)
        assert (
            selected_monthly_approval(
                [item.approval for item in receipts], scope=tuple(scope.values()), month="2026-09"
            )
            == prior.approval
        )
        checked, parent, _ = historical_approval_for(proposal, parent, port)
        repository.save_monthly_evaluation_approval(approval=checked)
        receipt = repository.resolve_monthly_eligibility_evidence(
            **scope,
            evaluation_revision=proposal.evaluation_revision,
            approval_content_hash=checked.content_hash,
        )
        receipts.append(receipt)
    assert [item.product_version for item in receipts] == ["v3", "v4", "v4"]
    assert [item.approval.proposal.evaluation.included_count for item in receipts] == [1, 0, 1]
    port.available = False
    for receipt in receipts:
        assert (
            repository.resolve_monthly_eligibility_evidence(
                **scope,
                evaluation_revision=receipt.approval.proposal.evaluation_revision,
                approval_content_hash=receipt.approval.content_hash,
            )
            == receipt
        )
        assert (
            receipt.approval.proposal.policy_approval == original.approval.proposal.policy_approval
        )
    assert receipts[-1].lineage.original_approval_binding.digest == original.approval.content_hash
    assert len(repository._publications) == 4


@pytest.mark.parametrize(
    "actors", [("controlled-current-checker",) * 4, ("checker-one", "checker-two")]
)
def test_concurrent_historical_approval_returns_one_exact_winner(actors):
    repository = InMemoryDpmCompositeRepository()
    port, scope, original, parent = seed_historical_root(repository)
    proposal = corrected_monthly_proposal(
        original, parent, sequence=original.publication_sequence, historical_verifier=port
    )
    repository.save_universe_attestation(attestation=proposal.universe)
    repository.save_monthly_evaluation_proposal(proposal=proposal)
    lock = Lock()
    counter = 0

    def clock():
        nonlocal counter
        with lock:
            counter += 1
            return (
                datetime.fromisoformat(proposal.proposed_at) + timedelta(seconds=counter)
            ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    service = CompositeMonthlyEvaluationApplicationService(
        CompositeMonthlyEligibilityApplicationService(
            repository, historical_admission=port, clock=clock
        )
    )
    command = MonthlyApprovalRequest(expected_proposal_content_hash=proposal.content_hash)

    def approve(actor):
        try:
            return service.approve(
                **scope,
                evaluation_revision=proposal.evaluation_revision,
                actor_id=actor,
                command=command,
            )
        except ValueError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=len(actors)) as pool:
        results = list(pool.map(approve, actors))
    approvals = [item for item in results if not isinstance(item, str)]
    assert len({item.content_hash for item in approvals}) == 1
    assert len(repository._publications) == 3
    if len(set(actors)) == 1:
        assert len(approvals) == len(actors)
    else:
        assert len(approvals) == 1
        assert any("CONFLICT" in item for item in results if isinstance(item, str))
    port.available = False
    assert approve(approvals[0].approved_by) == approvals[0]
    require_source_correction(proposal, original.approval)
