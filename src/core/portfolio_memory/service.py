"""Source-backed portfolio memory read-model assembly."""

from datetime import datetime, timezone
from typing import cast

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.construction.repository import ConstructionRepository
from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import (
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
    DpmSourceProductLineage,
)
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
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.portfolio_memory.models import (
    DpmPortfolioMemory,
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemoryEventLookup,
    DpmPortfolioMemorySearchAppliedFilters,
    DpmPortfolioMemorySearchItem,
    DpmPortfolioMemorySearchPage,
    DpmPortfolioMemorySourceRef,
    PortfolioMemorySupportabilityState,
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
from src.core.portfolio_memory.pm_quality_projection import (
    score_run_includes_portfolio as _score_run_includes_portfolio,
)
from src.core.portfolio_memory.outcome_projection import (
    outcome_review_events as _outcome_review_events,
)
from src.core.portfolio_memory.proof_pack_projection import (
    proof_pack_events as _proof_pack_events,
)
from src.core.portfolio_memory.source_refs import (
    campaign_definition_artifact_ref as _campaign_definition_artifact_ref,
    campaign_definition_source_refs as _campaign_definition_source_refs,
    from_outcome_source_ref as _from_outcome_source_ref,
    from_source_product_lineage as _from_source_product_lineage,
    from_wave_source_ref as _from_wave_source_ref,
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
    assignment_sla_state as _assignment_sla_state,
    assignment_task_state as _assignment_task_state,
    maker_checker_state as _maker_checker_state,
    monitoring_exception_state as _monitoring_exception_state,
    pm_quality_review_action_state as _pm_quality_review_action_state,
    pm_quality_summary_invocation_state as _pm_quality_summary_invocation_state,
    portfolio_memory_state as _memory_state,
    source_supportability_state as _state,
)
from src.core.portfolio_memory.wave_projection import (
    wave_events as _wave_events,
)
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves.models import (
    DpmRebalanceWave,
)
from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionAssignmentAction,
    DpmBulkReviewCampaignDefinitionAssignmentTask,
    DpmBulkReviewCampaignDefinitionAssignmentTaskTransition,
    DpmBulkReviewCampaignDefinitionMakerCheckerControl,
    DpmBulkReviewCampaignDefinitionApprovalDecision,
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


def _mandate_health_event(
    *,
    health_snapshot: DpmMandateHealthSnapshot,
    source_lineage: list[DpmSourceProductLineage],
) -> DpmPortfolioMemoryEvent:
    reason_codes = sorted(
        {reason.reason_code for reason in health_snapshot.top_reasons if reason.reason_code}
        | {score.reason_code for score in health_snapshot.dimension_scores if score.reason_code}
    )
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:mandate:{health_snapshot.mandate_id}:health:{health_snapshot.health_snapshot_id}",
        event_type="MANDATE_HEALTH_SNAPSHOT",
        event_time=health_snapshot.calculated_at.isoformat(),
        actor="lotus-manage",
        source_system="lotus-manage",
        source_type="DPM_MANDATE_HEALTH_SNAPSHOT",
        source_id=health_snapshot.health_snapshot_id,
        status=health_snapshot.health_state.value,
        supportability_state=_state(health_snapshot.health_state.value),
        summary=(
            f"Mandate health snapshot {health_snapshot.health_snapshot_id} calculated as "
            f"{health_snapshot.health_state.value}."
        ),
        reason_codes=reason_codes,
        source_refs=[_from_source_product_lineage(ref) for ref in source_lineage],
        artifact_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="DPM_MANDATE_HEALTH_EVIDENCE_REF",
                source_id=evidence_ref,
            )
            for evidence_ref in health_snapshot.evidence_refs
        ],
        content_hash=hash_canonical_payload(health_snapshot.model_dump(mode="json")),
        metadata={
            "mandate_id": health_snapshot.mandate_id,
            "as_of_date": health_snapshot.as_of_date.isoformat(),
            "health_score": health_snapshot.health_score,
            "recommended_action": health_snapshot.recommended_action.value,
            "source_readiness_state": health_snapshot.source_readiness_state,
            "dimension_count": len(health_snapshot.dimension_scores),
        },
    )


