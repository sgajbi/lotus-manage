"""Source-backed portfolio memory read-model assembly."""

from datetime import datetime, timezone
from typing import cast

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.construction.repository import ConstructionRepository
from src.core.mandate_repository import DpmMandateRepository
from src.core.pm_quality.repository import (
    DpmPmQualityReviewActionRepository,
    DpmPmQualityScoreRunRepository,
    DpmPmQualitySummaryInvocationRepository,
)
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.portfolio_memory.models import (
    DpmPortfolioMemory,
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemoryEventLookup,
    DpmPortfolioMemorySearchAppliedFilters,
    DpmPortfolioMemorySearchItem,
    DpmPortfolioMemorySearchPage,
    PortfolioMemorySupportabilityState,
)
from src.core.portfolio_memory.campaign_projection import (
    campaign_definition_events as _campaign_definition_events_for_definition,
)
from src.core.portfolio_memory.construction_projection import (
    construction_alternative_set_event as _construction_alternative_set_event,
    construction_selection_event as _construction_selection_event,
)
from src.core.portfolio_memory.governance import (
    client_communication_boundary_evidence as _client_communication_boundary_evidence,
    external_execution_boundary_evidence as _external_execution_boundary_evidence,
    portfolio_memory_governance_policy as _portfolio_memory_governance_policy,
    source_event_family_posture as _source_event_family_posture,
)
from src.core.portfolio_memory.mandate_projection import (
    mandate_exception_event as _mandate_exception_event,
    mandate_health_event as _mandate_health_event,
)
from src.core.portfolio_memory.pm_quality_projection import (
    pm_quality_review_action_event as _pm_quality_review_action_event,
    pm_quality_score_run_event as _pm_quality_score_run_event,
    pm_quality_summary_invocation_event as _pm_quality_summary_invocation_event,
    score_run_includes_portfolio as _score_run_includes_portfolio,
)
from src.core.portfolio_memory.outcome_projection import (
    outcome_review_events as _outcome_review_events,
)
from src.core.portfolio_memory.proof_pack_projection import (
    proof_pack_events as _proof_pack_events,
)
from src.core.portfolio_memory.search_filters import (
    count_values as _counts,
    dedupe_and_sort_events as _dedupe_and_sort,
    event_matches_search_filters as _event_matches_search_filters,
    event_source_systems as _event_source_systems,
    event_source_types as _event_source_types,
    normalize_portfolio_memory_search_filter,
)
from src.core.portfolio_memory.supportability import (
    portfolio_memory_state as _memory_state,
)
from src.core.portfolio_memory.wave_projection import (
    wave_events as _wave_events,
)
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves.models import (
    DpmRebalanceWave,
)
from src.core.waves.campaign_repository import DpmBulkReviewCampaignDefinitionRepository
from src.core.waves.repository import DpmWaveRepository


