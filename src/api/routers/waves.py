from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import (
    get_advise_authority_client,
    get_campaign_definition_repository,
    get_construction_repository,
    get_mandate_repository,
    get_outcome_review_repository,
    get_proof_pack_repository,
    get_risk_authority_client,
    get_wave_repository,
)
from src.api.routers.wave_response_contracts import (
    DpmWaveDetailResponse,
    DpmWaveItemsResponse,
    DpmWaveProofPackPostureResponse,
    DpmWaveResponse,
    DpmWaveSearchResponse,
    DpmWaveSupportabilityResponse,
)
from src.api.routers.wave_request_models import (
    DpmWavePreviewRequest,
    DpmWaveSelectionRequest,
    DpmWaveSimulationRequest,
    DpmWaveSourceCheckRequest,
    DpmWaveWorkflowCommandRequest,
)
from src.api.routers.wave_campaign_definition_http import (
    get_campaign_definition_response,
)
from src.api.routers.wave_campaign_definition_routes import (
    router as campaign_definition_router,
)
from src.api.routers.wave_campaign_evidence_routes import (
    router as campaign_evidence_router,
)
from src.api.routers.wave_campaign_read_model_routes import (
    router as campaign_read_model_router,
)
from src.api.routers.wave_route_parameters import (
    CampaignActiveOnQuery,
    CampaignEvidenceLimitQuery,
    CampaignEvidenceOffsetQuery,
    CampaignDefinitionIdPath,
    CampaignDefinitionVersionPath,
    CampaignIncludeLaunchPackageQuery,
    CampaignLaunchActorIdOptionalQuery,
    CampaignLaunchActorIdRequiredQuery,
    CampaignLaunchCorrelationIdQuery,
    CampaignLaunchHistoryLimitQuery,
    CampaignLaunchHistoryOffsetQuery,
    CampaignLaunchRequestedAsOfDateQuery,
    WaveCorrelationIdHeader,
    WaveCreateIdempotencyKeyHeader,
    WaveIdPath,
    WaveItemIdPath,
)
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionLaunchRequest,
)
from src.api.routers.wave_campaign_launch_http import (
    launch_bulk_review_campaign_definition_response,
)
from src.api.routers.wave_campaign_read_http import (
    get_campaign_definition_launch_package_response,
    get_campaign_definition_preview_readiness_response,
    get_campaign_definition_workflow_overview_response,
    list_campaign_definition_launch_history_response,
    list_campaign_definition_lifecycle_events_response,
)
from src.api.routers.wave_create_preview_http import create_wave_response, preview_wave_response
from src.api.routers.wave_openapi_examples import (
    SOURCE_CHECK_WAVE_EXAMPLE,
    WAVE_EXAMPLE,
)
from src.api.routers.wave_read_http import (
    get_wave_detail_response,
    get_wave_items_response,
    get_wave_proof_pack_posture_response,
)
from src.api.routers.wave_report_input_http import get_wave_report_input_response
from src.api.routers.wave_search_http import search_waves_response
from src.api.routers.wave_selection_http import select_wave_item_alternative_response
from src.api.routers.wave_simulation_http import simulate_wave_response
from src.api.routers.wave_source_check_http import source_check_wave_response
from src.api.routers.wave_supportability_http import get_wave_supportability_response
from src.api.routers.wave_workflow_command_http import run_wave_workflow_command_response
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.api.services.rebalance_simulation_service import build_core_resolver_client
from src.api.services import wave_service
from src.core.construction.repository import ConstructionRepository
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionLaunchHistoryPage,
    DpmBulkReviewCampaignDefinitionLaunchPackage,
    DpmBulkReviewCampaignDefinitionPreviewReadiness,
    DpmBulkReviewCampaignDefinitionWorkflowOverview,
    DpmBulkReviewCampaignDefinitionRepository,
    DpmWaveReportInput,
    DpmWaveRepository,
)
from src.core.waves.campaign_definition_events import (
    DpmBulkReviewCampaignDefinitionLifecycleEventPage,
)
from src.infrastructure.risk_authority import (
    LotusRiskAuthorityClient,
)
from src.infrastructure.advise_authority import (
    LotusAdviseAuthorityClient,
)