def _mandate_exception_event(
    exception: DpmMonitoringException,
) -> DpmPortfolioMemoryEvent:
    reason_codes = sorted(
        {
            exception.reason_code,
            exception.dimension.value,
            exception.severity.value,
        }
    )
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:mandate:{exception.mandate_id}:exception:{exception.exception_id}",
        event_type="MANDATE_MONITORING_EXCEPTION",
        event_time=exception.detected_at.isoformat(),
        actor="lotus-manage",
        source_system="lotus-manage",
        source_type="DPM_MONITORING_EXCEPTION",
        source_id=exception.exception_id,
        status=exception.state,
        supportability_state=_monitoring_exception_state(exception),
        summary=(
            f"Mandate monitoring exception {exception.exception_id} is {exception.state} "
            f"for {exception.dimension.value}."
        ),
        reason_codes=reason_codes,
        source_refs=[_from_source_product_lineage(ref) for ref in exception.source_lineage],
        artifact_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="DPM_MONITORING_RUN",
                source_id=exception.monitoring_run_id,
            )
        ]
        if exception.monitoring_run_id is not None
        else [],
        content_hash=hash_canonical_payload(exception.model_dump(mode="json")),
        metadata={
            "mandate_id": exception.mandate_id,
            "monitoring_run_id": exception.monitoring_run_id,
            "as_of_date": exception.as_of_date.isoformat(),
            "dimension": exception.dimension.value,
            "severity": exception.severity.value,
            "recommended_action": exception.recommended_action.value,
            "measured_value": str(exception.measured_value)
            if exception.measured_value is not None
            else None,
            "threshold_value": str(exception.threshold_value)
            if exception.threshold_value is not None
            else None,
            "resolved_at": exception.resolved_at.isoformat()
            if exception.resolved_at is not None
            else None,
            "resolution_reason": exception.resolution_reason,
        },
    )


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
        events.append(_campaign_definition_event(definition=definition, portfolio_id=portfolio_id))
        events.extend(
            _campaign_approval_decision_event(definition=definition, decision=decision)
            for decision in definition.approval_decisions
        )
        events.extend(
            _campaign_assignment_action_event(definition=definition, action=action)
            for action in definition.assignment_actions
        )
        events.extend(
            _campaign_assignment_task_event(definition=definition, task=task)
            for task in definition.assignment_tasks
        )
        events.extend(
            _campaign_assignment_task_transition_event(
                definition=definition,
                task=task,
                transition=transition,
            )
            for task in definition.assignment_tasks
            for transition in task.transitions
        )
        events.extend(
            _campaign_maker_checker_control_event(definition=definition, control=control)
            for control in definition.maker_checker_controls
        )
    return events


def _campaign_definition_event(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    portfolio_id: str,
) -> DpmPortfolioMemoryEvent:
    matching_candidates = [
        candidate for candidate in definition.candidates if candidate.portfolio_id == portfolio_id
    ]
    return DpmPortfolioMemoryEvent(
        event_id=(
            "memory:campaign_definition:"
            f"{definition.campaign_id}:{definition.campaign_version}:definition"
        ),
        event_type="BULK_REVIEW_CAMPAIGN_DEFINITION",
        event_time=definition.created_at.isoformat(),
        actor=definition.created_by,
        source_system="lotus-manage",
        source_type="BULK_REVIEW_CAMPAIGN_DEFINITION",
        source_id=f"{definition.campaign_id}:{definition.campaign_version}",
        status=definition.status,
        supportability_state=_state(definition.status),
        summary=(
            f"Bulk-review campaign definition {definition.campaign_id} "
            f"version {definition.campaign_version} is {definition.status}."
        ),
        reason_codes=sorted(
            {
                "BULK_REVIEW_CAMPAIGN_DEFINITION_PERSISTED",
                definition.status,
                *(
                    ref.supportability_state
                    for ref in _campaign_definition_source_refs(
                        definition=definition,
                        portfolio_id=portfolio_id,
                    )
                    if ref.supportability_state
                ),
            }
        ),
        source_refs=_campaign_definition_source_refs(
            definition=definition,
            portfolio_id=portfolio_id,
        ),
        artifact_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="BulkReviewCampaignDefinition",
                source_id=f"{definition.campaign_id}:{definition.campaign_version}",
                source_version=definition.product_version,
                content_hash=definition.content_hash,
            )
        ],
        content_hash=definition.content_hash,
        metadata={
            "campaign_id": definition.campaign_id,
            "campaign_version": definition.campaign_version,
            "as_of_date": definition.as_of_date,
            "candidate_count": len(definition.candidates),
            "matching_candidate_count": len(matching_candidates),
            "eligible_portfolio_types": definition.eligible_portfolio_types,
            "governance_evidence_present": definition.governance is not None,
            "approval_decision_count": len(definition.approval_decisions),
            "assignment_action_count": len(definition.assignment_actions),
            "assignment_task_count": len(definition.assignment_tasks),
            "maker_checker_control_count": len(definition.maker_checker_controls),
            "global_portfolio_universe_discovered": False,
            "membership_recalculated": False,
            "raw_campaign_payload_projected": False,
            "external_workflow_orchestration_claimed": False,
            "client_contact_claimed": False,
            "external_execution_claimed": False,
        },
    )


