"""Batch source collection for portfolio-memory search."""

from collections import defaultdict
from dataclasses import dataclass

from src.core.pm_quality.models import (
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityReviewAction,
    DpmPmQualitySummaryInvocation,
)
from src.core.portfolio_memory.campaign_projection import campaign_definition_events
from src.core.portfolio_memory.construction_collection import construction_memory_events
from src.core.portfolio_memory.mandate_projection import (
    mandate_exception_event,
    mandate_health_event,
)
from src.core.portfolio_memory.models import DpmPortfolioMemoryEvent
from src.core.portfolio_memory.outcome_projection import outcome_review_events
from src.core.portfolio_memory.pm_quality_projection import (
    pm_quality_review_action_event,
    pm_quality_score_run_event,
    pm_quality_summary_invocation_event,
    score_run_includes_portfolio,
)
from src.core.portfolio_memory.proof_pack_projection import proof_pack_events
from src.core.portfolio_memory.read_request import validate_portfolio_memory_read_limit
from src.core.portfolio_memory.source_repositories import PortfolioMemorySourceRepositories
from src.core.portfolio_memory.wave_projection import wave_events


@dataclass(frozen=True)
class PortfolioMemorySearchSourceEvents:
    candidate_portfolio_ids: list[str]
    events_by_portfolio_id: dict[str, list[DpmPortfolioMemoryEvent]]


def collect_portfolio_memory_search_events(
    *,
    repositories: PortfolioMemorySourceRepositories,
    portfolio_ids: set[str],
    limit: int,
) -> PortfolioMemorySearchSourceEvents:
    """Scan each search source family once and group projected events by portfolio."""

    limit = validate_portfolio_memory_read_limit(limit=limit)
    candidates = set(portfolio_ids)
    events_by_portfolio_id: dict[str, list[DpmPortfolioMemoryEvent]] = defaultdict(list)
    for portfolio_id in candidates:
        events_by_portfolio_id.setdefault(portfolio_id, [])

    _collect_proof_pack_events(
        repositories=repositories,
        candidates=candidates,
        events_by_portfolio_id=events_by_portfolio_id,
        limit=limit,
    )
    _collect_wave_events(
        repositories=repositories,
        candidates=candidates,
        events_by_portfolio_id=events_by_portfolio_id,
        limit=limit,
    )
    _collect_outcome_review_events(
        repositories=repositories,
        candidates=candidates,
        events_by_portfolio_id=events_by_portfolio_id,
        limit=limit,
    )
    _collect_mandate_exception_events(
        repositories=repositories,
        candidates=candidates,
        events_by_portfolio_id=events_by_portfolio_id,
        limit=limit,
    )
    _collect_campaign_definition_events(
        repositories=repositories,
        candidates=candidates,
        events_by_portfolio_id=events_by_portfolio_id,
        limit=limit,
    )
    _collect_pm_quality_events(
        repositories=repositories,
        candidates=candidates,
        events_by_portfolio_id=events_by_portfolio_id,
        limit=limit,
    )
    _collect_mandate_health_events(
        repositories=repositories,
        candidates=candidates,
        events_by_portfolio_id=events_by_portfolio_id,
    )
    _collect_construction_events(
        repositories=repositories,
        candidates=candidates,
        events_by_portfolio_id=events_by_portfolio_id,
        limit=limit,
    )

    return PortfolioMemorySearchSourceEvents(
        candidate_portfolio_ids=sorted(candidates),
        events_by_portfolio_id=dict(events_by_portfolio_id),
    )


def _collect_proof_pack_events(
    *,
    repositories: PortfolioMemorySourceRepositories,
    candidates: set[str],
    events_by_portfolio_id: dict[str, list[DpmPortfolioMemoryEvent]],
    limit: int,
) -> None:
    for proof_pack in repositories.proof_pack_repository.list_proof_packs(limit=limit):
        candidates.add(proof_pack.portfolio_id)
        events_by_portfolio_id[proof_pack.portfolio_id].extend(proof_pack_events(proof_pack))