router = APIRouter(prefix="/rebalance/waves", tags=["lotus-manage Rebalance Waves"])
logger = logging.getLogger(__name__)

router.include_router(campaign_definition_router)
router.include_router(campaign_read_model_router)


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_200_OK,
    summary="Get bulk-review campaign definition",
    description="Retrieves one immutable Manage-owned bulk-review campaign definition.",
)
def get_bulk_review_campaign_definition(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    return get_campaign_definition_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        repository=repository,
    )


router.include_router(campaign_evidence_router)


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/lifecycle-events",
    response_model=DpmBulkReviewCampaignDefinitionLifecycleEventPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign definition lifecycle events",
    description=(
        "Projects bounded lifecycle events for one persisted Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. Events are derived from the immutable definition "
        "record and show create, retire, and supersede posture without discovering the global "
        "portfolio universe, recalculating campaign membership, running maker-checker workflow, "
        "or claiming OMS execution."
    ),
)
def list_bulk_review_campaign_definition_lifecycle_events(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionLifecycleEventPage:
    return list_campaign_definition_lifecycle_events_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        repository=repository,
    )


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch-history",
    response_model=DpmBulkReviewCampaignDefinitionLaunchHistoryPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign definition launch history",
    description=(
        "Returns a bounded append-only launch audit page for one persisted Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. The records identify durable waves launched from "
        "the definition and preserve actor, requested as-of date, correlation, and idempotency "
        "evidence. They do not imply maker-checker workflow, trade approval, order generation, "
        "routing, fills, settlement, or OMS execution."
    ),
)
def list_bulk_review_campaign_definition_launch_history(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    limit: CampaignEvidenceLimitQuery = 50,
    offset: CampaignEvidenceOffsetQuery = 0,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionLaunchHistoryPage:
    return list_campaign_definition_launch_history_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        limit=limit,
        offset=offset,
        repository=repository,
    )


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/workflow-overview",
    response_model=DpmBulkReviewCampaignDefinitionWorkflowOverview,
    status_code=status.HTTP_200_OK,
    summary="Get bulk-review campaign workflow overview",
    description=(
        "Returns an operator-safe workflow overview for one persisted Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. The overview composes discovery posture, "
        "fail-closed preview readiness, lifecycle events, launch history, and optional launch "
        "package guidance. It does not discover the global portfolio universe, recalculate "
        "source facts, run maker-checker workflow, approve trades, route orders, or claim OMS "
        "execution."
    ),
)
def get_bulk_review_campaign_definition_workflow_overview(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    requested_as_of_date: CampaignLaunchRequestedAsOfDateQuery,
    actor_id: CampaignLaunchActorIdOptionalQuery = None,
    active_on: CampaignActiveOnQuery = None,
    include_launch_package: CampaignIncludeLaunchPackageQuery = True,
    correlation_id: CampaignLaunchCorrelationIdQuery = None,
    launch_history_limit: CampaignLaunchHistoryLimitQuery = 20,
    launch_history_offset: CampaignLaunchHistoryOffsetQuery = 0,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionWorkflowOverview:
    return get_campaign_definition_workflow_overview_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=active_on,
        launch_history_limit=launch_history_limit,
        launch_history_offset=launch_history_offset,
        include_launch_package=include_launch_package,
        correlation_id=correlation_id,
        repository=repository,
    )


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/preview-readiness",
    response_model=DpmBulkReviewCampaignDefinitionPreviewReadiness,
    status_code=status.HTTP_200_OK,
    summary="Check bulk-review campaign definition preview readiness",
    description=(
        "Evaluates whether one persisted Manage-owned `BulkReviewCampaignDefinition:v1` can be "
        "used for new `BULK_REVIEW_CAMPAIGN` preview/create. The response is a bounded "
        "fail-closed supportability check over lifecycle status, as-of date, source-backed "
        "candidate eligibility, approval evidence, expiry, and optional actor entitlement. It "
        "does not create a wave, discover the global portfolio universe, recalculate membership, "
        "run maker-checker workflow, approve trades, or claim OMS execution."
    ),
)
def get_bulk_review_campaign_definition_preview_readiness(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    requested_as_of_date: CampaignLaunchRequestedAsOfDateQuery,
    actor_id: CampaignLaunchActorIdOptionalQuery = None,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionPreviewReadiness:
    return get_campaign_definition_preview_readiness_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        repository=repository,
    )


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch-package",
    response_model=DpmBulkReviewCampaignDefinitionLaunchPackage,
    status_code=status.HTTP_200_OK,
    summary="Build bulk-review campaign definition launch package",
    description=(
        "Builds an operator launch package for one persisted Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. The package contains fail-closed preview readiness, "
        "a bounded preview/create request draft, idempotency and correlation headers, and explicit "
        "operating boundaries for downstream consumers. It does not create a wave, discover the "
        "global portfolio universe, recalculate membership, run maker-checker workflow, approve "
        "trades, or claim OMS execution."
    ),
)
def get_bulk_review_campaign_definition_launch_package(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    requested_as_of_date: CampaignLaunchRequestedAsOfDateQuery,
    actor_id: CampaignLaunchActorIdRequiredQuery,
    correlation_id: CampaignLaunchCorrelationIdQuery = None,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionLaunchPackage:
    return get_campaign_definition_launch_package_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        correlation_id=correlation_id,
        repository=repository,
    )


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Launch bulk-review campaign definition",
    description=(
        "Creates a durable `BULK_REVIEW_CAMPAIGN` wave from one persisted Manage-owned "
        "`BulkReviewCampaignDefinition:v1` only when its launch package is ready. The endpoint "
        "uses the persisted source-backed candidate set and deterministic launch idempotency key; "
        "it does not discover the global portfolio universe, recalculate membership, run "
        "maker-checker workflow, approve trades, route orders, or claim OMS execution."
    ),
)
def launch_bulk_review_campaign_definition(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    request: DpmBulkReviewCampaignDefinitionLaunchRequest,
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmWaveResponse:
    return launch_bulk_review_campaign_definition_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        request=request,
        mandate_repository=mandate_repository,
        wave_repository=wave_repository,
        campaign_definition_repository=campaign_definition_repository,
        core_resolver_factory=build_core_resolver_client,
    )


