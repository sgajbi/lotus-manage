"""Source-backed portfolio memory read-model assembly."""

from datetime import datetime, timezone
from typing import Iterable

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.construction.models import (
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
)
from src.core.construction.repository import ConstructionRepository
from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import (
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
    DpmSourceProductLineage,
)
from src.core.outcomes.models import DpmOutcomeEvent, DpmOutcomeSourceRef, DpmPostTradeOutcomeReview
from src.core.pm_quality.models import DpmPmOperatingQualityScoreRun
from src.core.pm_quality.repository import DpmPmQualityScoreRunRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.portfolio_memory.models import (
    DpmPortfolioMemory,
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemoryExternalExecutionBoundaryEvidence,
    DpmPortfolioMemorySearchItem,
    DpmPortfolioMemorySearchPage,
    DpmPortfolioMemorySourceEventFamilyPosture,
    DpmPortfolioMemorySourceRef,
    PORTFOLIO_MEMORY_ACCESS_CLASSIFICATION,
    PORTFOLIO_MEMORY_AUDIT_POLICY,
    PORTFOLIO_MEMORY_EVENT_IDENTITY_SCHEME,
    PORTFOLIO_MEMORY_REDACTION_POLICY,
    PORTFOLIO_MEMORY_RETENTION_POLICY,
    PORTFOLIO_MEMORY_SOURCE_AUTHORITY_POLICY,
    PortfolioMemorySupportabilityState,
)
from src.core.proof_packs.models import (
    DpmPreTradeProofPack,
    DpmProofPackEvidenceRef,
    DpmProofPackSourceRef,
)
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves.models import (
    DpmRebalanceWave,
    DpmRebalanceWaveEvent,
    DpmRebalanceWaveItem,
    DpmWaveHandoffRef,
    DpmWaveSourceRef,
)
from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionAssignmentAction,
    DpmBulkReviewCampaignDefinitionAssignmentTask,
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

    events = _dedupe_and_sort(events)[:limit]
    event_type_counts = _counts(event.event_type for event in events)
    reason_codes = sorted({reason for event in events for reason in event.reason_codes})
    source_systems = sorted(
        {
            source_system
            for event in events
            for source_system in [
                event.source_system,
                *(ref.source_system for ref in event.source_refs),
            ]
            if source_system
        }
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
        events=events,
        content_hash="",
        generated_at=generated_at.isoformat(),
    )
    payload = memory.model_dump(mode="json")
    payload["content_hash"] = hash_canonical_payload(strip_keys(payload, exclude={"content_hash"}))
    return DpmPortfolioMemory.model_validate(payload)


def search_portfolio_memory(
    *,
    proof_pack_repository: DpmProofPackRepository,
    wave_repository: DpmWaveRepository,
    outcome_review_repository: DpmOutcomeReviewRepository,
    mandate_repository: DpmMandateRepository | None = None,
    construction_repository: ConstructionRepository | None = None,
    pm_quality_score_run_repository: DpmPmQualityScoreRunRepository | None = None,
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository | None = None,
    portfolio_ids: list[str] | None = None,
    event_type: str | None = None,
    supportability_state: PortfolioMemorySupportabilityState | None = None,
    source_system: str | None = None,
    limit: int = 50,
    offset: int = 0,
    source_scan_limit: int = 500,
    generated_at: datetime | None = None,
) -> DpmPortfolioMemorySearchPage:
    """Build a bounded Manage-local index over persisted portfolio-memory evidence."""

    generated_at = generated_at or datetime.now(timezone.utc)
    candidate_ids = _memory_candidate_portfolio_ids(
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
        campaign_definition_repository=campaign_definition_repository,
        portfolio_ids=portfolio_ids,
        source_scan_limit=source_scan_limit,
    )
    items: list[DpmPortfolioMemorySearchItem] = []
    for portfolio_id in candidate_ids:
        memory = build_portfolio_memory(
            portfolio_id=portfolio_id,
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=outcome_review_repository,
            mandate_repository=mandate_repository,
            construction_repository=construction_repository,
            pm_quality_score_run_repository=pm_quality_score_run_repository,
            campaign_definition_repository=campaign_definition_repository,
            limit=source_scan_limit,
            generated_at=generated_at,
        )
        if memory.event_count == 0:
            continue
        if event_type is not None and event_type not in memory.event_type_counts:
            continue
        if supportability_state is not None and memory.supportability_state != supportability_state:
            continue
        if source_system is not None and source_system not in memory.source_systems:
            continue
        latest_event = memory.events[0] if memory.events else None
        items.append(
            DpmPortfolioMemorySearchItem(
                portfolio_id=memory.portfolio_id,
                event_count=memory.event_count,
                supportability_state=memory.supportability_state,
                event_type_counts=memory.event_type_counts,
                source_systems=memory.source_systems,
                reason_codes=memory.reason_codes,
                latest_event_time=latest_event.event_time if latest_event else None,
                latest_event_type=latest_event.event_type if latest_event else None,
                content_hash=memory.content_hash,
            )
        )

    items = sorted(
        items,
        key=lambda item: (item.latest_event_time or "", item.portfolio_id),
        reverse=True,
    )
    total_count = len(items)
    page = items[offset : offset + limit]
    return DpmPortfolioMemorySearchPage(
        items=page,
        limit=limit,
        offset=offset,
        returned_count=len(page),
        total_count=total_count,
        scanned_portfolio_count=len(candidate_ids),
        generated_at=generated_at.isoformat(),
        support_boundary=(
            "Manage-local memory search indexes persisted Manage evidence and explicit "
            "caller-supplied portfolio identifiers only; it does not discover the global "
            "portfolio universe, query external source-owner event stores, project OMS "
            "acknowledgement/fill/settlement events, or recalculate source truth."
        ),
    )