def _campaign_approval_decision_event(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    decision: DpmBulkReviewCampaignDefinitionApprovalDecision,
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=(
            "memory:campaign_definition:"
            f"{definition.campaign_id}:{definition.campaign_version}:approval:{decision.decision_id}"
        ),
        event_type="BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION",
        event_time=decision.decided_at.isoformat(),
        actor=decision.decided_by,
        source_system="lotus-manage",
        source_type="BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION",
        source_id=decision.decision_id,
        status=decision.decision_type,
        supportability_state=_state(decision.decision_type),
        summary=f"Bulk-review campaign approval decision {decision.decision_type} recorded.",
        reason_codes=[
            "BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_RECORDED",
            decision.decision_type,
        ],
        source_refs=[_from_wave_source_ref(ref) for ref in decision.source_refs],
        artifact_refs=[_campaign_definition_artifact_ref(definition)],
        content_hash=decision.content_hash,
        metadata={
            "campaign_id": definition.campaign_id,
            "campaign_version": definition.campaign_version,
            "decision_ref": decision.decision_ref,
            "correlation_id": decision.correlation_id,
            "forbidden_actions": decision.forbidden_actions,
            "trade_approval_claimed": False,
            "external_execution_claimed": False,
        },
    )


def _campaign_assignment_action_event(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    action: DpmBulkReviewCampaignDefinitionAssignmentAction,
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=(
            "memory:campaign_definition:"
            f"{definition.campaign_id}:{definition.campaign_version}:assignment-action:{action.action_id}"
        ),
        event_type="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION",
        event_time=action.recorded_at.isoformat(),
        actor=action.recorded_by,
        source_system="lotus-manage",
        source_type="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION",
        source_id=action.action_id,
        status=action.action_type,
        supportability_state=_assignment_sla_state(action.sla_posture),
        summary=f"Bulk-review campaign assignment action {action.action_type} recorded.",
        reason_codes=[
            "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_RECORDED",
            action.action_type,
            action.sla_posture,
        ],
        source_refs=[_from_wave_source_ref(ref) for ref in action.source_refs],
        artifact_refs=[_campaign_definition_artifact_ref(definition)],
        content_hash=action.content_hash,
        metadata={
            "campaign_id": definition.campaign_id,
            "campaign_version": definition.campaign_version,
            "action_ref": action.action_ref,
            "assigned_actor_count": len(action.assigned_actor_ids),
            "escalation_tier": action.escalation_tier,
            "sla_posture": action.sla_posture,
            "correlation_id": action.correlation_id,
            "forbidden_actions": action.forbidden_actions,
            "external_workflow_orchestration_claimed": False,
            "client_contact_claimed": False,
            "external_execution_claimed": False,
        },
    )


def _campaign_assignment_task_event(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    task: DpmBulkReviewCampaignDefinitionAssignmentTask,
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=(
            "memory:campaign_definition:"
            f"{definition.campaign_id}:{definition.campaign_version}:assignment-task:{task.task_id}"
        ),
        event_type="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK",
        event_time=task.opened_at.isoformat(),
        actor=task.opened_by,
        source_system="lotus-manage",
        source_type="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK",
        source_id=task.task_id,
        status=task.status,
        supportability_state=_assignment_task_state(task.status, task.sla_posture),
        summary=f"Bulk-review campaign assignment task {task.task_ref} is {task.status}.",
        reason_codes=[
            "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_RECORDED",
            task.status,
            task.sla_posture,
        ],
        source_refs=[_from_wave_source_ref(ref) for ref in task.source_refs],
        artifact_refs=[_campaign_definition_artifact_ref(definition)],
        content_hash=task.content_hash,
        metadata={
            "campaign_id": definition.campaign_id,
            "campaign_version": definition.campaign_version,
            "task_ref": task.task_ref,
            "task_type": task.task_type,
            "assigned_actor_count": len(task.assigned_actor_ids),
            "escalation_tier": task.escalation_tier,
            "sla_posture": task.sla_posture,
            "transition_count": len(task.transitions),
            "correlation_id": task.correlation_id,
            "forbidden_actions": task.forbidden_actions,
            "external_workflow_orchestration_claimed": False,
            "approval_state_mutation_claimed": False,
            "client_contact_claimed": False,
            "external_execution_claimed": False,
        },
    )