@router.post(
    "/preview",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview an affected-portfolio rebalance wave",
    description=(
        "Builds a non-durable RFC-0041 affected-portfolio wave preview. "
        "`EXPLICIT_PORTFOLIO_LIST` preserves source refs from the request or existing mandate "
        "digital twins. `PM_BOOK_REVIEW` resolves the cohort from the lotus-core "
        "`PortfolioManagerBookMembership:v1` source product. `CIO_MODEL_CHANGE` resolves the "
        "cohort from lotus-core `CioModelChangeAffectedCohort:v1`. `RISK_EVENT` evaluates the "
        "candidate set through lotus-risk `RiskEventAffectedCohort:v1` and preserves source-owned "
        "membership evidence. `TACTICAL_HOUSE_VIEW` evaluates the candidate set through "
        "lotus-advise `TacticalHouseViewAffectedCohort:v1` and preserves source-owned "
        "house-view/candidate evidence. `BULK_REVIEW_CAMPAIGN` builds the Manage-owned "
        "`BulkReviewCampaignMembership:v1` envelope from inline or persisted source-backed "
        "candidate portfolios, or from lotus-core `DpmPortfolioUniverseCandidate:v1` when "
        "`campaign_candidate_source=CORE_DPM_PORTFOLIO_UNIVERSE`. Core candidate discovery walks "
        "bounded continuation pages to terminal exhaustion and fails closed on unavailable, "
        "incomplete, degraded, empty, duplicate, non-terminating, or still-truncated source pages. "
        "Unsupported trigger types remain blocked; the endpoint does not recompute house-view, "
        "holdings, risk, performance, simulation, approval, staging, operations handoff, "
        "relationship householding, global portfolio-universe semantics, workflow orchestration, "
        "or OMS execution."
    ),
    responses={
        200: {
            "description": "Non-durable wave preview with explicit candidate and blocked states.",
            "content": {"application/json": {"example": WAVE_EXAMPLE}},
        },
        422: {
            "description": "Unsupported trigger, missing source evidence, or invalid request.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "TACTICAL_HOUSE_VIEW_REQUIRED",
                            "message": "TACTICAL_HOUSE_VIEW requires tactical_house_view source evidence.",
                        }
                    }
                }
            },
        },
    },
)
def preview_wave(
    request: DpmWavePreviewRequest,
    x_correlation_id: WaveCorrelationIdHeader = None,
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    advise_authority_client: LotusAdviseAuthorityClient | None = Depends(
        get_advise_authority_client
    ),
    risk_authority_client: LotusRiskAuthorityClient | None = Depends(get_risk_authority_client),
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmWaveResponse:
    correlation_id = x_correlation_id or f"corr_wave_preview_{request.trigger_id}"
    return preview_wave_response(
        request=request,
        correlation_id=correlation_id,
        mandate_repository=mandate_repository,
        advise_authority_client=advise_authority_client,
        risk_authority_client=risk_authority_client,
        campaign_definition_repository=campaign_definition_repository,
        core_resolver_factory=build_core_resolver_client,
    )


@router.post(
    "",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a durable affected-portfolio rebalance wave",
    description=(
        "Creates a durable RFC-0041 rebalance wave. `EXPLICIT_PORTFOLIO_LIST` uses caller-supplied "
        "affected portfolios, while `PM_BOOK_REVIEW` and `CIO_MODEL_CHANGE` resolve cohorts from "
        "lotus-core source products and `RISK_EVENT` evaluates the candidate set through "
        "lotus-risk `RiskEventAffectedCohort:v1` before persistence. `TACTICAL_HOUSE_VIEW` "
        "evaluates the candidate set through lotus-advise "
        "`TacticalHouseViewAffectedCohort:v1` before persistence. `BULK_REVIEW_CAMPAIGN` persists "
        "a Manage-owned campaign membership wave from inline, persisted, or lotus-core "
        "`DpmPortfolioUniverseCandidate:v1` source-backed candidates. Core candidate discovery "
        "requires `campaign_candidate_source=CORE_DPM_PORTFOLIO_UNIVERSE`, walks bounded "
        "continuation pages to terminal exhaustion, and fails closed on unavailable, incomplete, "
        "degraded, empty, duplicate, non-terminating, or still-truncated source pages. Required header: "
        "`Idempotency-Key`. Unsupported trigger types are rejected and missing source evidence "
        "produces blocked items, not false readiness; the route does not claim relationship "
        "householding, global portfolio-universe ownership, workflow orchestration, client "
        "communication workflow, order routing, or OMS execution."
    ),
    responses={
        201: {
            "description": "Durable wave created.",
            "content": {"application/json": {"example": {**WAVE_EXAMPLE, "durable": True}}},
        },
        409: {
            "description": "Wave identity or idempotency conflict.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "WAVE_CREATE_CONFLICT",
                            "message": "DPM_WAVE_IDEMPOTENCY_CONFLICT",
                        }
                    }
                }
            },
        },
        422: {
            "description": "Unsupported trigger, missing source evidence, or invalid request.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "TACTICAL_HOUSE_VIEW_REQUIRED",
                            "message": "TACTICAL_HOUSE_VIEW requires tactical_house_view source evidence.",
                        }
                    }
                }
            },
        },
    },
)
def create_wave(
    request: DpmWavePreviewRequest,
    idempotency_key: WaveCreateIdempotencyKeyHeader,
    x_correlation_id: WaveCorrelationIdHeader = None,
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    advise_authority_client: LotusAdviseAuthorityClient | None = Depends(
        get_advise_authority_client
    ),
    risk_authority_client: LotusRiskAuthorityClient | None = Depends(get_risk_authority_client),
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmWaveResponse:
    correlation_id = x_correlation_id or f"corr_wave_create_{request.trigger_id}"
    return create_wave_response(
        request=request,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        mandate_repository=mandate_repository,
        wave_repository=wave_repository,
        advise_authority_client=advise_authority_client,
        risk_authority_client=risk_authority_client,
        campaign_definition_repository=campaign_definition_repository,
        core_resolver_factory=build_core_resolver_client,
    )


@router.get(
    "",
    response_model=DpmWaveSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search durable rebalance waves",
    description=(
        "Returns a bounded search page over durable RFC-0041 waves. Search reads persisted manage "
        "wave truth and derives supportability from item states; it does not recalculate source "
        "readiness, construction alternatives, proof-pack state, or handoff posture."
    ),
    responses={
        200: {
            "description": "Bounded search page of durable waves.",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "wave_id": "dwv_001",
                                "wave_state": "HANDOFF_READY",
                                "trigger_type": "EXPLICIT_PORTFOLIO_LIST",
                                "trigger_id": "manual-wave-001",
                                "as_of_date": "2026-05-03",
                                "created_at": "2026-05-03T09:30:00Z",
                                "created_by": "pm_001",
                                "item_count": 1,
                                "aggregate_metrics": {
                                    "item_count": 1,
                                    "state_counts": {"HANDOFF_READY": 1},
                                    "ready_item_count": 1,
                                    "blocked_item_count": 0,
                                    "review_required_item_count": 0,
                                    "source_degraded_item_count": 0,
                                },
                                "supportability_state": "ready",
                                "supportability_reason": "wave_supportability_ready",
                                "latest_event_type": "STATE_TRANSITION",
                                "latest_event_reason_code": "WAVE_HANDOFF_READY",
                            }
                        ],
                        "limit": 50,
                        "offset": 0,
                        "returned_count": 1,
                    }
                }
            },
        }
    },
)
def search_waves(
    state: Annotated[
        str | None,
        Query(
            description="Optional wave state filter, for example HANDOFF_READY.",
            examples=["HANDOFF_READY"],
        ),
    ] = None,
    trigger_type: Annotated[
        str | None,
        Query(
            description="Optional trigger type filter.",
            examples=["EXPLICIT_PORTFOLIO_LIST"],
        ),
    ] = None,
    as_of_date: Annotated[
        str | None,
        Query(description="Optional business as-of date filter.", examples=["2026-05-03"]),
    ] = None,
    supportability_state: Annotated[
        Literal["ready", "degraded", "blocked"] | None,
        Query(
            description="Optional derived supportability filter.",
            examples=["ready"],
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Maximum number of waves to return.", examples=[50]),
    ] = 50,
    offset: Annotated[
        int,
        Query(ge=0, description="Zero-based page offset.", examples=[0]),
    ] = 0,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveSearchResponse:
    return search_waves_response(
        wave_repository=wave_repository,
        state=state,
        trigger_type=trigger_type,
        as_of_date=as_of_date,
        supportability_state=supportability_state,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{wave_id}",
    response_model=DpmWaveDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve durable rebalance wave detail",
    description=(
        "Returns one persisted RFC-0041 wave with items, aggregate metrics, events, source refs, "
        "latest supportability, and proof-pack/handoff posture. The endpoint reads durable manage "
        "state and does not regenerate downstream construction or proof-pack artifacts."
    ),
    responses={
        200: {"description": "Persisted wave detail."},
        404: {"description": "Wave not found."},
    },
)
def get_wave_detail(
    wave_id: WaveIdPath,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveDetailResponse:
    return get_wave_detail_response(
        wave_id=wave_id,
        wave_repository=wave_repository,
    )


@router.get(
    "/{wave_id}/items",
    response_model=DpmWaveItemsResponse,
    status_code=status.HTTP_200_OK,
    summary="List rebalance wave items",
    description=(
        "Returns persisted item-level wave posture for source readiness, construction selection, "
        "proof-pack linkage, and internal operations handoff. The response is intended for Gateway "
        "and Workbench command-center realization without UI-side recomputation."
    ),
    responses={
        200: {"description": "Persisted wave item list."},
        404: {"description": "Wave not found."},
    },
)
def get_wave_items(
    wave_id: WaveIdPath,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveItemsResponse:
    return get_wave_items_response(
        wave_id=wave_id,
        wave_repository=wave_repository,
    )


@router.post(
    "/{wave_id}/source-check",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Source-check a durable rebalance wave",
    description=(
        "Evaluates RFC-0041 source readiness for each durable wave item using persisted mandate "
        "digital twins, mandate health snapshots, and their source lineage. Items are classified "
        "as `SOURCE_READY`, `SOURCE_DEGRADED`, `REVIEW_REQUIRED`, or `SOURCE_BLOCKED`; caller "
        "portfolio ids or supplied refs alone never promote an item to ready. Repeating the call "
        "after the wave is already `SOURCE_CHECKED` returns the persisted wave as an idempotent "
        "replay without appending a duplicate event."
    ),
    responses={
        200: {
            "description": "Durable source-checked wave with item classifications.",
            "content": {"application/json": {"example": SOURCE_CHECK_WAVE_EXAMPLE}},
        },
        404: {
            "description": "Wave not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "DPM_WAVE_NOT_FOUND",
                            "message": "Wave dwv_missing was not found.",
                        }
                    }
                }
            },
        },
        409: {
            "description": "Wave version conflict during optimistic update.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "DPM_WAVE_VERSION_CONFLICT",
                            "message": "DPM_WAVE_VERSION_CONFLICT",
                        }
                    }
                }
            },
        },
        422: {
            "description": "Wave is not in a state that can be source-checked.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "DPM_WAVE_SOURCE_CHECK_INVALID_STATE",
                            "message": "Wave dwv_001 cannot be source-checked from state DRAFT.",
                        }
                    }
                }
            },
        },
    },
)
def source_check_wave(
    wave_id: WaveIdPath,
    request: DpmWaveSourceCheckRequest,
    x_correlation_id: WaveCorrelationIdHeader = None,
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    return source_check_wave_response(
        wave_id=wave_id,
        request=request,
        correlation_id=x_correlation_id or f"corr_wave_source_check_{wave_id}",
        mandate_repository=mandate_repository,
        wave_repository=wave_repository,
    )


@router.post(
    "/{wave_id}/simulate",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate construction alternatives for source-ready wave items",
    description=(
        "Calls the RFC-0039 construction alternative authority for source-ready wave items that "
        "have caller-supplied construction inputs. Source-blocked, degraded, and review-required "
        "items are preserved with their reasons. Ready items without construction input become "
        "`SIMULATION_BLOCKED`; the endpoint does not synthesize portfolio holdings, market data, "
        "model targets, or shelf data from mandate identifiers."
    ),
    responses={
        200: {"description": "Durable simulated or partially simulated wave."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave is not source-checked or request is invalid."},
    },
)
def simulate_wave(
    wave_id: WaveIdPath,
    request: DpmWaveSimulationRequest,
    x_correlation_id: WaveCorrelationIdHeader = None,
    construction_repository: ConstructionRepository = Depends(get_construction_repository),
    risk_authority_client: LotusRiskAuthorityClient | None = Depends(get_risk_authority_client),
    run_service: DpmRunSupportService = Depends(get_dpm_run_support_service),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    return simulate_wave_response(
        wave_id=wave_id,
        request=request,
        correlation_id=x_correlation_id or f"corr_wave_simulate_{wave_id}",
        construction_repository=construction_repository,
        run_service=run_service,
        wave_repository=wave_repository,
        risk_authority_client=risk_authority_client,
    )


@router.post(
    "/{wave_id}/items/{wave_item_id}/select",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Select a construction alternative for a wave item",
    description=(
        "Records item-level RFC-0039 alternative selection with actor, reason, and optional "
        "comment. When requested, it generates an RFC-0040 proof pack from the selected "
        "alternative. Proof-pack failures are represented as degraded selection posture instead "
        "of unsupported proof-pack readiness."
    ),
    responses={
        200: {"description": "Wave item selection recorded and persisted."},
        404: {"description": "Wave, item, alternative set, or alternative id was not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave or item is not eligible for selection."},
    },
)
def select_wave_item_alternative(
    wave_id: WaveIdPath,
    wave_item_id: WaveItemIdPath,
    request: DpmWaveSelectionRequest,
    x_correlation_id: WaveCorrelationIdHeader = None,
    construction_repository: ConstructionRepository = Depends(get_construction_repository),
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    run_service: DpmRunSupportService = Depends(get_dpm_run_support_service),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    return select_wave_item_alternative_response(
        wave_id=wave_id,
        wave_item_id=wave_item_id,
        request=request,
        correlation_id=x_correlation_id or f"corr_wave_select_{wave_id}_{wave_item_id}",
        construction_repository=construction_repository,
        proof_pack_repository=proof_pack_repository,
        mandate_repository=mandate_repository,
        run_service=run_service,
        wave_repository=wave_repository,
    )


@router.post(
    "/{wave_id}/approve",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve selected rebalance wave items",
    description=(
        "Approves selected or proof-pack-ready wave items with actor attribution. Source-blocked, "
        "simulation-blocked, degraded, failed, or otherwise unselected items are never approved; "
        "mixed waves become `APPROVED_WITH_EXCEPTIONS`. Repeating the command after approval "
        "returns the persisted wave without appending duplicate approval evidence."
    ),
    responses={
        200: {"description": "Wave approval recorded or replayed."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave has no eligible items or is not approval-ready."},
    },
)
def approve_wave(
    wave_id: WaveIdPath,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: WaveCorrelationIdHeader = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    return run_wave_workflow_command_response(
        command=wave_service.approve_wave,
        wave_id=wave_id,
        request=request,
        correlation_id=x_correlation_id or f"corr_wave_approve_{wave_id}",
        wave_repository=wave_repository,
    )


@router.post(
    "/{wave_id}/stage",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Stage approved rebalance wave items",
    description=(
        "Stages approved wave items for internal operations handoff. The endpoint does not stage "
        "blocked or unapproved items and does not claim external order execution. Repeating the "
        "command after staging or handoff readiness returns the persisted wave without duplicate "
        "events."
    ),
    responses={
        200: {"description": "Wave staging recorded or replayed."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave has no approved items or is not stage-ready."},
    },
)
def stage_wave(
    wave_id: WaveIdPath,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: WaveCorrelationIdHeader = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    return run_wave_workflow_command_response(
        command=wave_service.stage_wave,
        wave_id=wave_id,
        request=request,
        correlation_id=x_correlation_id or f"corr_wave_stage_{wave_id}",
        wave_repository=wave_repository,
    )


@router.post(
    "/{wave_id}/handoff",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Create internal operations handoff evidence",
    description=(
        "Creates append-only internal operations handoff evidence for staged wave items. This is "
        "a manage-owned readiness package only: it records `external_execution_claimed=false` and "
        "does not send orders, client communications, or external execution instructions."
    ),
    responses={
        200: {"description": "Wave handoff evidence recorded or replayed."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave has no staged items or is not handoff-ready."},
    },
)
def handoff_wave(
    wave_id: WaveIdPath,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: WaveCorrelationIdHeader = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    return run_wave_workflow_command_response(
        command=wave_service.handoff_wave,
        wave_id=wave_id,
        request=request,
        correlation_id=x_correlation_id or f"corr_wave_handoff_{wave_id}",
        wave_repository=wave_repository,
    )


@router.post(
    "/{wave_id}/cancel",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel a rebalance wave before external execution",
    description=(
        "Cancels an eligible RFC-0041 wave with actor attribution and preserves all item evidence. "
        "Items that have not reached internal handoff are marked `EXCLUDED` with cancellation "
        "diagnostics; manage still records `external_execution_claimed=false`. The endpoint does "
        "not cancel external orders, because manage wave handoff is an internal readiness package "
        "and not an execution instruction. Repeating the command after cancellation returns the "
        "persisted wave without duplicate cancellation events."
    ),
    responses={
        200: {"description": "Wave cancellation recorded or replayed."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave state cannot be cancelled."},
    },
)
def cancel_wave(
    wave_id: WaveIdPath,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: WaveCorrelationIdHeader = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    return run_wave_workflow_command_response(
        command=wave_service.cancel_wave,
        wave_id=wave_id,
        request=request,
        correlation_id=x_correlation_id or f"corr_wave_cancel_{wave_id}",
        wave_repository=wave_repository,
    )


@router.get(
    "/{wave_id}/proof-pack",
    response_model=DpmWaveProofPackPostureResponse,
    status_code=status.HTTP_200_OK,
    summary="Get wave proof-pack and handoff posture",
    description=(
        "Returns item-level RFC-0040 proof-pack refs, degraded proof-pack posture, append-only "
        "handoff refs, and the no-external-execution boundary for a persisted wave. The endpoint "
        "does not rebuild proof packs or claim external execution."
    ),
    responses={
        200: {"description": "Wave proof-pack and handoff posture."},
        404: {"description": "Wave not found."},
    },
)
def get_wave_proof_pack_posture(
    wave_id: WaveIdPath,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveProofPackPostureResponse:
    return get_wave_proof_pack_posture_response(
        wave_id=wave_id,
        wave_repository=wave_repository,
    )


@router.get(
    "/{wave_id}/report-input",
    response_model=DpmWaveReportInput,
    status_code=status.HTTP_200_OK,
    summary="Get wave report input",
    description=(
        "Returns deterministic `DpmWaveReportInput` for a persisted RFC-0041 rebalance wave. "
        "`lotus-report`, `lotus-render`, and `lotus-archive` can use this payload to materialize "
        "and govern wave evidence without reconstructing wave state, proof-pack linkage, internal "
        "handoff refs, source hashes, or supportability posture. `lotus-manage` does not generate "
        "rendered reports, archive records, or external execution claims."
    ),
    responses={
        200: {"description": "Generated wave report-input payload."},
        404: {"description": "Wave not found."},
        422: {
            "description": (
                "Wave evidence crosses the unsupported external OMS/execution boundary and cannot "
                "be emitted as manage report input."
            )
        },
    },
)
def get_wave_report_input(
    wave_id: WaveIdPath,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    outcome_review_repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmWaveReportInput:
    return get_wave_report_input_response(
        wave_id=wave_id,
        wave_repository=wave_repository,
        proof_pack_repository=proof_pack_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
    )


@router.get(
    "/{wave_id}/supportability",
    response_model=DpmWaveSupportabilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get product-safe wave supportability diagnostics",
    description=(
        "Returns operator-safe RFC-0041 wave supportability diagnostics. The response excludes "
        "portfolio identifiers, client identifiers, raw request bodies, raw response bodies, "
        "secrets, and trace details. Use this endpoint to understand blocked/degraded item states, "
        "source owners, bounded reason codes, remediation routes, and support references."
    ),
    responses={
        200: {"description": "Product-safe wave supportability diagnostics."},
        404: {"description": "Wave not found."},
    },
)
def get_wave_supportability(
    wave_id: WaveIdPath,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveSupportabilityResponse:
    return get_wave_supportability_response(
        wave_id=wave_id,
        wave_repository=wave_repository,
        logger=logger,
    )
