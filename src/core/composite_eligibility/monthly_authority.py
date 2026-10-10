"""One immutable approved monthly chain; selection never relies on timestamps."""

from collections.abc import Sequence
from datetime import datetime

from src.core.composite_eligibility.evaluation_control import (
    MonthlyEvaluationApproval,
    HistoricalMonthlyEvaluationApproval,
    evaluation_key,
)
from src.core.composite_eligibility.monthly_amendment import (
    MonthlyAmendmentApprovalContent as MonthlyAmendmentApproval,
    MonthlyAmendmentProposalContent as MonthlyAmendmentProposal,
    MonthlyApproval,
    MonthlyCorrectionApproval,
    MonthlyApprovalBinding,
    MonthlyReceiptBinding,
    HistoricalMonthlyApprovalBinding,
    HistoricalMonthlyReceiptBinding,
)

MAX_MONTHLY_AUTHORITY_RECORDS = 64


def require_amendment_authority(
    proposal: MonthlyAmendmentProposal,
    approvals: Sequence[MonthlyApproval],
    predecessor_receipt: MonthlyReceiptBinding | HistoricalMonthlyReceiptBinding,
) -> None:
    """Caller holds the owning publication lock and supplies the exact retained graph."""
    selected = selected_monthly_approval(
        approvals, scope=evaluation_key(proposal)[:3], month=proposal.evaluation.month
    )
    require_source_correction(proposal, selected)
    if len(approvals) >= MAX_MONTHLY_AUTHORITY_RECORDS:
        raise ValueError("COMPOSITE_MONTHLY_AUTHORITY_HISTORY_LIMIT")
    root = next(
        item
        for item in approvals
        if isinstance(item, (MonthlyEvaluationApproval, HistoricalMonthlyEvaluationApproval))
    )
    if proposal.amendment.original_approval_binding != approval_binding(root):
        raise ValueError("COMPOSITE_MONTHLY_AUTHORITY_ORIGINAL_MISMATCH")
    if proposal.amendment.predecessor_receipt_binding != predecessor_receipt:
        raise ValueError("COMPOSITE_MONTHLY_AMENDMENT_PREDECESSOR_RECEIPT_MISMATCH")


def approval_binding(
    approval: MonthlyApproval,
) -> MonthlyApprovalBinding | HistoricalMonthlyApprovalBinding:
    model = (
        HistoricalMonthlyApprovalBinding
        if approval.product_version in {"v3", "v4"}
        else MonthlyApprovalBinding
    )
    return model.model_validate(
        dict(
            product_version=approval.product_version,
            revision=approval.proposal.evaluation_revision,
            digest=approval.content_hash,
        )
    )


def selected_monthly_approval(
    approvals: Sequence[MonthlyApproval],
    *,
    scope: tuple[str, str, str],
    month: str,
) -> MonthlyApproval:
    """Validate all retained links before returning the unique bounded chain tip."""
    if not approvals or len(approvals) > MAX_MONTHLY_AUTHORITY_RECORDS:
        raise ValueError("COMPOSITE_MONTHLY_AUTHORITY_HISTORY_UNAVAILABLE")
    if any(
        evaluation_key(item.proposal)[:3] != scope or item.proposal.evaluation.month != month
        for item in approvals
    ):
        raise ValueError("COMPOSITE_MONTHLY_AUTHORITY_SCOPE_MISMATCH")
    roots = [
        item
        for item in approvals
        if isinstance(item, (MonthlyEvaluationApproval, HistoricalMonthlyEvaluationApproval))
    ]
    if len(roots) != 1:
        raise ValueError("COMPOSITE_MONTHLY_AUTHORITY_ROOT_AMBIGUOUS")
    by_hash = {item.content_hash: item for item in approvals}
    if len(by_hash) != len(approvals):
        raise ValueError("COMPOSITE_MONTHLY_AUTHORITY_RECORD_AMBIGUOUS")
    children = _validated_children(approvals, by_hash, approval_binding(roots[0]))
    current: MonthlyApproval = roots[0]
    visited = set()
    while current.content_hash not in visited:
        visited.add(current.content_hash)
        child = children.get(current.content_hash)
        if child is None:
            if len(visited) != len(approvals):
                raise ValueError("COMPOSITE_MONTHLY_AUTHORITY_HISTORY_DISCONNECTED")
            return current
        current = child
    raise ValueError("COMPOSITE_MONTHLY_AUTHORITY_HISTORY_CYCLE")


def _validated_children(
    approvals: Sequence[MonthlyApproval],
    by_hash: dict[str, MonthlyApproval],
    root: MonthlyApprovalBinding | HistoricalMonthlyApprovalBinding,
) -> dict[str, MonthlyCorrectionApproval]:
    children = {}
    for item in approvals:
        if not isinstance(item, MonthlyAmendmentApproval):
            continue
        claims = item.proposal.amendment
        predecessor = by_hash.get(claims.predecessor_approval_binding.digest)
        if (
            predecessor is None
            or approval_binding(predecessor) != claims.predecessor_approval_binding
        ):
            raise ValueError("COMPOSITE_MONTHLY_AUTHORITY_PREDECESSOR_MISMATCH")
        if claims.original_approval_binding != root:
            raise ValueError("COMPOSITE_MONTHLY_AUTHORITY_ORIGINAL_MISMATCH")
        if predecessor.content_hash in children:
            raise ValueError("COMPOSITE_MONTHLY_AUTHORITY_FORK_FORBIDDEN")
        children[predecessor.content_hash] = item
    return children


def require_source_correction(
    proposal: MonthlyAmendmentProposal,
    predecessor: MonthlyApproval,
) -> None:
    """The independent approved policy and expected universe survive the source amendment."""
    prior = predecessor.proposal
    if (
        proposal.amendment.expected_authority_binding != approval_binding(predecessor)
        or evaluation_key(proposal)[:3] != evaluation_key(prior)[:3]
        or proposal.evaluation.month != prior.evaluation.month
    ):
        raise ValueError("COMPOSITE_MONTHLY_AMENDMENT_STALE_AUTHORITY")
    if datetime.fromisoformat(proposal.proposed_at) < datetime.fromisoformat(
        predecessor.approved_at
    ):
        raise ValueError("COMPOSITE_MONTHLY_AMENDMENT_CLOCK_MISMATCH")
    if proposal.policy_approval != prior.policy_approval:
        raise ValueError("COMPOSITE_MONTHLY_AMENDMENT_POLICY_CHANGE_UNSUPPORTED")
    if proposal.universe.expected_portfolio_ids != prior.universe.expected_portfolio_ids:
        raise ValueError("COMPOSITE_MONTHLY_AMENDMENT_POPULATION_CHANGE_UNSUPPORTED")
    old, new = prior.observations, proposal.observations
    if (old.source_cut_id, old.source_revision, old.portfolios) == (
        new.source_cut_id,
        new.source_revision,
        new.portfolios,
    ):
        raise ValueError("COMPOSITE_MONTHLY_AMENDMENT_SOURCE_UNCHANGED")
