"""PM-quality repository collection for portfolio-memory events."""

from __future__ import annotations

from src.core.pm_quality.models import (
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityReviewAction,
    DpmPmQualitySummaryInvocation,
)
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
    tenant_id: str,
    portfolio_id: str,
    score_run_repository: DpmPmQualityScoreRunRepository,
    review_action_repository: DpmPmQualityReviewActionRepository | None = None,
    summary_invocation_repository: DpmPmQualitySummaryInvocationRepository | None = None,
    limit: int,
) -> list[DpmPortfolioMemoryEvent]:
    """Collect PM-quality memory events with one PM-book scoped score-run scan."""

    score_runs_by_id = _score_runs_by_id_for_portfolio(
        tenant_id=tenant_id,
        portfolio_id=portfolio_id,
        score_run_repository=score_run_repository,
        limit=limit,
    )
    events = _score_run_events(score_runs_by_id)
    if not score_runs_by_id:
        return events

    events.extend(
        _review_action_events(
            review_action_repository=review_action_repository,
            tenant_id=tenant_id,
            score_runs_by_id=score_runs_by_id,
            limit=limit,
        )
    )
    events.extend(
        _summary_invocation_events(
            summary_invocation_repository=summary_invocation_repository,
            tenant_id=tenant_id,
            score_runs_by_id=score_runs_by_id,
            limit=limit,
        )
    )
    return events


def _score_runs_by_id_for_portfolio(
    *,
    tenant_id: str,
    portfolio_id: str,
    score_run_repository: DpmPmQualityScoreRunRepository,
    limit: int,
) -> dict[str, DpmPmOperatingQualityScoreRun]:
    return {
        score_run.score_run_id: score_run
        for score_run in score_run_repository.list_score_runs(tenant_id=tenant_id, limit=limit)
        if score_run_includes_portfolio(score_run=score_run, portfolio_id=portfolio_id)
    }


def _score_run_events(
    score_runs_by_id: dict[str, DpmPmOperatingQualityScoreRun],
) -> list[DpmPortfolioMemoryEvent]:
    return [pm_quality_score_run_event(score_run) for score_run in score_runs_by_id.values()]


def _review_action_events(
    *,
    review_action_repository: DpmPmQualityReviewActionRepository | None,
    tenant_id: str,
    score_runs_by_id: dict[str, DpmPmOperatingQualityScoreRun],
    limit: int,
) -> list[DpmPortfolioMemoryEvent]:
    if review_action_repository is None:
        return []
    return [
        pm_quality_review_action_event(
            action=action,
            score_run=score_runs_by_id[action.target_id],
        )
        for action in _matching_score_run_review_actions(
            review_action_repository=review_action_repository,
            tenant_id=tenant_id,
            score_runs_by_id=score_runs_by_id,
            limit=limit,
        )
    ]


def _matching_score_run_review_actions(
    *,
    review_action_repository: DpmPmQualityReviewActionRepository,
    tenant_id: str,
    score_runs_by_id: dict[str, DpmPmOperatingQualityScoreRun],
    limit: int,
) -> list[DpmPmQualityReviewAction]:
    return [
        action
        for action in review_action_repository.list_review_actions(
            tenant_id=tenant_id,
            target_type="SCORE_RUN",
            limit=limit,
        )
        if action.target_id in score_runs_by_id
    ]


def _summary_invocation_events(
    *,
    summary_invocation_repository: DpmPmQualitySummaryInvocationRepository | None,
    tenant_id: str,
    score_runs_by_id: dict[str, DpmPmOperatingQualityScoreRun],
    limit: int,
) -> list[DpmPortfolioMemoryEvent]:
    if summary_invocation_repository is None:
        return []
    return [
        pm_quality_summary_invocation_event(
            invocation=invocation,
            score_run=score_runs_by_id[invocation.score_run_id],
        )
        for invocation in _matching_score_run_summary_invocations(
            summary_invocation_repository=summary_invocation_repository,
            tenant_id=tenant_id,
            score_runs_by_id=score_runs_by_id,
            limit=limit,
        )
    ]


def _matching_score_run_summary_invocations(
    *,
    summary_invocation_repository: DpmPmQualitySummaryInvocationRepository,
    tenant_id: str,
    score_runs_by_id: dict[str, DpmPmOperatingQualityScoreRun],
    limit: int,
) -> list[DpmPmQualitySummaryInvocation]:
    return [
        invocation
        for invocation in summary_invocation_repository.list_summary_invocations(
            tenant_id=tenant_id,
            limit=limit,
        )
        if invocation.score_run_id in score_runs_by_id
    ]
