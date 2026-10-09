"""Bind membership decision changes to the declared inclusive correction window."""

from datetime import date

from src.core.composite_membership import DpmCompositeMembershipRevision

DecisionEvidence = tuple[str, str | None, bool, str | None, str]
DecisionInterval = tuple[str, int, int, DecisionEvidence]


def require_correction_window(
    *, parent: DpmCompositeMembershipRevision, revision: DpmCompositeMembershipRevision
) -> None:
    """Compare retained decision evidence outside the impact window, without expanding days.

    Adjacent equivalent segments are one effective decision. Source and approval
    evidence remain part of that decision; a correction cannot silently replace
    those references on dates it declares unaffected.
    """
    revision = DpmCompositeMembershipRevision.model_validate(revision.model_dump(mode="json"))
    parent = DpmCompositeMembershipRevision.model_validate(parent.model_dump(mode="json"))
    if revision.affected_from is None or revision.affected_to is None:
        raise ValueError("COMPOSITE_MEMBERSHIP_CORRECTION_WINDOW_REQUIRED")
    start = date.fromisoformat(revision.affected_from).toordinal()
    end = date.fromisoformat(revision.affected_to).toordinal()
    if _unaffected_intervals(parent, start, end) != _unaffected_intervals(revision, start, end):
        raise ValueError("COMPOSITE_MEMBERSHIP_CORRECTION_OUTSIDE_WINDOW")


def _unaffected_intervals(
    revision: DpmCompositeMembershipRevision, start: int, end: int
) -> list[DecisionInterval]:
    fragments: list[DecisionInterval] = []
    for decision in revision.decisions:
        first = date.fromisoformat(decision.effective_from).toordinal()
        last = (
            date.max.toordinal()
            if decision.effective_to is None
            else date.fromisoformat(decision.effective_to).toordinal()
        )
        evidence: DecisionEvidence = (
            decision.status,
            decision.reason_code,
            decision.discretionary,
            decision.approval_ref,
            decision.source_snapshot_id,
        )
        for lower, upper in ((first, min(last, start - 1)), (max(first, end + 1), last)):
            if lower <= upper:
                fragments.append((decision.portfolio_id, lower, upper, evidence))
    merged: list[DecisionInterval] = []
    for member, first, last, evidence in sorted(fragments, key=lambda item: item[:3]):
        if (
            merged
            and merged[-1][0] == member
            and merged[-1][2] + 1 == first
            and (merged[-1][3] == evidence)
        ):
            merged[-1] = (member, merged[-1][1], last, evidence)
        else:
            merged.append((member, first, last, evidence))
    return merged
