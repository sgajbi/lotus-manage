"""API routes for RFC-0040 portfolio memory."""

from typing import cast, get_args

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import (
    get_construction_repository,
    get_campaign_definition_repository,
    get_mandate_repository,
    get_outcome_review_repository,
    get_pm_quality_review_action_repository,
    get_pm_quality_score_run_repository,
    get_pm_quality_summary_invocation_repository,
    get_proof_pack_repository,
    get_wave_repository,
)
from src.core.construction.repository import ConstructionRepository
from src.core.mandate_repository import DpmMandateRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.pm_quality.repository import (
    DpmPmQualityReviewActionRepository,
    DpmPmQualityScoreRunRepository,
    DpmPmQualitySummaryInvocationRepository,
)
from src.core.portfolio_memory import DpmPortfolioMemory, DpmPortfolioMemorySearchPage
from src.core.portfolio_memory.models import (
    DpmPortfolioMemoryEventLookup,
    PortfolioMemoryEventType,
    PortfolioMemorySupportabilityState,
)
from src.core.portfolio_memory.service import (
    build_portfolio_memory_event_lookup,
    build_portfolio_memory,
    normalize_portfolio_memory_search_filter,
    search_portfolio_memory,
)
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves.campaign_repository import DpmBulkReviewCampaignDefinitionRepository
from src.core.waves.repository import DpmWaveRepository


router = APIRouter(
    prefix="/rebalance/portfolio-memory",
    tags=["lotus-manage Portfolio Memory"],
)
_PORTFOLIO_MEMORY_EVENT_TYPES = tuple(get_args(PortfolioMemoryEventType))
_PORTFOLIO_MEMORY_EVENT_TYPE_SET = set(_PORTFOLIO_MEMORY_EVENT_TYPES)