def build_portfolio_memory(
    *,
    portfolio_id: str,
    proof_pack_repository: DpmProofPackRepository,
    wave_repository: DpmWaveRepository,
    outcome_review_repository: DpmOutcomeReviewRepository,
    mandate_repository: DpmMandateRepository | None = None,
    construction_repository: ConstructionRepository | None = None,
    pm_quality_score_run_repository: DpmPmQualityScoreRunRepository | None = None,
    pm_quality_review_action_repository: DpmPmQualityReviewActionRepository | None = None,
    pm_quality_summary_invocation_repository: DpmPmQualitySummaryInvocationRepository | None = None,
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository | None = None,
    limit: int = 100,
    generated_at: datetime | None = None,
) -> DpmPortfolioMemory:
    """Compose manage-owned portfolio memory without recalculating source truth."""

    generated_at = generated_at or datetime.now(timezone.utc)
    events: list[DpmPortfolioMemoryEvent] = []
    proof_packs = proof_pack_repository.list_proof_packs(portfolio_id=portfolio_id, limit=limit)
    for proof_pack in proof_packs:
        events.extend(_proof_pack_events(proof_pack))

    if mandate_repository is not None:
        events.extend(
            _mandate_events(
                portfolio_id=portfolio_id,
                mandate_repository=mandate_repository,
                limit=limit,
            )
        )

    if construction_repository is not None:
        events.extend(
            _construction_events(
                portfolio_id=portfolio_id,
                construction_repository=construction_repository,
                limit=limit,
            )
        )

    for wave in _waves_for_portfolio(
        portfolio_id=portfolio_id,
        wave_repository=wave_repository,
        limit=limit,
    ):
        events.extend(_wave_events(wave=wave, portfolio_id=portfolio_id))

    if campaign_definition_repository is not None:
        events.extend(
            _campaign_definition_events(
                portfolio_id=portfolio_id,
                campaign_definition_repository=campaign_definition_repository,
                limit=limit,
            )
        )

    outcome_reviews = outcome_review_repository.list_outcome_reviews(
        portfolio_id=portfolio_id,
        limit=limit,
    )
    for review in outcome_reviews:
        persisted_events = outcome_review_repository.list_events(
            outcome_review_id=review.outcome_review_id
        )
        events.extend(_outcome_review_events(review=review, persisted_events=persisted_events))

    if pm_quality_score_run_repository is not None:
        events.extend(
            _pm_quality_score_run_events(
                portfolio_id=portfolio_id,
                score_run_repository=pm_quality_score_run_repository,
                limit=limit,
            )
        )
    if (
        pm_quality_score_run_repository is not None
        and pm_quality_review_action_repository is not None
    ):
        events.extend(
            _pm_quality_review_action_events(
                portfolio_id=portfolio_id,
                score_run_repository=pm_quality_score_run_repository,
                review_action_repository=pm_quality_review_action_repository,
                limit=limit,
            )
        )
    if (
        pm_quality_score_run_repository is not None
        and pm_quality_summary_invocation_repository is not None
    ):
        events.extend(
            _pm_quality_summary_invocation_events(
                portfolio_id=portfolio_id,
                score_run_repository=pm_quality_score_run_repository,
                summary_invocation_repository=pm_quality_summary_invocation_repository,
                limit=limit,
            )
        )

    events = _dedupe_and_sort(events)[:limit]
    event_type_counts = _counts(event.event_type for event in events)
    reason_codes = sorted({reason for event in events for reason in event.reason_codes})
    source_systems = sorted(
        {source_system for event in events for source_system in _event_source_systems(event)}
    )
    memory = DpmPortfolioMemory(
        portfolio_id=portfolio_id,
        event_count=len(events),
        supportability_state=_memory_state(events),
        event_type_counts=event_type_counts,
        source_systems=source_systems,
        reason_codes=reason_codes,
        governance_policy=_portfolio_memory_governance_policy(),
        source_event_family_posture=_source_event_family_posture(),
        external_execution_boundary=_external_execution_boundary_evidence(),
        client_communication_boundary=_client_communication_boundary_evidence(),
        events=events,
        content_hash="",
        generated_at=generated_at.isoformat(),
    )
    payload = memory.model_dump(mode="json")
    payload["content_hash"] = hash_canonical_payload(
        strip_keys(payload, exclude={"content_hash", "generated_at"})
    )
    return DpmPortfolioMemory.model_validate(payload)