def _memory_candidate_portfolio_ids(
    *,
    proof_pack_repository: DpmProofPackRepository,
    wave_repository: DpmWaveRepository,
    outcome_review_repository: DpmOutcomeReviewRepository,
    mandate_repository: DpmMandateRepository | None,
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository | None,
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
    return sorted(candidates)


def _portfolio_memory_governance_policy() -> dict[str, str]:
    return {
        "event_identity_scheme": PORTFOLIO_MEMORY_EVENT_IDENTITY_SCHEME,
        "retention_policy": PORTFOLIO_MEMORY_RETENTION_POLICY,
        "redaction_policy": PORTFOLIO_MEMORY_REDACTION_POLICY,
        "audit_policy": PORTFOLIO_MEMORY_AUDIT_POLICY,
        "access_classification": PORTFOLIO_MEMORY_ACCESS_CLASSIFICATION,
        "source_authority_policy": PORTFOLIO_MEMORY_SOURCE_AUTHORITY_POLICY,
    }


def _external_execution_boundary_evidence() -> DpmPortfolioMemoryExternalExecutionBoundaryEvidence:
    payload = {
        "boundary_id": "DPM_PORTFOLIO_MEMORY_EXTERNAL_EXECUTION_BOUNDARY",
        "supportability_state": "BLOCKED",
        "source_system": "lotus-manage",
        "source_product_name": "DpmPortfolioMemory",
        "source_product_version": "v1",
        "external_execution_events_projected": False,
        "external_acknowledgement_events_projected": False,
        "reason_code": "PORTFOLIO_MEMORY_EXTERNAL_EXECUTION_EVENTS_NOT_SUPPORTED",
        "blocked_capabilities": [
            "order_generation",
            "venue_routing",
            "best_execution",
            "oms_acknowledgement",
            "fills",
            "settlement",
            "execution_status_projection",
        ],
        "required_owner": "future execution/OMS owner",
        "required_source_product": "ExternalOrderExecutionAcknowledgement:v1",
        "summary": (
            "Portfolio memory preserves source-backed Manage, report, AI, archive, and PM-quality "
            "lineage only; external execution, OMS acknowledgement, fill, settlement, and "
            "execution-status events remain blocked until a certified bank-owned OMS source-event "
            "family is published."
        ),
    }
    payload["content_hash"] = hash_canonical_payload(payload)
    return DpmPortfolioMemoryExternalExecutionBoundaryEvidence.model_validate(payload)


def _source_event_family_posture() -> list[DpmPortfolioMemorySourceEventFamilyPosture]:
    return [
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="mandate_health",
            source_system="lotus-manage",
            owner="lotus-manage",
            support_status="SUPPORTED",
            event_types=["MANDATE_HEALTH_SNAPSHOT"],
            route="/api/v1/rebalance/portfolio-memory/{portfolio_id}",
            reason_code="MANDATE_HEALTH_SOURCE_EVENTS_SUPPORTED",
            summary="Mandate health snapshots are projected from persisted mandate repository truth.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="mandate_monitoring_exception",
            source_system="lotus-manage",
            owner="lotus-manage",
            support_status="SUPPORTED",
            event_types=["MANDATE_MONITORING_EXCEPTION"],
            route="/api/v1/rebalance/portfolio-memory/{portfolio_id}",
            reason_code="MANDATE_MONITORING_SOURCE_EVENTS_SUPPORTED",
            summary="Mandate monitoring exceptions are projected from persisted exception truth.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="proof_pack_decision_timeline",
            source_system="lotus-manage",
            owner="lotus-manage",
            support_status="SUPPORTED",
            event_types=["PROOF_PACK_CREATED", "PROOF_PACK_TIMELINE_EVENT"],
            route="/api/v1/rebalance/portfolio-memory/{portfolio_id}",
            reason_code="PROOF_PACK_SOURCE_EVENTS_SUPPORTED",
            summary="Proof-pack creation and proof-pack-local decision timeline events are projected.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="construction_alternatives",
            source_system="lotus-manage",
            owner="lotus-manage construction alternatives product",
            support_status="SUPPORTED",
            event_types=["CONSTRUCTION_ALTERNATIVE_SET", "CONSTRUCTION_ALTERNATIVE_SELECTED"],
            route="/api/v1/rebalance/portfolio-memory/{portfolio_id}",
            reason_code="CONSTRUCTION_ALTERNATIVE_SOURCE_EVENTS_SUPPORTED",
            summary=(
                "Construction alternative set generation and selected-alternative decisions are "
                "projected from persisted construction repository truth without copying raw "
                "request payloads or recalculating construction, risk, performance, tax, cash, "
                "FX, or execution methodology."
            ),
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="rebalance_wave",
            source_system="lotus-manage",
            owner="lotus-manage",
            support_status="SUPPORTED",
            event_types=["WAVE_CREATED", "WAVE_EVENT", "WAVE_HANDOFF_READY"],
            route="/api/v1/rebalance/portfolio-memory/{portfolio_id}",
            reason_code="REBALANCE_WAVE_SOURCE_EVENTS_SUPPORTED",
            summary="Rebalance wave lifecycle and internal handoff events are projected.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="bulk_review_campaign_workflow",
            source_system="lotus-manage",
            owner="lotus-manage campaign definition product",
            support_status="SUPPORTED",
            event_types=[
                "BULK_REVIEW_CAMPAIGN_DEFINITION",
                "BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION",
                "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION",
                "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK",
                "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL",
            ],
            route="/api/v1/rebalance/portfolio-memory/{portfolio_id}",
            reason_code="BULK_REVIEW_CAMPAIGN_WORKFLOW_SOURCE_EVENTS_SUPPORTED",
            summary=(
                "Bulk-review campaign definitions and Manage-side approval, assignment, task, "
                "and maker-checker evidence are projected from persisted campaign truth without "
                "discovering the global portfolio universe, recalculating membership, "
                "or orchestrating external workflow, client-contact, order, or OMS actions."
            ),
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="post_trade_outcome_review",
            source_system="lotus-manage",
            owner="lotus-manage",
            support_status="SUPPORTED",
            event_types=["OUTCOME_REVIEW_CREATED", "OUTCOME_REVIEW_EVENT"],
            route="/api/v1/rebalance/portfolio-memory/{portfolio_id}",
            reason_code="OUTCOME_REVIEW_SOURCE_EVENTS_SUPPORTED",
            summary="Post-trade outcome-review creation and review events are projected.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="report_lifecycle",
            source_system="lotus-report",
            owner="lotus-report",
            support_status="SUPPORTED",
            event_types=[
                "REPORT_JOB_CREATED",
                "REPORT_SNAPSHOT_CAPTURED",
                "REPORT_RENDERED",
                "REPORT_ARCHIVED",
            ],
            route="/reports/jobs/{job_id}/portfolio-memory-events",
            reason_code="REPORT_SOURCE_EVENTS_SUPPORTED",
            summary="Report lifecycle, snapshot, render, and archive lineage are source-owned by report.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="ai_workflow_pack",
            source_system="lotus-ai",
            owner="lotus-ai",
            support_status="SUPPORTED",
            event_types=[
                "AI_WORKFLOW_PACK_RUN",
                "AI_WORKFLOW_PACK_REVIEW",
                "AI_WORKFLOW_PACK_LINEAGE",
            ],
            route="/platform/workflow-packs/source-events",
            reason_code="AI_WORKFLOW_PACK_SOURCE_EVENTS_SUPPORTED",
            summary="AI workflow-pack run, review, and lineage posture are source-owned by AI.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="generated_document_archive",
            source_system="lotus-archive",
            owner="lotus-archive",
            support_status="SUPPORTED",
            event_types=[
                "GENERATED_DOCUMENT_ARCHIVED",
                "GENERATED_DOCUMENT_SUPERSEDED",
                "GENERATED_DOCUMENT_CORRECTED",
                "CLIENT_DELIVERY_REISSUED",
            ],
            route="/documents/{document_id}/source-events",
            reason_code="GENERATED_DOCUMENT_SOURCE_EVENTS_SUPPORTED",
            summary="Generated-document archive and client-delivery lineage are source-owned by archive.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="external_oms_execution",
            source_system="future-oms-owner",
            owner="future execution or OMS owner",
            support_status="DEFERRED_SOURCE_OWNER",
            event_types=[],
            route=None,
            reason_code="OMS_SOURCE_EVENTS_NOT_SUPPORTED",
            summary=(
                "No external OMS execution, fill, or acknowledgement events are projected until a "
                "governed OMS owner publishes a no-raw-payload source-event family."
            ),
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="external_order_execution_acknowledgement",
            source_system="lotus-core",
            owner="lotus-core source-boundary posture; future execution or OMS owner",
            support_status="DEFERRED_SOURCE_OWNER",
            event_types=[],
            route="/integration/portfolios/{portfolio_id}/external-order-execution-acknowledgement",
            reason_code="EXTERNAL_ORDER_ACKNOWLEDGEMENT_SOURCE_EVENTS_DEFERRED",
            summary=(
                "Core ExternalOrderExecutionAcknowledgement:v1 is consumed only as fail-closed "
                "source-product posture for construction and outcome evidence; portfolio memory "
                "does not project acknowledgement, fill, settlement, or execution-status events "
                "until bank-owned OMS acknowledgement ingestion publishes a certified "
                "no-raw-payload source-event family."
            ),
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="pm_scoring",
            source_system="lotus-manage",
            owner="lotus-manage PM operating quality product",
            support_status="SUPPORTED",
            event_types=["PM_QUALITY_SCORE_RUN"],
            route="/api/v1/rebalance/pm-operating-quality/score-runs",
            reason_code="PM_QUALITY_SCORE_RUN_SOURCE_EVENTS_SUPPORTED",
            summary=(
                "Persisted PM operating quality score runs are supported as a separate explicit "
                "Manage product with bank-supplied policy and source-backed evidence; portfolio "
                "memory projects only source-backed score-run lineage for portfolios included in "
                "Core PM-book membership evidence and does not copy raw score payloads or create "
                "portfolio-level rankings."
            ),
        ),
    ]


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