@router.get(
    "/search",
    response_model=DpmPortfolioMemorySearchPage,
    summary="Search Manage-local portfolio memory",
    description=(
        "What: Return a bounded search page of portfolio-memory summaries built from persisted "
        "Manage evidence and optional caller-supplied portfolio identifiers.\n"
        "When: Use when PM, CIO, operations, audit, Gateway, or Workbench consumers need to find "
        "portfolios with existing Manage memory evidence before loading a single portfolio "
        "timeline.\n"
        "How: The endpoint scans persisted proof packs, rebalance waves, monitoring exceptions, "
        "campaign definitions, and outcome reviews, then composes each matching portfolio with "
        "the same source-backed memory assembler used by the detail route. It can filter by "
        "event type, supportability state, represented source system, and represented source "
        "type. It does not discover the global portfolio universe, "
        "query external source-owner event stores, project OMS acknowledgement/fill/settlement "
        "events, project client contact/message/delivery/approval events, or recalculate risk, "
        "performance, execution, tax, cash, FX, mandate-health, PM-quality score/review-action, "
        "report, archive, or AI truth."
    ),
)
def search_portfolio_memory_index(
    portfolio_ids: list[str] | None = Query(
        default=None,
        description=(
            "Optional portfolio identifiers to include in addition to portfolios discovered from "
            "Manage-local persisted evidence. This is not a global portfolio-universe selector."
        ),
    ),
    event_type: str | None = Query(
        default=None,
        description=(
            "Optional portfolio-memory event type filter. Unsupported event types are rejected "
            "instead of being interpreted as an empty source result."
        ),
        examples=["WAVE_HANDOFF_READY"],
    ),
    supportability_state: str | None = Query(
        default=None,
        pattern=r"^\s*(READY|PENDING_REVIEW|DEGRADED|BLOCKED|EMPTY)\s*$",
        description=(
            "Optional aggregate supportability-state filter. Leading and trailing whitespace is "
            "normalized before matching."
        ),
        examples=["READY"],
    ),
    source_system: str | None = Query(
        default=None,
        description=(
            "Optional represented source-system filter. Leading and trailing whitespace is "
            "normalized before matching."
        ),
        examples=["lotus-manage"],
    ),
    source_type: str | None = Query(
        default=None,
        description=(
            "Optional represented source-type filter across matching events, source refs, and "
            "artifact refs. Leading and trailing whitespace is normalized before matching."
        ),
        examples=["DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF"],
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum summaries to return."),
    offset: int = Query(default=0, ge=0, description="Zero-based page offset."),
    source_scan_limit: int = Query(
        default=500,
        ge=1,
        le=1000,
        description="Maximum rows to scan from each Manage-local evidence repository.",
    ),
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    construction_repository: ConstructionRepository = Depends(get_construction_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    outcome_review_repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    pm_quality_score_run_repository: DpmPmQualityScoreRunRepository = Depends(
        get_pm_quality_score_run_repository
    ),
    pm_quality_review_action_repository: DpmPmQualityReviewActionRepository = Depends(
        get_pm_quality_review_action_repository
    ),
    pm_quality_summary_invocation_repository: DpmPmQualitySummaryInvocationRepository = Depends(
        get_pm_quality_summary_invocation_repository
    ),
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmPortfolioMemorySearchPage:
    normalized_event_type = normalize_portfolio_memory_search_filter(event_type)
    normalized_supportability_state = normalize_portfolio_memory_search_filter(supportability_state)
    normalized_source_system = normalize_portfolio_memory_search_filter(source_system)
    normalized_source_type = normalize_portfolio_memory_search_filter(source_type)
    if (
        normalized_event_type is not None
        and normalized_event_type not in _PORTFOLIO_MEMORY_EVENT_TYPE_SET
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"UNSUPPORTED_PORTFOLIO_MEMORY_EVENT_TYPE: {normalized_event_type}; "
                f"supported_event_types={','.join(_PORTFOLIO_MEMORY_EVENT_TYPES)}"
            ),
        )
    return search_portfolio_memory(
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
        construction_repository=construction_repository,
        pm_quality_score_run_repository=pm_quality_score_run_repository,
        pm_quality_review_action_repository=pm_quality_review_action_repository,
        pm_quality_summary_invocation_repository=pm_quality_summary_invocation_repository,
        campaign_definition_repository=campaign_definition_repository,
        portfolio_ids=portfolio_ids,
        event_type=normalized_event_type,
        supportability_state=cast(
            PortfolioMemorySupportabilityState | None, normalized_supportability_state
        ),
        source_system=normalized_source_system,
        source_type=normalized_source_type,
        limit=limit,
        offset=offset,
        source_scan_limit=source_scan_limit,
    )


@router.get(
    "/{portfolio_id}/events/{event_id}",
    response_model=DpmPortfolioMemoryEventLookup,
    summary="Get one portfolio-memory event",
    description=(
        "What: Return one exact source-backed portfolio-memory event for a portfolio using the "
        "stable event id surfaced by the timeline or search API.\n"
        "When: Use when PM, CIO, operations, audit, Gateway, or Workbench consumers need to "
        "drill down from a search hit into the exact event row without loading unrelated "
        "portfolio-memory rows.\n"
        "How: The endpoint composes the same Manage-local memory view as the detail route, "
        "selects the requested event id, and returns the event with the memory content hash for "
        "reconciliation. It does not discover the global portfolio universe, query external "
        "source-owner event stores, project OMS acknowledgement/fill/settlement events, project "
        "client contact/message/delivery/approval events, or recalculate risk, performance, "
        "execution, tax, cash, FX, mandate-health, PM-quality, report, archive, or AI truth."
    ),
)
def get_portfolio_memory_event(
    portfolio_id: str,
    event_id: str,
    limit: int = Query(default=500, ge=1, le=1000, description="Maximum events to scan."),
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    construction_repository: ConstructionRepository = Depends(get_construction_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    outcome_review_repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    pm_quality_score_run_repository: DpmPmQualityScoreRunRepository = Depends(
        get_pm_quality_score_run_repository
    ),
    pm_quality_review_action_repository: DpmPmQualityReviewActionRepository = Depends(
        get_pm_quality_review_action_repository
    ),
    pm_quality_summary_invocation_repository: DpmPmQualitySummaryInvocationRepository = Depends(
        get_pm_quality_summary_invocation_repository
    ),
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmPortfolioMemoryEventLookup:
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
        limit=limit,
    )
    lookup = build_portfolio_memory_event_lookup(
        memory=memory,
        event_id=event_id,
        support_boundary=(
            "Manage-local memory event lookup selects exact events from persisted Manage "
            "evidence only; it does not discover the global portfolio universe, query "
            "external source-owner event stores, project OMS acknowledgement/fill/"
            "settlement events, or recalculate source truth."
        ),
    )
    if lookup is not None:
        return lookup
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=(
            f"PORTFOLIO_MEMORY_EVENT_NOT_FOUND: {event_id}; "
            f"portfolio_id={portfolio_id}; scanned_event_count={memory.event_count}; "
            "Manage-local lookup does not query external source-owner event stores."
        ),
    )


@router.get(
    "/{portfolio_id}",
    response_model=DpmPortfolioMemory,
    summary="Get source-backed portfolio memory",
    description=(
        "What: Return a deterministic, source-backed portfolio timeline across manage-owned "
        "mandate health, monitoring exceptions, construction alternative decisions, proof packs, "
        "rebalance waves, internal handoffs, and outcome reviews.\n"
        "When: Use when PM, CIO, operations, audit, Gateway, or Workbench consumers need a "
        "single queryable memory view for a portfolio without reconstructing source truth.\n"
        "How: The endpoint composes persisted RFC-0038, RFC-0039, RFC-0040, RFC-0041, and "
        "RFC-0042 records, including bounded campaign-definition workflow evidence. It preserves "
        "source refs, hashes, states, and reason codes, and "
        "publishes source-event family posture for supported and deferred source owners; it does "
        "not compute risk, performance, execution, tax, cash, mandate-health, PM quality scores, "
        "PM review decisions, external order truth, or client communication truth locally."
    ),
)
def get_portfolio_memory(
    portfolio_id: str,
    limit: int = Query(default=100, ge=1, le=500, description="Maximum events to return."),
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    construction_repository: ConstructionRepository = Depends(get_construction_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    outcome_review_repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    pm_quality_score_run_repository: DpmPmQualityScoreRunRepository = Depends(
        get_pm_quality_score_run_repository
    ),
    pm_quality_review_action_repository: DpmPmQualityReviewActionRepository = Depends(
        get_pm_quality_review_action_repository
    ),
    pm_quality_summary_invocation_repository: DpmPmQualitySummaryInvocationRepository = Depends(
        get_pm_quality_summary_invocation_repository
    ),
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmPortfolioMemory:
    return build_portfolio_memory(
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
        limit=limit,
    )