def search_portfolio_memory(
    *,
    proof_pack_repository: DpmProofPackRepository,
    wave_repository: DpmWaveRepository,
    outcome_review_repository: DpmOutcomeReviewRepository,
    mandate_repository: DpmMandateRepository | None = None,
    construction_repository: ConstructionRepository | None = None,
    pm_quality_score_run_repository: DpmPmQualityScoreRunRepository | None = None,
    pm_quality_review_action_repository: DpmPmQualityReviewActionRepository | None = None,
    pm_quality_summary_invocation_repository: DpmPmQualitySummaryInvocationRepository | None = None,
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository | None = None,
    portfolio_ids: list[str] | None = None,
    event_type: str | None = None,
    supportability_state: PortfolioMemorySupportabilityState | None = None,
    source_system: str | None = None,
    source_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    source_scan_limit: int = 500,
    generated_at: datetime | None = None,
) -> DpmPortfolioMemorySearchPage:
    """Build a bounded Manage-local index over persisted portfolio-memory evidence."""

    generated_at = generated_at or datetime.now(timezone.utc)
    normalized_event_type = normalize_portfolio_memory_search_filter(event_type)
    normalized_supportability_state = cast(
        PortfolioMemorySupportabilityState | None,
        normalize_portfolio_memory_search_filter(cast(str | None, supportability_state)),
    )
    normalized_source_system = normalize_portfolio_memory_search_filter(source_system)
    normalized_source_type = normalize_portfolio_memory_search_filter(source_type)
    explicit_candidate_ids = {
        portfolio_id.strip() for portfolio_id in (portfolio_ids or []) if portfolio_id.strip()
    }
    candidate_ids = _memory_candidate_portfolio_ids(
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
        campaign_definition_repository=campaign_definition_repository,
        pm_quality_score_run_repository=pm_quality_score_run_repository,
        portfolio_ids=portfolio_ids,
        source_scan_limit=source_scan_limit,
    )
    search_rows: list[tuple[DpmPortfolioMemorySearchItem, list[DpmPortfolioMemoryEvent]]] = []
    for portfolio_id in candidate_ids:
        memory = build_portfolio_memory(
            portfolio_id=portfolio_id,
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=outcome_review_repository,
            mandate_repository=mandate_repository,
            construction_repository=construction_repository,
            pm_quality_score_run_repository=pm_quality_score_run_repository,
            pm_quality_review_action_repository=pm_quality_review_action_repository,
            pm_quality_summary_invocation_repository=pm_quality_summary_invocation_repository,
            campaign_definition_repository=campaign_definition_repository,
            limit=source_scan_limit,
            generated_at=generated_at,
        )
        if memory.event_count == 0:
            if (
                normalized_supportability_state != "EMPTY"
                or portfolio_id not in explicit_candidate_ids
            ):
                continue
        if (
            normalized_event_type is not None
            and normalized_event_type not in memory.event_type_counts
        ):
            continue
        if (
            normalized_supportability_state is not None
            and memory.supportability_state != normalized_supportability_state
        ):
            continue
        if (
            normalized_source_system is not None
            and normalized_source_system not in memory.source_systems
        ):
            continue
        matching_events = [
            event
            for event in memory.events
            if _event_matches_search_filters(
                event=event,
                event_type=normalized_event_type,
                supportability_state=normalized_supportability_state,
                source_system=normalized_source_system,
                source_type=normalized_source_type,
            )
        ]
        if (
            (
                normalized_event_type is not None
                or normalized_source_system is not None
                or normalized_source_type is not None
                or normalized_supportability_state is not None
            )
            and normalized_supportability_state != "EMPTY"
            and not matching_events
        ):
            continue
        latest_event = memory.events[0] if memory.events else None
        latest_matching_event = matching_events[0] if matching_events else None
        search_rows.append(
            (
                DpmPortfolioMemorySearchItem(
                    portfolio_id=memory.portfolio_id,
                    event_count=memory.event_count,
                    supportability_state=memory.supportability_state,
                    event_type_counts=memory.event_type_counts,
                    source_systems=memory.source_systems,
                    reason_codes=memory.reason_codes,
                    latest_event_time=latest_event.event_time if latest_event else None,
                    latest_event_type=latest_event.event_type if latest_event else None,
                    matching_event_count=len(matching_events),
                    latest_matching_event_time=(
                        latest_matching_event.event_time if latest_matching_event else None
                    ),
                    latest_matching_event_type=(
                        latest_matching_event.event_type if latest_matching_event else None
                    ),
                    latest_matching_event_id=(
                        latest_matching_event.event_id if latest_matching_event else None
                    ),
                    latest_matching_event_identity=(
                        latest_matching_event.event_identity if latest_matching_event else None
                    ),
                    latest_matching_event_source_system=(
                        latest_matching_event.source_system if latest_matching_event else None
                    ),
                    latest_matching_event_source_type=(
                        latest_matching_event.source_type if latest_matching_event else None
                    ),
                    latest_matching_event_source_id=(
                        latest_matching_event.source_id if latest_matching_event else None
                    ),
                    latest_matching_event_content_hash=(
                        latest_matching_event.content_hash if latest_matching_event else None
                    ),
                    content_hash=memory.content_hash,
                ),
                matching_events,
            )
        )

    search_rows = sorted(
        search_rows,
        key=lambda row: (row[0].latest_event_time or "", row[0].portfolio_id),
        reverse=True,
    )
    total_count = len(search_rows)
    supportability_state_counts = _counts(
        item.supportability_state for item, _events in search_rows
    )
    event_type_counts: dict[str, int] = {}
    matching_event_supportability_state_counts: dict[str, int] = {}
    matching_event_source_system_counts: dict[str, int] = {}
    matching_event_source_type_counts: dict[str, int] = {}
    source_system_counts: dict[str, int] = {}
    for item, matching_events in search_rows:
        for event in matching_events:
            event_type_counts[event.event_type] = event_type_counts.get(event.event_type, 0) + 1
            matching_event_supportability_state_counts[event.supportability_state] = (
                matching_event_supportability_state_counts.get(event.supportability_state, 0) + 1
            )
            for event_source_system in _event_source_systems(event):
                matching_event_source_system_counts[event_source_system] = (
                    matching_event_source_system_counts.get(event_source_system, 0) + 1
                )
            for event_source_type in _event_source_types(event):
                matching_event_source_type_counts[event_source_type] = (
                    matching_event_source_type_counts.get(event_source_type, 0) + 1
                )
        for represented_source_system in item.source_systems:
            source_system_counts[represented_source_system] = (
                source_system_counts.get(represented_source_system, 0) + 1
            )
    page_rows = search_rows[offset : offset + limit]
    page = [item for item, _events in page_rows]
    next_offset = offset + len(page)
    has_more = next_offset < total_count
    page_payload = {
        "items": page,
        "limit": limit,
        "offset": offset,
        "returned_count": len(page),
        "total_count": total_count,
        "has_more": has_more,
        "next_offset": next_offset if has_more else None,
        "scanned_portfolio_count": len(candidate_ids),
        "source_scan_limit": source_scan_limit,
        "applied_filters": DpmPortfolioMemorySearchAppliedFilters(
            portfolio_ids=sorted(explicit_candidate_ids),
            event_type=normalized_event_type,
            supportability_state=normalized_supportability_state,
            source_system=normalized_source_system,
            source_type=normalized_source_type,
        ),
        "supportability_state_counts": dict(sorted(supportability_state_counts.items())),
        "event_type_counts": dict(sorted(event_type_counts.items())),
        "matching_event_supportability_state_counts": dict(
            sorted(matching_event_supportability_state_counts.items())
        ),
        "matching_event_source_system_counts": dict(
            sorted(matching_event_source_system_counts.items())
        ),
        "matching_event_source_type_counts": dict(
            sorted(matching_event_source_type_counts.items())
        ),
        "source_system_counts": dict(sorted(source_system_counts.items())),
        "source_event_family_posture": _source_event_family_posture(),
        "external_execution_boundary": _external_execution_boundary_evidence(),
        "client_communication_boundary": _client_communication_boundary_evidence(),
        "generated_at": generated_at.isoformat(),
        "support_boundary": (
            "Manage-local memory search indexes persisted Manage evidence and explicit "
            "caller-supplied portfolio identifiers only. It exposes supported and deferred "
            "source-event family posture for Manage/report/AI/archive/PM-quality lineage, but "
            "does not discover the global portfolio universe, query external source-owner "
            "event stores, project OMS acknowledgement/fill/settlement events, project "
            "client-communication events, or recalculate source truth."
        ),
    }
    page_for_hash = DpmPortfolioMemorySearchPage.model_validate(
        {**page_payload, "content_hash": "sha256:pending"}
    )
    page_payload["content_hash"] = hash_canonical_payload(
        strip_keys(page_for_hash.model_dump(mode="json"), exclude={"content_hash", "generated_at"})
    )
    return DpmPortfolioMemorySearchPage.model_validate(page_payload)