def _construction_alternative_set_event(
    alternative_set: ConstructionAlternativeSet,
) -> DpmPortfolioMemoryEvent:
    method_counts = _counts(
        alternative.method.value for alternative in alternative_set.alternatives
    )
    reason_codes = sorted(
        {
            "CONSTRUCTION_ALTERNATIVE_SET_READY",
            alternative_set.status.value,
            *(
                alternative.method_status.value
                for alternative in alternative_set.alternatives
                if alternative.method_status.value != alternative_set.status.value
            ),
        }
    )
    content_hash = _construction_alternative_set_content_hash(alternative_set)
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:construction:{alternative_set.alternative_set_id}:generated",
        event_type="CONSTRUCTION_ALTERNATIVE_SET",
        event_time=alternative_set.generated_at.isoformat(),
        actor="lotus-manage",
        source_system="lotus-manage",
        source_type="DPM_CONSTRUCTION_ALTERNATIVE_SET",
        source_id=alternative_set.alternative_set_id,
        status=alternative_set.status.value,
        supportability_state=_state(alternative_set.status.value),
        summary=(
            f"Construction alternative set {alternative_set.alternative_set_id} generated "
            f"with {len(alternative_set.alternatives)} alternatives."
        ),
        reason_codes=reason_codes,
        artifact_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="DPM_CONSTRUCTION_ALTERNATIVE_SET",
                source_id=alternative_set.alternative_set_id,
                content_hash=content_hash,
            )
        ],
        content_hash=content_hash,
        metadata={
            "as_of": alternative_set.as_of,
            "alternative_count": len(alternative_set.alternatives),
            "method_counts": method_counts,
            "input_mode": alternative_set.input_mode,
            "source_supportability_state": alternative_set.source_supportability_state,
            "request_hash_available": alternative_set.request_hash is not None,
            "raw_request_payload_projected": False,
        },
    )


