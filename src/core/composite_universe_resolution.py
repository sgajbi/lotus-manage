"""Pure effective-window reconciliation shared by legacy and monthly publication."""

from datetime import date, timedelta
from src.core.composite_membership import DpmCompositeMembershipRevision


def reconcile_composite_universe(
    *,
    revision: DpmCompositeMembershipRevision,
    coverage_from: date,
    coverage_to: date,
    expected_portfolio_ids: list[str],
) -> tuple[list[str], list[str], list[str], list[str]]:
    if coverage_to < coverage_from:
        raise ValueError("COMPOSITE_UNIVERSE_COVERAGE_WINDOW_INVALID")
    overlapping: dict[str, list[tuple[date, date]]] = {}
    for decision in revision.decisions:
        start = date.fromisoformat(decision.effective_from)
        end = date.fromisoformat(decision.effective_to) if decision.effective_to else date.max
        if start <= coverage_to and end >= coverage_from:
            overlapping.setdefault(decision.portfolio_id, []).append(
                (max(start, coverage_from), min(end, coverage_to))
            )
    observed = sorted(overlapping)
    expected = set(expected_portfolio_ids)
    missing = sorted(expected - set(observed))
    unexpected = sorted(set(observed) - expected)
    gaps = sorted(
        portfolio_id
        for portfolio_id in expected & set(observed)
        if not _covers_window(
            windows=overlapping[portfolio_id],
            coverage_from=coverage_from,
            coverage_to=coverage_to,
        )
    )
    return observed, missing, unexpected, gaps


def _covers_window(
    *, windows: list[tuple[date, date]], coverage_from: date, coverage_to: date
) -> bool:
    covered_to: date | None = None
    for start, end in sorted(windows):
        if covered_to is None:
            if start > coverage_from:
                return False
        elif start > covered_to + timedelta(days=1):
            return False
        covered_to = end if covered_to is None else max(covered_to, end)
        if covered_to >= coverage_to:
            return True
    return False