def _campaign_assignment_task_transition_event(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    task: DpmBulkReviewCampaignDefinitionAssignmentTask,
    transition: DpmBulkReviewCampaignDefinitionAssignmentTaskTransition,
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=(
            "memory:campaign_definition:"
            f"{definition.campaign_id}:{definition.campaign_version}:"
            f"assignment-task:{task.task_id}:transition:{transition.transition_id}"
        ),
        event_type="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION",
        event_time=transition.transitioned_at.isoformat(),
        actor=transition.transitioned_by,
        source_system="lotus-manage",
        source_type="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION",
        source_id=transition.transition_id,
        status=transition.to_status,
        supportability_state=_assignment_task_state(
            transition.to_status,
            transition.sla_posture,
        ),
        summary=(
            f"Bulk-review campaign assignment task {task.task_ref} transition "
            f"{transition.transition_type} recorded."
        ),
        reason_codes=[
            "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION_RECORDED",
            transition.transition_type,
            transition.to_status,
            transition.sla_posture,
        ],
        source_refs=[_from_wave_source_ref(ref) for ref in transition.source_refs],
        artifact_refs=[
            _campaign_definition_artifact_ref(definition),
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK",
                source_id=task.task_id,
                content_hash=task.content_hash,
            ),
        ],
        content_hash=transition.content_hash,
        metadata={
            "campaign_id": definition.campaign_id,
            "campaign_version": definition.campaign_version,
            "task_id": task.task_id,
            "task_ref": task.task_ref,
            "task_type": task.task_type,
            "transition_ref": transition.transition_ref,
            "transition_type": transition.transition_type,
            "from_status": transition.from_status,
            "to_status": transition.to_status,
            "assigned_actor_count": len(transition.assigned_actor_ids),
            "escalation_tier": transition.escalation_tier,
            "sla_posture": transition.sla_posture,
            "due_at_present": transition.due_at is not None,
            "correlation_id": transition.correlation_id,
            "transition_reason_projected": False,
            "external_workflow_orchestration_claimed": False,
            "approval_state_mutation_claimed": False,
            "client_contact_claimed": False,
            "external_execution_claimed": False,
        },
    )


def _campaign_maker_checker_control_event(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    control: DpmBulkReviewCampaignDefinitionMakerCheckerControl,
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=(
            "memory:campaign_definition:"
            f"{definition.campaign_id}:{definition.campaign_version}:maker-checker:{control.control_id}"
        ),
        event_type="BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL",
        event_time=control.recorded_at.isoformat(),
        actor=control.recorded_by,
        source_system="lotus-manage",
        source_type="BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL",
        source_id=control.control_id,
        status=control.control_outcome,
        supportability_state=_maker_checker_state(control.control_outcome),
        summary=(
            f"Bulk-review campaign maker-checker control {control.control_action} "
            f"recorded with {control.control_outcome} outcome."
        ),
        reason_codes=[
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_RECORDED",
            control.control_action,
            control.control_outcome,
        ],
        source_refs=[_from_wave_source_ref(ref) for ref in control.source_refs],
        artifact_refs=[_campaign_definition_artifact_ref(definition)],
        content_hash=control.content_hash,
        metadata={
            "campaign_id": definition.campaign_id,
            "campaign_version": definition.campaign_version,
            "control_ref": control.control_ref,
            "control_action": control.control_action,
            "submitter_actor_id_present": control.submitter_actor_id is not None,
            "reviewer_actor_id_present": control.reviewer_actor_id is not None,
            "required_reviewer_role": control.required_reviewer_role,
            "correlation_id": control.correlation_id,
            "forbidden_actions": control.forbidden_actions,
            "trade_approval_claimed": False,
            "external_workflow_orchestration_claimed": False,
            "client_contact_claimed": False,
            "external_execution_claimed": False,
        },
    )


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