def _construction_selection_event(
    *,
    alternative_set: ConstructionAlternativeSet,
    selection: ConstructionAlternativeSelection,
) -> DpmPortfolioMemoryEvent:
    selected_alternative = next(
        (
            alternative
            for alternative in alternative_set.alternatives
            if alternative.alternative_id == selection.alternative_id
        ),
        None,
    )
    content_hash = hash_canonical_payload(selection.model_dump(mode="json"))
    alternative_set_content_hash = _construction_alternative_set_content_hash(alternative_set)
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:construction:{alternative_set.alternative_set_id}:selection:{selection.selection_id}",
        event_type="CONSTRUCTION_ALTERNATIVE_SELECTED",
        event_time=selection.selected_at.isoformat(),
        actor=selection.actor_id,
        source_system="lotus-manage",
        source_type="DPM_CONSTRUCTION_ALTERNATIVE_SELECTION",
        source_id=selection.selection_id,
        status="SELECTED",
        supportability_state="READY",
        summary=(
            f"Construction alternative {selection.alternative_id} selected from "
            f"{alternative_set.alternative_set_id}."
        ),
        reason_codes=[selection.reason_code],
        artifact_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="DPM_CONSTRUCTION_ALTERNATIVE_SET",
                source_id=alternative_set.alternative_set_id,
                content_hash=alternative_set_content_hash,
            ),
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="DPM_CONSTRUCTION_ALTERNATIVE_SELECTION",
                source_id=selection.selection_id,
                content_hash=content_hash,
            ),
        ],
        content_hash=content_hash,
        metadata={
            "alternative_set_id": alternative_set.alternative_set_id,
            "alternative_id": selection.alternative_id,
            "selected_method": selected_alternative.method.value
            if selected_alternative is not None
            else None,
            "selected_method_status": selected_alternative.method_status.value
            if selected_alternative is not None
            else None,
            "correlation_id": selection.correlation_id,
            "comment_projected": selection.comment is not None,
            "raw_selection_payload_projected": False,
        },
    )