def _collect_wave_events(
    *,
    repositories: PortfolioMemorySourceRepositories,
    candidates: set[str],
    events_by_portfolio_id: dict[str, list[DpmPortfolioMemoryEvent]],
    limit: int,
) -> None:
    for wave in repositories.wave_repository.list_waves(limit=limit):
        matching_portfolio_ids = {
            item.portfolio_id for item in wave.items if item.portfolio_id.strip()
        }
        candidates.update(matching_portfolio_ids)
        for portfolio_id in matching_portfolio_ids:
            events_by_portfolio_id[portfolio_id].extend(
                wave_events(wave=wave, portfolio_id=portfolio_id)
            )


def _collect_outcome_review_events(
    *,
    repositories: PortfolioMemorySourceRepositories,
    candidates: set[str],
    events_by_portfolio_id: dict[str, list[DpmPortfolioMemoryEvent]],
    limit: int,
) -> None:
    for review in repositories.outcome_review_repository.list_outcome_reviews(limit=limit):
        candidates.add(review.portfolio_id)
        persisted_events = repositories.outcome_review_repository.list_events(
            outcome_review_id=review.outcome_review_id
        )
        events_by_portfolio_id[review.portfolio_id].extend(
            outcome_review_events(review=review, persisted_events=persisted_events)
        )


def _collect_mandate_exception_events(
    *,
    repositories: PortfolioMemorySourceRepositories,
    candidates: set[str],
    events_by_portfolio_id: dict[str, list[DpmPortfolioMemoryEvent]],
    limit: int,
) -> None:
    if repositories.mandate_repository is None:
        return

    exceptions, _cursor = repositories.mandate_repository.list_monitoring_exceptions(
        monitoring_run_id=None,
        mandate_id=None,
        portfolio_id=None,
        state=None,
        limit=limit,
        cursor=None,
    )
    for exception in exceptions:
        candidates.add(exception.portfolio_id)
        events_by_portfolio_id[exception.portfolio_id].append(mandate_exception_event(exception))


def _collect_mandate_health_events(
    *,
    repositories: PortfolioMemorySourceRepositories,
    candidates: set[str],
    events_by_portfolio_id: dict[str, list[DpmPortfolioMemoryEvent]],
) -> None:
    if repositories.mandate_repository is None:
        return
    for portfolio_id in sorted(candidates):
        twin = repositories.mandate_repository.get_latest_mandate_by_portfolio(
            portfolio_id=portfolio_id
        )
        if twin is None:
            continue
        health_snapshot = repositories.mandate_repository.get_latest_health_snapshot(
            mandate_id=twin.mandate_id
        )
        if health_snapshot is not None:
            events_by_portfolio_id[portfolio_id].append(
                mandate_health_event(
                    health_snapshot=health_snapshot,
                    source_lineage=twin.source_lineage,
                )
            )


def _collect_construction_events(
    *,
    repositories: PortfolioMemorySourceRepositories,
    candidates: set[str],
    events_by_portfolio_id: dict[str, list[DpmPortfolioMemoryEvent]],
    limit: int,
) -> None:
    if repositories.construction_repository is None:
        return
    for portfolio_id in sorted(candidates):
        events_by_portfolio_id[portfolio_id].extend(
            construction_memory_events(
                portfolio_id=portfolio_id,
                construction_repository=repositories.construction_repository,
                limit=limit,
            )
        )


def _collect_campaign_definition_events(
    *,
    repositories: PortfolioMemorySourceRepositories,
    candidates: set[str],
    events_by_portfolio_id: dict[str, list[DpmPortfolioMemoryEvent]],
    limit: int,
) -> None:
    if repositories.campaign_definition_repository is None:
        return
    for definition in repositories.campaign_definition_repository.list_definitions(limit=limit):
        matching_portfolio_ids = {
            candidate.portfolio_id
            for candidate in definition.candidates
            if candidate.portfolio_id.strip()
        }
        candidates.update(matching_portfolio_ids)
        for portfolio_id in matching_portfolio_ids:
            events_by_portfolio_id[portfolio_id].extend(
                campaign_definition_events(definition=definition, portfolio_id=portfolio_id)
            )