def _pm_quality_score_run_event(
    score_run: DpmPmOperatingQualityScoreRun,
) -> DpmPortfolioMemoryEvent:
    source_refs = sorted(
        [_from_outcome_source_ref(ref) for ref in score_run.source_refs],
        key=lambda ref: (ref.source_system, ref.source_type, ref.source_id),
    )
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:pm_quality:{score_run.score_run_id}",
        event_type="PM_QUALITY_SCORE_RUN",
        event_time=score_run.generated_at.isoformat(),
        actor=score_run.generated_by,
        source_system="lotus-manage",
        source_type="DPM_PM_OPERATING_QUALITY_SCORE_RUN",
        source_id=score_run.score_run_id,
        status=score_run.state,
        supportability_state=_state(score_run.state),
        summary=(
            f"PM operating quality score run {score_run.score_run_id} is available for "
            f"PM {score_run.pm_id} under policy {score_run.policy_id}:{score_run.policy_version}."
        ),
        reason_codes=score_run.reason_codes,
        source_refs=source_refs,
        artifact_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="PmOperatingQualityScoreRun",
                source_id=score_run.score_run_id,
                source_version=score_run.product_version,
                content_hash=score_run.content_hash,
            )
        ],
        content_hash=score_run.content_hash,
        metadata={
            "pm_id": score_run.pm_id,
            "book_id": score_run.book_id,
            "as_of_date": score_run.as_of_date,
            "policy_id": score_run.policy_id,
            "policy_version": score_run.policy_version,
            "score_state": score_run.state,
            "indicator_count": len(score_run.indicator_results),
            "numeric_score_projected": False,
            "portfolio_scope_source": "PortfolioManagerBookMembership:v1",
            "forbidden_uses": score_run.forbidden_uses,
        },
    )


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


def _pm_quality_review_action_event(
    *,
    action: DpmPmQualityReviewAction,
    score_run: DpmPmOperatingQualityScoreRun,
) -> DpmPortfolioMemoryEvent:
    source_refs = sorted(
        [_from_outcome_source_ref(ref) for ref in action.source_refs],
        key=lambda ref: (ref.source_system, ref.source_type, ref.source_id),
    )
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:pm_quality_review_action:{action.review_action_id}",
        event_type="PM_QUALITY_REVIEW_ACTION",
        event_time=action.generated_at.isoformat(),
        actor=action.actor_id,
        source_system="lotus-manage",
        source_type="DPM_PM_OPERATING_QUALITY_REVIEW_ACTION",
        source_id=action.review_action_id,
        status=action.action_state,
        supportability_state=_pm_quality_review_action_state(action),
        summary=(
            f"PM operating quality review action {action.action_type} recorded for "
            f"{action.target_type} {action.target_id}."
        ),
        reason_codes=sorted({*action.reason_codes, action.action_type, action.action_state}),
        source_refs=source_refs,
        artifact_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="PmOperatingQualityReviewAction",
                source_id=action.review_action_id,
                source_version=action.product_version,
                content_hash=action.content_hash,
            ),
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="PmOperatingQualityScoreRun",
                source_id=score_run.score_run_id,
                source_version=score_run.product_version,
                content_hash=score_run.content_hash,
            ),
        ],
        content_hash=action.content_hash,
        metadata={
            "review_action_ref": action.review_action_ref,
            "target_type": action.target_type,
            "target_id": action.target_id,
            "target_content_hash": action.target_content_hash,
            "target_state": action.target_state,
            "policy_id": action.policy_id,
            "policy_version": action.policy_version,
            "as_of_date": action.as_of_date,
            "action_type": action.action_type,
            "action_state": action.action_state,
            "remediation_due_date": action.remediation_due_date,
            "correlation_id": action.correlation_id,
            "review_reason_projected": False,
            "numeric_score_projected": False,
            "score_recalculated": False,
            "fairness_recomputed": False,
            "pm_ranking_created": False,
            "client_contact_claimed": False,
            "trade_approval_claimed": False,
            "external_execution_claimed": False,
            "forbidden_uses": action.forbidden_uses,
            "operating_boundaries": action.operating_boundaries,
        },
    )


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