def _construction_alternative_set_content_hash(
    alternative_set: ConstructionAlternativeSet,
) -> str:
    return alternative_set.request_hash or hash_canonical_payload(
        alternative_set.model_dump(mode="json")
    )


def _proof_pack_events(proof_pack: DpmPreTradeProofPack) -> list[DpmPortfolioMemoryEvent]:
    refs = _proof_pack_source_refs(proof_pack)
    events = [
        DpmPortfolioMemoryEvent(
            event_id=f"memory:proof_pack:{proof_pack.proof_pack_id}:created",
            event_type="PROOF_PACK_CREATED",
            event_time=proof_pack.created_at.isoformat(),
            actor=proof_pack.created_by,
            source_system="lotus-manage",
            source_type="DPM_PRE_TRADE_PROOF_PACK",
            source_id=proof_pack.proof_pack_id,
            status=proof_pack.status,
            supportability_state=_state(proof_pack.status),
            summary=f"Proof pack {proof_pack.proof_pack_id} created from {proof_pack.source_type}.",
            reason_codes=proof_pack.supportability.reason_codes,
            source_refs=refs,
            artifact_refs=_proof_pack_artifact_refs(proof_pack),
            content_hash=proof_pack.content_hash,
            metadata={
                "mandate_id": proof_pack.mandate_id,
                "rebalance_run_id": proof_pack.rebalance_run_id,
                "alternative_set_id": proof_pack.alternative_set_id,
                "selected_alternative_id": proof_pack.selected_alternative_id,
                "as_of_date": proof_pack.as_of_date,
            },
        )
    ]
    for timeline_event in proof_pack.decision_timeline.events:
        events.append(
            DpmPortfolioMemoryEvent(
                event_id=(
                    f"memory:proof_pack:{proof_pack.proof_pack_id}:"
                    f"timeline:{timeline_event.event_id}"
                ),
                event_type="PROOF_PACK_TIMELINE_EVENT",
                event_time=timeline_event.event_time,
                actor=timeline_event.actor,
                source_system=timeline_event.source_system,
                source_type=timeline_event.event_type,
                source_id=timeline_event.event_id,
                status=timeline_event.status,
                supportability_state=_state(timeline_event.status),
                summary=f"Proof-pack timeline event {timeline_event.event_type}.",
                reason_codes=timeline_event.reason_codes,
                source_refs=refs,
                artifact_refs=[
                    _from_proof_pack_evidence_ref(ref) for ref in timeline_event.artifact_refs
                ],
                content_hash=proof_pack.content_hash,
                metadata={"proof_pack_id": proof_pack.proof_pack_id},
            )
        )
    return events


