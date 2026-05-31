"""PM operating-quality projection helpers for portfolio memory."""

from src.core.pm_quality.models import DpmPmOperatingQualityScoreRun


def score_run_includes_portfolio(
    *,
    score_run: DpmPmOperatingQualityScoreRun,
    portfolio_id: str,
) -> bool:
    """Return whether PM-book evidence links a score run to a portfolio."""

    if score_run.book_scope_evidence is None:
        return False
    if portfolio_id in score_run.book_scope_evidence.member_portfolio_ids:
        return True
    return any(
        ref.source_type == "PORTFOLIO_MANAGER_BOOK_MEMBER"
        and (ref.source_id == portfolio_id or ref.source_id.endswith(f":{portfolio_id}"))
        for ref in score_run.book_scope_evidence.source_refs
    )
