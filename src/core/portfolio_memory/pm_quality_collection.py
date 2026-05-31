"""PM-quality repository collection for portfolio-memory events."""

from src.core.pm_quality.repository import (
    DpmPmQualityReviewActionRepository,
    DpmPmQualityScoreRunRepository,
    DpmPmQualitySummaryInvocationRepository,
)
from src.core.portfolio_memory.models import DpmPortfolioMemoryEvent
from src.core.portfolio_memory.pm_quality_projection import (
    pm_quality_review_action_event,
    pm_quality_score_run_event,
    pm_quality_summary_invocation_event,
    score_run_includes_portfolio,
)


def pm_quality_memory_events(
    *,
    portfolio_id: str,
    score_run_repository: DpmPmQualityScoreRunRepository,
    review_action_repository: DpmPmQualityReviewActionRepository | None = None,
    summary_invocation_repository: DpmPmQualitySummaryInvocationRepository | None = None,
    limit: int,
) -> list[DpmPortfolioMemoryEvent]:
    """Collect PM-quality memory events with one PM-book scoped score-run scan."""

    score_runs_by_id = {
        score_run.score_run_id: score_run
        for score_run in score_run_repository.list_score_runs(limit=limit)
        if score_run_includes_portfolio(score_run=score_run, portfolio_id=portfolio_id)
    }
    events = [pm_quality_score_run_event(score_run) for score_run in score_runs_by_id.values()]
    if not score_runs_by_id:
        return events

    if review_action_repository is not None:
        events.extend(
            pm_quality_review_action_event(
                action=action,
                score_run=score_runs_by_id[action.target_id],
            )
            for action in review_action_repository.list_review_actions(
                target_type="SCORE_RUN",
                limit=limit,
            )
            if action.target_id in score_runs_by_id
        )
    if summary_invocation_repository is not None:
        events.extend(
            pm_quality_summary_invocation_event(
                invocation=invocation,
                score_run=score_runs_by_id[invocation.score_run_id],
            )
            for invocation in summary_invocation_repository.list_summary_invocations(limit=limit)
            if invocation.score_run_id in score_runs_by_id
        )
    return events