def _pm_quality_summary_invocation_event(
    *,
    invocation: DpmPmQualitySummaryInvocation,
    score_run: DpmPmOperatingQualityScoreRun,
) -> DpmPortfolioMemoryEvent:
    source_refs = sorted(
        [_from_outcome_source_ref(ref) for ref in invocation.source_refs],
        key=lambda ref: (ref.source_system, ref.source_type, ref.source_id),
    )
    artifact_refs = [
        DpmPortfolioMemorySourceRef(
            source_system="lotus-manage",
            source_type="PmOperatingQualitySummaryInvocation",
            source_id=invocation.summary_invocation_id,
            source_version=invocation.product_version,
            content_hash=invocation.content_hash,
        ),
        DpmPortfolioMemorySourceRef(
            source_system="lotus-manage",
            source_type="PmOperatingQualityScoreRun",
            source_id=score_run.score_run_id,
            source_version=score_run.product_version,
            content_hash=score_run.content_hash,
        ),
        DpmPortfolioMemorySourceRef(
            source_system="lotus-manage",
            source_type="PmOperatingQualityReviewAction",
            source_id=invocation.review_action_id,
            source_version="v1",
            content_hash=invocation.review_action_content_hash,
        ),
    ]
    if invocation.summary_artifact_ref is not None or invocation.summary_content_hash is not None:
        artifact_refs.append(
            DpmPortfolioMemorySourceRef(
                source_system="lotus-ai",
                source_type=invocation.workflow_pack_name,
                source_id=(
                    invocation.summary_artifact_ref
                    or invocation.workflow_run_id
                    or invocation.summary_invocation_id
                ),
                source_version=invocation.workflow_pack_version,
                content_hash=invocation.summary_content_hash,
            )
        )
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:pm_quality_summary_invocation:{invocation.summary_invocation_id}",
        event_type="PM_QUALITY_SUMMARY_INVOCATION",
        event_time=invocation.generated_at.isoformat(),
        actor=invocation.requested_by,
        source_system="lotus-manage",
        source_type="DPM_PM_OPERATING_QUALITY_SUMMARY_INVOCATION",
        source_id=invocation.summary_invocation_id,
        status=invocation.invocation_state,
        supportability_state=_pm_quality_summary_invocation_state(invocation),
        summary=(
            "PM operating quality summary invocation history recorded for score run "
            f"{invocation.score_run_id} and review action {invocation.review_action_id}."
        ),
        reason_codes=sorted({*invocation.reason_codes, invocation.invocation_state}),
        source_refs=source_refs,
        artifact_refs=artifact_refs,
        content_hash=invocation.content_hash,
        metadata={
            "summary_ref": invocation.summary_ref,
            "score_run_id": invocation.score_run_id,
            "score_run_content_hash": invocation.score_run_content_hash,
            "review_action_id": invocation.review_action_id,
            "review_action_content_hash": invocation.review_action_content_hash,
            "policy_id": invocation.policy_id,
            "policy_version": invocation.policy_version,
            "as_of_date": invocation.as_of_date,
            "invocation_state": invocation.invocation_state,
            "workflow_pack_name": invocation.workflow_pack_name,
            "workflow_pack_version": invocation.workflow_pack_version,
            "workflow_run_id": invocation.workflow_run_id,
            "summary_artifact_ref": invocation.summary_artifact_ref,
            "summary_content_hash": invocation.summary_content_hash,
            "correlation_id": invocation.correlation_id,
            "summary_text_stored": False,
            "summary_text_exposed": False,
            "summary_text_projected": False,
            "downstream_summary_ux_projected": False,
            "prompt_reconstructed": False,
            "model_response_reconstructed": False,
            "review_reason_projected": False,
            "numeric_score_projected": False,
            "score_recalculated": False,
            "fairness_recomputed": False,
            "pm_ranking_created": False,
            "client_contact_claimed": False,
            "trade_approval_claimed": False,
            "external_execution_claimed": False,
            "summary_text_boundary_id": invocation.summary_text_boundary.boundary_id,
            "summary_text_boundary_content_hash": invocation.summary_text_boundary.content_hash,
            "forbidden_uses": invocation.forbidden_uses,
            "operating_boundaries": invocation.operating_boundaries,
        },
    )


def _waves_for_portfolio(
    *,
    portfolio_id: str,
    wave_repository: DpmWaveRepository,
    limit: int,
) -> list[DpmRebalanceWave]:
    waves = wave_repository.list_waves(limit=limit)
    return [wave for wave in waves if any(item.portfolio_id == portfolio_id for item in wave.items)]