def _collect_pm_quality_events(
    *,
    repositories: PortfolioMemorySourceRepositories,
    candidates: set[str],
    events_by_portfolio_id: dict[str, list[DpmPortfolioMemoryEvent]],
    limit: int,
) -> None:
    if repositories.pm_quality_score_run_repository is None:
        return
    score_runs = repositories.pm_quality_score_run_repository.list_score_runs(limit=limit)
    score_runs_by_id = {score_run.score_run_id: score_run for score_run in score_runs}
    review_actions_by_score_run_id = _pm_quality_review_actions_by_score_run_id(
        repositories=repositories,
        score_runs_by_id=score_runs_by_id,
        limit=limit,
    )
    summary_invocations_by_score_run_id = _pm_quality_summary_invocations_by_score_run_id(
        repositories=repositories,
        score_runs_by_id=score_runs_by_id,
        limit=limit,
    )

    for score_run in score_runs:
        matching_portfolio_ids = _score_run_matching_portfolio_ids(
            score_run=score_run,
            candidate_portfolio_ids=candidates,
        )
        candidates.update(matching_portfolio_ids)
        for portfolio_id in matching_portfolio_ids:
            events_by_portfolio_id[portfolio_id].append(pm_quality_score_run_event(score_run))
            events_by_portfolio_id[portfolio_id].extend(
                pm_quality_review_action_event(action=action, score_run=score_run)
                for action in review_actions_by_score_run_id.get(score_run.score_run_id, [])
            )
            events_by_portfolio_id[portfolio_id].extend(
                pm_quality_summary_invocation_event(invocation=invocation, score_run=score_run)
                for invocation in summary_invocations_by_score_run_id.get(
                    score_run.score_run_id,
                    [],
                )
            )


def _pm_quality_review_actions_by_score_run_id(
    *,
    repositories: PortfolioMemorySourceRepositories,
    score_runs_by_id: dict[str, DpmPmOperatingQualityScoreRun],
    limit: int,
) -> dict[str, list[DpmPmQualityReviewAction]]:
    if repositories.pm_quality_review_action_repository is None or not score_runs_by_id:
        return {}
    actions_by_score_run_id: dict[str, list[DpmPmQualityReviewAction]] = defaultdict(list)
    for action in repositories.pm_quality_review_action_repository.list_review_actions(
        target_type="SCORE_RUN",
        limit=limit,
    ):
        if action.target_id in score_runs_by_id:
            actions_by_score_run_id[action.target_id].append(action)
    return dict(actions_by_score_run_id)


def _pm_quality_summary_invocations_by_score_run_id(
    *,
    repositories: PortfolioMemorySourceRepositories,
    score_runs_by_id: dict[str, DpmPmOperatingQualityScoreRun],
    limit: int,
) -> dict[str, list[DpmPmQualitySummaryInvocation]]:
    if repositories.pm_quality_summary_invocation_repository is None or not score_runs_by_id:
        return {}
    invocations_by_score_run_id: dict[str, list[DpmPmQualitySummaryInvocation]] = defaultdict(list)
    invocations = repositories.pm_quality_summary_invocation_repository.list_summary_invocations(
        limit=limit
    )
    for invocation in invocations:
        if invocation.score_run_id in score_runs_by_id:
            invocations_by_score_run_id[invocation.score_run_id].append(invocation)
    return dict(invocations_by_score_run_id)


def _score_run_matching_portfolio_ids(
    *,
    score_run: DpmPmOperatingQualityScoreRun,
    candidate_portfolio_ids: set[str],
) -> set[str]:
    if score_run.book_scope_evidence is None:
        return set()
    declared_ids = {
        portfolio_id
        for portfolio_id in score_run.book_scope_evidence.member_portfolio_ids
        if portfolio_id.strip()
    }
    matching_ids = set(declared_ids)
    matching_ids.update(
        portfolio_id
        for portfolio_id in candidate_portfolio_ids
        if score_run_includes_portfolio(score_run=score_run, portfolio_id=portfolio_id)
    )
    return matching_ids