def build_portfolio_memory_event_lookup(
    *,
    memory: DpmPortfolioMemory,
    event_id: str,
    support_boundary: str,
) -> DpmPortfolioMemoryEventLookup | None:
    """Select one portfolio-memory event and return a replay-stable lookup envelope."""

    for event in memory.events:
        if event.event_id != event_id:
            continue
        lookup = DpmPortfolioMemoryEventLookup(
            portfolio_id=memory.portfolio_id,
            event_id=event_id,
            event_identity=event.event_identity,
            event=event,
            memory_content_hash=memory.content_hash,
            content_hash="sha256:pending",
            generated_at=memory.generated_at,
            support_boundary=support_boundary,
        )
        payload = lookup.model_dump(mode="json")
        payload["content_hash"] = hash_canonical_payload(
            strip_keys(payload, exclude={"content_hash", "generated_at"})
        )
        return DpmPortfolioMemoryEventLookup.model_validate(payload)
    return None


def _memory_candidate_portfolio_ids(
    *,
    proof_pack_repository: DpmProofPackRepository,
    wave_repository: DpmWaveRepository,
    outcome_review_repository: DpmOutcomeReviewRepository,
    mandate_repository: DpmMandateRepository | None,
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository | None,
    pm_quality_score_run_repository: DpmPmQualityScoreRunRepository | None,
    portfolio_ids: list[str] | None,
    source_scan_limit: int,
) -> list[str]:
    candidates: set[str] = {
        portfolio_id.strip() for portfolio_id in (portfolio_ids or []) if portfolio_id.strip()
    }
    candidates.update(
        proof_pack.portfolio_id
        for proof_pack in proof_pack_repository.list_proof_packs(limit=source_scan_limit)
    )
    candidates.update(
        item.portfolio_id
        for wave in wave_repository.list_waves(limit=source_scan_limit)
        for item in wave.items
    )
    candidates.update(
        review.portfolio_id
        for review in outcome_review_repository.list_outcome_reviews(limit=source_scan_limit)
    )
    if mandate_repository is not None:
        exceptions, _cursor = mandate_repository.list_monitoring_exceptions(
            monitoring_run_id=None,
            mandate_id=None,
            portfolio_id=None,
            state=None,
            limit=source_scan_limit,
            cursor=None,
        )
        candidates.update(exception.portfolio_id for exception in exceptions)
    if campaign_definition_repository is not None:
        candidates.update(
            candidate.portfolio_id
            for definition in campaign_definition_repository.list_definitions(
                limit=source_scan_limit
            )
            for candidate in definition.candidates
        )
    if pm_quality_score_run_repository is not None:
        candidates.update(
            portfolio_id
            for score_run in pm_quality_score_run_repository.list_score_runs(
                limit=source_scan_limit
            )
            if score_run.book_scope_evidence is not None
            for portfolio_id in score_run.book_scope_evidence.member_portfolio_ids
        )
    return sorted(candidates)