def _wave_events(*, wave: DpmRebalanceWave, portfolio_id: str) -> list[DpmPortfolioMemoryEvent]:
    matching_items = [item for item in wave.items if item.portfolio_id == portfolio_id]
    item_ids = {item.wave_item_id for item in matching_items}
    refs = _wave_source_refs(wave=wave, items=matching_items)
    events = [
        DpmPortfolioMemoryEvent(
            event_id=f"memory:wave:{wave.wave_id}:created",
            event_type="WAVE_CREATED",
            event_time=wave.created_at.isoformat(),
            actor=wave.created_by,
            source_system="lotus-manage",
            source_type="DPM_REBALANCE_WAVE",
            source_id=wave.wave_id,
            status=wave.state,
            supportability_state=_state(wave.state),
            summary=f"Rebalance wave {wave.wave_id} created for trigger {wave.trigger.trigger_type}.",
            reason_codes=sorted(
                {reason for item in matching_items for reason in item.reason_codes}
            ),
            source_refs=refs,
            content_hash=None,
            metadata={
                "trigger_type": wave.trigger.trigger_type,
                "trigger_id": wave.trigger.trigger_id,
                "as_of_date": wave.as_of_date,
                "matching_item_count": len(matching_items),
            },
        )
    ]
    events.extend(_wave_state_events(wave=wave, refs=refs))
    for handoff in wave.handoff_refs:
        if item_ids and not item_ids.intersection(handoff.item_ids):
            continue
        events.append(_handoff_event(wave=wave, handoff=handoff, refs=refs))
    return events


def _wave_state_events(
    *,
    wave: DpmRebalanceWave,
    refs: list[DpmPortfolioMemorySourceRef],
) -> list[DpmPortfolioMemoryEvent]:
    return [
        DpmPortfolioMemoryEvent(
            event_id=f"memory:wave:{wave.wave_id}:event:{event.event_id}",
            event_type="WAVE_EVENT",
            event_time=event.created_at.isoformat(),
            actor=event.actor_id,
            source_system="lotus-manage",
            source_type=event.event_type,
            source_id=event.event_id,
            status=event.to_state,
            supportability_state=_state(event.to_state),
            summary=f"Wave event {event.event_type} moved wave to {event.to_state}.",
            reason_codes=[event.reason_code],
            source_refs=refs,
            content_hash=None,
            metadata=_wave_event_metadata(event),
        )
        for event in wave.events
    ]


def _handoff_event(
    *,
    wave: DpmRebalanceWave,
    handoff: DpmWaveHandoffRef,
    refs: list[DpmPortfolioMemorySourceRef],
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:wave:{wave.wave_id}:handoff:{handoff.handoff_ref_id}",
        event_type="WAVE_HANDOFF_READY",
        event_time=handoff.created_at.isoformat(),
        actor=handoff.actor_id,
        source_system="lotus-manage",
        source_type="DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF",
        source_id=handoff.handoff_ref_id,
        status=wave.state,
        supportability_state=_state(wave.state),
        summary="Internal operations handoff evidence recorded without external execution claim.",
        reason_codes=[handoff.reason_code],
        source_refs=refs,
        artifact_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF",
                source_id=handoff.handoff_ref_id,
                content_hash=handoff.content_hash,
            )
        ],
        content_hash=handoff.content_hash,
        metadata={
            "wave_id": wave.wave_id,
            "item_count": len(handoff.item_ids),
            "external_execution_claimed": handoff.external_execution_claimed,
        },
    )


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