def _mandate_events(
    *,
    portfolio_id: str,
    mandate_repository: DpmMandateRepository,
    limit: int,
) -> list[DpmPortfolioMemoryEvent]:
    twin = mandate_repository.get_latest_mandate_by_portfolio(portfolio_id=portfolio_id)
    events: list[DpmPortfolioMemoryEvent] = []
    if twin is not None:
        health_snapshot = mandate_repository.get_latest_health_snapshot(mandate_id=twin.mandate_id)
        if health_snapshot is not None:
            events.append(
                _mandate_health_event(
                    health_snapshot=health_snapshot,
                    source_lineage=twin.source_lineage,
                )
            )

    exceptions, _cursor = mandate_repository.list_monitoring_exceptions(
        monitoring_run_id=None,
        mandate_id=twin.mandate_id if twin is not None else None,
        portfolio_id=portfolio_id,
        state=None,
        limit=limit,
        cursor=None,
    )
    events.extend(_mandate_exception_event(exception) for exception in exceptions)
    return events


def _construction_events(
    *,
    portfolio_id: str,
    construction_repository: ConstructionRepository,
    limit: int,
) -> list[DpmPortfolioMemoryEvent]:
    alternative_sets = construction_repository.list_alternative_sets(
        portfolio_id=portfolio_id,
        limit=limit,
    )
    events: list[DpmPortfolioMemoryEvent] = []
    for alternative_set in alternative_sets:
        events.append(_construction_alternative_set_event(alternative_set))
        selection = construction_repository.get_selection(
            alternative_set_id=alternative_set.alternative_set_id
        )
        if selection is not None:
            events.append(
                _construction_selection_event(
                    alternative_set=alternative_set,
                    selection=selection,
                )
            )
    return events


def _campaign_definition_events(
    *,
    portfolio_id: str,
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository,
    limit: int,
) -> list[DpmPortfolioMemoryEvent]:
    definitions = [
        definition
        for definition in campaign_definition_repository.list_definitions(limit=limit)
        if any(candidate.portfolio_id == portfolio_id for candidate in definition.candidates)
    ]
    events: list[DpmPortfolioMemoryEvent] = []
    for definition in definitions:
        events.extend(
            _campaign_definition_events_for_definition(
                definition=definition,
                portfolio_id=portfolio_id,
            )
        )
    return events


def _pm_quality_score_run_events(
    *,
    portfolio_id: str,
    score_run_repository: DpmPmQualityScoreRunRepository,
    limit: int,
) -> list[DpmPortfolioMemoryEvent]:
    score_runs = score_run_repository.list_score_runs(limit=limit)
    return [
        _pm_quality_score_run_event(score_run)
        for score_run in score_runs
        if _score_run_includes_portfolio(score_run=score_run, portfolio_id=portfolio_id)
    ]


def _pm_quality_review_action_events(
    *,
    portfolio_id: str,
    score_run_repository: DpmPmQualityScoreRunRepository,
    review_action_repository: DpmPmQualityReviewActionRepository,
    limit: int,
) -> list[DpmPortfolioMemoryEvent]:
    score_runs_by_id = {
        score_run.score_run_id: score_run
        for score_run in score_run_repository.list_score_runs(limit=limit)
        if _score_run_includes_portfolio(score_run=score_run, portfolio_id=portfolio_id)
    }
    if not score_runs_by_id:
        return []
    return [
        _pm_quality_review_action_event(action=action, score_run=score_runs_by_id[action.target_id])
        for action in review_action_repository.list_review_actions(
            target_type="SCORE_RUN",
            limit=limit,
        )
        if action.target_id in score_runs_by_id
    ]


def _pm_quality_summary_invocation_events(
    *,
    portfolio_id: str,
    score_run_repository: DpmPmQualityScoreRunRepository,
    summary_invocation_repository: DpmPmQualitySummaryInvocationRepository,
    limit: int,
) -> list[DpmPortfolioMemoryEvent]:
    score_runs_by_id = {
        score_run.score_run_id: score_run
        for score_run in score_run_repository.list_score_runs(limit=limit)
        if _score_run_includes_portfolio(score_run=score_run, portfolio_id=portfolio_id)
    }
    if not score_runs_by_id:
        return []
    return [
        _pm_quality_summary_invocation_event(
            invocation=invocation,
            score_run=score_runs_by_id[invocation.score_run_id],
        )
        for invocation in summary_invocation_repository.list_summary_invocations(limit=limit)
        if invocation.score_run_id in score_runs_by_id
    ]


def _waves_for_portfolio(
    *,
    portfolio_id: str,
    wave_repository: DpmWaveRepository,
    limit: int,
) -> list[DpmRebalanceWave]:
    waves = wave_repository.list_waves(limit=limit)
    return [wave for wave in waves if any(item.portfolio_id == portfolio_id for item in wave.items)]