def _outcome_review_events(
    *,
    review: DpmPostTradeOutcomeReview,
    persisted_events: list[DpmOutcomeEvent],
) -> list[DpmPortfolioMemoryEvent]:
    events_by_id = {event.event_id: event for event in [*review.events, *persisted_events]}
    events = [
        DpmPortfolioMemoryEvent(
            event_id=f"memory:outcome:{review.outcome_review_id}:created",
            event_type="OUTCOME_REVIEW_CREATED",
            event_time=review.created_at.isoformat(),
            actor=review.created_by,
            source_system="lotus-manage",
            source_type="DPM_POST_TRADE_OUTCOME_REVIEW",
            source_id=review.outcome_review_id,
            status=review.state,
            supportability_state=_state(review.state),
            summary=f"Outcome review {review.outcome_review_id} created with {review.overall_outcome}.",
            reason_codes=review.supportability.reason_codes,
            source_refs=[_from_outcome_source_ref(ref) for ref in review.source_lineage],
            content_hash=review.content_hash,
            metadata={
                "proof_pack_id": review.proof_pack_id,
                "wave_id": review.wave_id,
                "wave_item_id": review.wave_item_id,
                "operations_handoff_ref_id": review.operations_handoff_ref_id,
            },
        )
    ]
    for event in events_by_id.values():
        events.append(
            DpmPortfolioMemoryEvent(
                event_id=f"memory:outcome:{review.outcome_review_id}:event:{event.event_id}",
                event_type="OUTCOME_REVIEW_EVENT",
                event_time=event.event_time,
                actor=event.actor,
                source_system="lotus-manage",
                source_type=event.event_type,
                source_id=event.event_id,
                status=event.state,
                supportability_state=_state(event.state),
                summary=f"Outcome-review event {event.event_type}.",
                reason_codes=event.reason_codes,
                source_refs=[_from_outcome_source_ref(ref) for ref in event.source_refs],
                content_hash=review.content_hash,
                metadata={"outcome_review_id": review.outcome_review_id},
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


def _score_run_includes_portfolio(
    *,
    score_run: DpmPmOperatingQualityScoreRun,
    portfolio_id: str,
) -> bool:
    if score_run.book_scope_evidence is None:
        return False
    if portfolio_id in score_run.book_scope_evidence.member_portfolio_ids:
        return True
    return any(
        ref.source_type == "PORTFOLIO_MANAGER_BOOK_MEMBER"
        and (ref.source_id == portfolio_id or ref.source_id.endswith(f":{portfolio_id}"))
        for ref in score_run.book_scope_evidence.source_refs
    )


def _waves_for_portfolio(
    *,
    portfolio_id: str,
    wave_repository: DpmWaveRepository,
    limit: int,
) -> list[DpmRebalanceWave]:
    waves = wave_repository.list_waves(limit=limit)
    return [wave for wave in waves if any(item.portfolio_id == portfolio_id for item in wave.items)]


def _dedupe_and_sort(
    events: Iterable[DpmPortfolioMemoryEvent],
) -> list[DpmPortfolioMemoryEvent]:
    unique = {event.event_id: event for event in events}
    return sorted(
        unique.values(), key=lambda event: (event.event_time, event.event_id), reverse=True
    )


def _memory_state(
    events: list[DpmPortfolioMemoryEvent],
) -> PortfolioMemorySupportabilityState:
    if not events:
        return "EMPTY"
    states = {event.supportability_state for event in events}
    for state in ("BLOCKED", "DEGRADED", "PENDING_REVIEW"):
        if state in states:
            return state
    return "READY"


def _state(source_state: str | None) -> PortfolioMemorySupportabilityState:
    normalized = (source_state or "").upper()
    if "BLOCK" in normalized or normalized in {"FAILED", "REJECTED", "CANCELLED"}:
        return "BLOCKED"
    if "DEGRADED" in normalized or "BREACHED" in normalized or "PARTIAL" in normalized:
        return "DEGRADED"
    if "REVIEW" in normalized or normalized in {"CREATED", "DRAFT", "PREVIEWED", "CANDIDATE"}:
        return "PENDING_REVIEW"
    return "READY"


def _counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _proof_pack_source_refs(proof_pack: DpmPreTradeProofPack) -> list[DpmPortfolioMemorySourceRef]:
    refs: dict[tuple[str, str, str], DpmPortfolioMemorySourceRef] = {}
    for section in proof_pack.sections:
        for ref in section.source_refs:
            memory_ref = _from_proof_pack_source_ref(ref)
            refs[(memory_ref.source_system, memory_ref.source_type, memory_ref.source_id)] = (
                memory_ref
            )
    return sorted(
        refs.values(), key=lambda ref: (ref.source_system, ref.source_type, ref.source_id)
    )


def _proof_pack_artifact_refs(
    proof_pack: DpmPreTradeProofPack,
) -> list[DpmPortfolioMemorySourceRef]:
    refs = [
        ref
        for ref in [
            proof_pack.markdown_summary_ref,
            proof_pack.report_input_ref,
            proof_pack.ai_evidence_ref,
        ]
        if ref is not None
    ]
    return [_from_proof_pack_evidence_ref(ref) for ref in refs]


def _wave_source_refs(
    *,
    wave: DpmRebalanceWave,
    items: list[DpmRebalanceWaveItem],
) -> list[DpmPortfolioMemorySourceRef]:
    refs = [_from_wave_source_ref(ref) for ref in wave.trigger.source_refs]
    for item in items:
        refs.extend(_from_wave_source_ref(ref) for ref in item.source_refs)
    return sorted(refs, key=lambda ref: (ref.source_system, ref.source_type, ref.source_id))


def _campaign_definition_source_refs(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    portfolio_id: str,
) -> list[DpmPortfolioMemorySourceRef]:
    refs = [_from_wave_source_ref(ref) for ref in definition.source_refs]
    if definition.governance is not None:
        refs.extend(_from_wave_source_ref(ref) for ref in definition.governance.source_refs)
    for candidate in definition.candidates:
        if candidate.portfolio_id == portfolio_id:
            refs.extend(_from_wave_source_ref(ref) for ref in candidate.source_refs)
    unique = {
        (ref.source_system, ref.source_type, ref.source_id, ref.source_version): ref for ref in refs
    }
    return sorted(
        unique.values(),
        key=lambda ref: (ref.source_system, ref.source_type, ref.source_id),
    )


def _campaign_definition_artifact_ref(
    definition: DpmBulkReviewCampaignDefinition,
) -> DpmPortfolioMemorySourceRef:
    return DpmPortfolioMemorySourceRef(
        source_system="lotus-manage",
        source_type="BulkReviewCampaignDefinition",
        source_id=f"{definition.campaign_id}:{definition.campaign_version}",
        source_version=definition.product_version,
        content_hash=definition.content_hash,
    )


def _from_proof_pack_source_ref(ref: DpmProofPackSourceRef) -> DpmPortfolioMemorySourceRef:
    return DpmPortfolioMemorySourceRef(
        source_system=ref.source_system,
        source_type=ref.source_type,
        source_id=ref.source_id,
        supportability_state=ref.supportability_state,
        content_hash=ref.content_hash,
    )


def _from_proof_pack_evidence_ref(ref: DpmProofPackEvidenceRef) -> DpmPortfolioMemorySourceRef:
    return DpmPortfolioMemorySourceRef(
        source_system=ref.source_system,
        source_type=ref.ref_type,
        source_id=ref.ref_id,
        content_hash=ref.content_hash,
    )


def _from_wave_source_ref(ref: DpmWaveSourceRef) -> DpmPortfolioMemorySourceRef:
    return DpmPortfolioMemorySourceRef(
        source_system=ref.source_system,
        source_type=ref.source_type,
        source_id=ref.source_id,
        source_version=ref.source_version,
        supportability_state=ref.supportability_state,
        content_hash=ref.content_hash,
    )


def _from_outcome_source_ref(ref: DpmOutcomeSourceRef) -> DpmPortfolioMemorySourceRef:
    return DpmPortfolioMemorySourceRef(
        source_system=ref.source_system,
        source_type=ref.source_type,
        source_id=ref.source_id,
        source_version=ref.source_version,
        content_hash=ref.content_hash,
    )


def _from_source_product_lineage(ref: DpmSourceProductLineage) -> DpmPortfolioMemorySourceRef:
    return DpmPortfolioMemorySourceRef(
        source_system=ref.source_system,
        source_type=ref.product_name,
        source_id=ref.source_record_id or ref.product_name,
        source_version=ref.product_version,
        supportability_state=ref.data_quality_status,
    )


def _monitoring_exception_state(
    exception: DpmMonitoringException,
) -> PortfolioMemorySupportabilityState:
    if exception.state == "RESOLVED":
        return "READY"
    if exception.severity.value == "CRITICAL":
        return "BLOCKED"
    if exception.severity.value == "WARNING":
        return "DEGRADED"
    return "PENDING_REVIEW"


def _assignment_sla_state(sla_posture: str) -> PortfolioMemorySupportabilityState:
    if sla_posture == "BREACHED_OR_BLOCKED":
        return "DEGRADED"
    return "READY"


def _assignment_task_state(
    status: str,
    sla_posture: str,
) -> PortfolioMemorySupportabilityState:
    if status == "CANCELLED":
        return "BLOCKED"
    if status == "BLOCKED" or sla_posture == "BREACHED_OR_BLOCKED":
        return "DEGRADED"
    if status in {"OPEN", "ACKNOWLEDGED", "IN_PROGRESS"}:
        return "PENDING_REVIEW"
    return "READY"


def _maker_checker_state(control_outcome: str) -> PortfolioMemorySupportabilityState:
    if control_outcome == "FAILED":
        return "BLOCKED"
    if control_outcome == "EXCEPTION_OPEN":
        return "DEGRADED"
    if control_outcome == "PENDING":
        return "PENDING_REVIEW"
    return "READY"


def _wave_event_metadata(event: DpmRebalanceWaveEvent) -> dict[str, object]:
    metadata = dict(event.metadata)
    metadata["from_state"] = event.from_state
    metadata["to_state"] = event.to_state
    metadata["correlation_id"] = event.correlation_id
    return metadata
