from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Query, status

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
from src.api.request_models import RebalanceRequest
from src.api.routers.wave_response_contracts import (
    DpmWaveDetailResponse,
    DpmWaveItemsResponse,
    DpmWaveProofPackPostureResponse,
    DpmWaveResponse,
    DpmWaveSearchItem,
    DpmWaveSearchResponse,
    DpmWaveSupportabilityResponse,
    wave_response,
)
from src.api.routers.wave_request_models import (
    DpmWavePreviewRequest,
    DpmWaveSelectionRequest,
    DpmWaveSimulationRequest,
    DpmWaveSourceCheckRequest,
    DpmWaveWorkflowCommandRequest,
)
from src.api.routers.wave_campaign_definition_http import (
    campaign_definition_conflict_http_exception,
    campaign_definition_launch_blocked_http_exception,
    campaign_definition_lifecycle_http_exception,
    campaign_definition_not_found_http_exception,
    campaign_definition_value_http_exception,
    get_campaign_definition_or_404,
    parse_optional_campaign_discovery_date,
)
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionApprovalDecisionRequest,
    DpmBulkReviewCampaignDefinitionAssignmentActionRequest,
    DpmBulkReviewCampaignDefinitionAssignmentTaskOpenRequest,
    DpmBulkReviewCampaignDefinitionAssignmentTaskTransitionRequest,
    DpmBulkReviewCampaignDefinitionLaunchRequest,
    DpmBulkReviewCampaignDefinitionMakerCheckerControlRequest,
    DpmBulkReviewCampaignDefinitionPage,
    DpmBulkReviewCampaignDefinitionRequest,
    DpmBulkReviewCampaignDefinitionRetirementRequest,
    DpmBulkReviewCampaignDefinitionSupersessionRequest,
)
from src.api.routers.wave_http_errors import (
    wave_lookup_http_exception,
    wave_validation_http_exception,
)
from src.api.routers.wave_openapi_examples import (
    SOURCE_CHECK_WAVE_EXAMPLE,
    WAVE_EXAMPLE,
)
from src.api.routers.wave_portfolio_resolution import (
    resolve_portfolio_inputs_for_request,
)
from src.api.routers.wave_read_http import (
    get_wave_detail_response,
    get_wave_items_response,
    get_wave_proof_pack_posture_response,
)
from src.api.routers.wave_supportability_http import get_wave_supportability_response
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.api.services.rebalance_simulation_service import build_core_resolver_client
from src.api.services import wave_service
from src.core.construction.repository import ConstructionRepository
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves import (
    CampaignApprovalInboxStatus,
    CampaignAssignmentEscalationTier,
    CampaignAssignmentTaskStatus,
    CampaignWorkflowBoardStatus,
    CampaignWorkflowNextAction,
    CampaignWorkflowAutomationAction,
    CampaignWorkflowAutomationStatus,
    DpmBulkReviewCampaignApprovalInboxPage,
    DpmBulkReviewCampaignAssignmentPlanPage,
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionApprovalDecisionPage,
    DpmBulkReviewCampaignDefinitionAssignmentActionPage,
    DpmBulkReviewCampaignDefinitionAssignmentTaskPage,
    DpmBulkReviewCampaignDefinitionMakerCheckerControlPage,
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmBulkReviewCampaignDiscoveryPage,
    DpmBulkReviewCampaignDefinitionLaunchHistoryPage,
    DpmBulkReviewCampaignDefinitionLaunchBlocked,
    DpmBulkReviewCampaignDefinitionLaunchPackage,
    DpmBulkReviewCampaignOperatingQueuePage,
    DpmBulkReviewCampaignWorkflowBoardPage,
    DpmBulkReviewCampaignWorkflowAutomationPage,
    DpmBulkReviewCampaignDefinitionPreviewReadiness,
    DpmBulkReviewCampaignDefinitionWorkflowOverview,
    DpmBulkReviewCampaignDefinitionRepository,
    DpmWaveReportInput,
    DpmWaveRepository,
    build_bulk_review_campaign_discovery_item,
    build_bulk_review_campaign_definition_preview_readiness,
    build_bulk_review_campaign_definition_launch_package,
    build_bulk_review_campaign_definition_launch_command,
    build_bulk_review_campaign_definition_launch_history_page,
    record_bulk_review_campaign_definition_launch,
    build_bulk_review_campaign_definition_approval_decision_page,
    build_bulk_review_campaign_definition_assignment_action_page,
    build_bulk_review_campaign_definition_assignment_task_page,
    build_bulk_review_campaign_definition_maker_checker_control_page,
    record_bulk_review_campaign_definition_approval_decision,
    record_bulk_review_campaign_definition_assignment_action,
    open_bulk_review_campaign_definition_assignment_task,
    transition_bulk_review_campaign_definition_assignment_task,
    record_bulk_review_campaign_definition_maker_checker_control,
    build_bulk_review_campaign_approval_inbox_page,
    build_bulk_review_campaign_assignment_plan_page,
    build_bulk_review_campaign_definition_workflow_overview,
    build_bulk_review_campaign_operating_queue_page,
    build_bulk_review_campaign_workflow_board_page,
    build_bulk_review_campaign_workflow_automation_page,
)
from src.core.waves.campaign_definition_lifecycle import (
    DpmBulkReviewCampaignDefinitionLifecycleError,
    retire_bulk_review_campaign_definition as retire_campaign_definition,
    supersede_bulk_review_campaign_definition as supersede_campaign_definition,
)
from src.core.waves.campaign_definition_events import (
    DpmBulkReviewCampaignDefinitionLifecycleEventPage,
    build_bulk_review_campaign_definition_lifecycle_events,
)
from src.infrastructure.risk_authority import (
    LotusRiskAuthorityClient,
)
from src.infrastructure.advise_authority import (
    LotusAdviseAuthorityClient,
)


router = APIRouter(prefix="/rebalance/waves", tags=["lotus-manage Rebalance Waves"])
logger = logging.getLogger(__name__)


@router.put(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_200_OK,
    summary="Persist bulk-review campaign definition",
    description=(
        "Persists an immutable Manage-owned `BulkReviewCampaignDefinition:v1` over a bounded, "
        "source-backed candidate portfolio set. This endpoint does not discover the global book, "
        "own source facts, run maker-checker workflow, expose downstream UI, or claim OMS "
        "execution."
    ),
)
def put_bulk_review_campaign_definition(
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    try:
        definition = DpmBulkReviewCampaignDefinition(
            campaign_id=campaign_id,
            campaign_version=campaign_version,
            display_name=request.display_name,
            status=request.status,
            as_of_date=request.as_of_date,
            rationale=request.rationale,
            eligible_portfolio_types=request.eligible_portfolio_types,
            candidates=request.candidates,
            governance=request.governance,
            source_refs=request.source_refs,
            created_by=request.created_by,
            correlation_id=request.correlation_id,
        )
        repository.save_definition(definition=definition)
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc
    return definition


@router.get(
    "/campaign-definitions",
    response_model=DpmBulkReviewCampaignDefinitionPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign definitions",
    description="Lists immutable Manage-owned bulk-review campaign definitions.",
)
def list_bulk_review_campaign_definitions(
    campaign_id: str | None = Query(default=None),
    campaign_status: Literal["ACTIVE", "RETIRED", "SUPERSEDED"] | None = Query(default=None),
    as_of_date: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionPage:
    items = repository.list_definitions(
        campaign_id=campaign_id,
        status=campaign_status,
        as_of_date=as_of_date,
        limit=limit,
        offset=offset,
    )
    return DpmBulkReviewCampaignDefinitionPage(
        items=items,
        limit=limit,
        offset=offset,
        count=len(items),
    )


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/retire",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_200_OK,
    summary="Retire bulk-review campaign definition",
    description=(
        "Retires a persisted Manage-owned `BulkReviewCampaignDefinition:v1` so it remains "
        "auditable but can no longer be used for new `BULK_REVIEW_CAMPAIGN` preview/create "
        "requests. This lifecycle action does not change the source-backed candidate set, "
        "discover a global portfolio universe, run maker-checker workflow, or claim OMS execution."
    ),
)
def retire_bulk_review_campaign_definition(
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionRetirementRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    try:
        retired = retire_campaign_definition(
            repository=repository,
            campaign_id=campaign_id,
            campaign_version=campaign_version,
            retired_by=request.retired_by,
            retirement_reason=request.retirement_reason,
            correlation_id=request.correlation_id,
        )
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except DpmBulkReviewCampaignDefinitionLifecycleError as exc:
        raise campaign_definition_lifecycle_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc
    if retired is None:
        raise campaign_definition_not_found_http_exception()
    return retired


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/supersede",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_200_OK,
    summary="Supersede bulk-review campaign definition",
    description=(
        "Supersedes a persisted Manage-owned `BulkReviewCampaignDefinition:v1` with an already "
        "persisted ACTIVE replacement version for the same campaign id. Superseded definitions "
        "remain auditable but cannot be used for new `BULK_REVIEW_CAMPAIGN` preview/create "
        "requests. This lifecycle action does not discover the global portfolio universe, "
        "recalculate source facts, run maker-checker workflow, or claim OMS execution."
    ),
)
def supersede_bulk_review_campaign_definition(
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionSupersessionRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    try:
        superseded = supersede_campaign_definition(
            repository=repository,
            campaign_id=campaign_id,
            campaign_version=campaign_version,
            replacement_version=request.superseded_by_campaign_version,
            superseded_by=request.superseded_by,
            supersession_reason=request.supersession_reason,
            correlation_id=request.correlation_id,
        )
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except DpmBulkReviewCampaignDefinitionLifecycleError as exc:
        raise campaign_definition_lifecycle_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc
    if superseded is None:
        raise campaign_definition_not_found_http_exception()
    return superseded


@router.get(
    "/campaign-discovery",
    response_model=DpmBulkReviewCampaignDiscoveryPage,
    status_code=status.HTTP_200_OK,
    summary="Discover persisted bulk-review campaigns",
    description=(
        "Discovers persisted Manage-owned `BulkReviewCampaignDefinition:v1` records as a bounded "
        "front-office operating read model. This endpoint summarizes campaign identity, governance "
        "posture, expiry posture, source-ref count, and source-backed candidate counts. It does not "
        "discover the global portfolio universe, calculate source facts, run maker-checker workflow, "
        "or claim OMS execution. Each item includes `BulkReviewCampaignUniversePosture:v1` so the "
        "persisted-candidate source scope, unsupported global portfolio-universe boundary, required "
        "future `GlobalPortfolioUniverseCampaignCandidateSet:v1` source product, blocked global "
        "candidate-discovery capabilities, and deterministic posture hash are machine-readable."
    ),
)
def discover_bulk_review_campaigns(
    campaign_id: str | None = Query(default=None),
    campaign_status: Literal["ACTIVE", "RETIRED", "SUPERSEDED"] | None = Query(default="ACTIVE"),
    as_of_date: str | None = Query(default=None),
    active_on: str | None = Query(
        default=None,
        description=(
            "Optional ISO date used to classify and filter campaign expiry posture. When supplied "
            "with include_expired=false, expired campaigns are omitted."
        ),
    ),
    include_expired: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDiscoveryPage:
    active_on_date = parse_optional_campaign_discovery_date(
        value=active_on,
        field_name="active_on",
    )
    definitions = repository.list_definitions(
        campaign_id=campaign_id,
        status=campaign_status,
        as_of_date=as_of_date,
        limit=limit,
        offset=offset,
    )
    items = [
        build_bulk_review_campaign_discovery_item(definition=definition, active_on=active_on_date)
        for definition in definitions
    ]
    if active_on_date is not None and not include_expired:
        items = [item for item in items if item.expiry_state != "EXPIRED"]
    return DpmBulkReviewCampaignDiscoveryPage(
        items=items,
        limit=limit,
        offset=offset,
        count=len(items),
    )


@router.get(
    "/campaign-operating-queue",
    response_model=DpmBulkReviewCampaignOperatingQueuePage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign operating queue",
    description=(
        "Returns a Manage-owned operating queue over persisted "
        "`BulkReviewCampaignDefinition:v1` records. The queue composes discovery posture, "
        "fail-closed preview readiness, lifecycle event counts, launch-history posture, and "
        "bounded reason codes so operators can separate launch-ready campaigns from attention "
        "items and closed definitions. It does not discover the global portfolio universe, "
        "recalculate source facts, run maker-checker workflow, approve trades, generate orders, "
        "or claim OMS execution."
    ),
)
def list_bulk_review_campaign_operating_queue(
    campaign_id: str | None = Query(default=None),
    campaign_status: Literal["ACTIVE", "RETIRED", "SUPERSEDED"] | None = Query(default=None),
    as_of_date: str | None = Query(default=None),
    requested_as_of_date: str | None = Query(
        default=None,
        description=(
            "Optional ISO date to evaluate readiness for every returned definition. When omitted, "
            "each definition's persisted campaign as-of date is used."
        ),
        examples=["2026-05-10"],
    ),
    actor_id: str | None = Query(
        default=None,
        description="Optional actor id to evaluate against campaign entitlement evidence.",
    ),
    active_on: str | None = Query(
        default=None,
        description=(
            "Optional ISO date used to classify and filter campaign expiry posture. When supplied "
            "with include_expired=false, expired campaigns are omitted."
        ),
    ),
    include_expired: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignOperatingQueuePage:
    active_on_date = parse_optional_campaign_discovery_date(
        value=active_on,
        field_name="active_on",
    )
    definitions = repository.list_definitions(
        campaign_id=campaign_id,
        status=campaign_status,
        as_of_date=as_of_date,
        limit=limit,
        offset=offset,
    )
    return build_bulk_review_campaign_operating_queue_page(
        definitions=definitions,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=active_on_date,
        include_expired=include_expired,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/campaign-approval-inbox",
    response_model=DpmBulkReviewCampaignApprovalInboxPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign approval attention inbox",
    description=(
        "Returns a read-only approval attention inbox over persisted "
        "`BulkReviewCampaignDefinition:v1` records. The inbox classifies approval-complete, "
        "approval-required, approval-incomplete, expiry-attention, entitlement-attention, and "
        "closed campaign definitions from existing governance evidence and fail-closed readiness "
        "checks. It does not mutate approval state, create maker-checker workflow, approve trades, "
        "generate orders, or claim OMS execution."
    ),
)
def list_bulk_review_campaign_approval_inbox(
    campaign_id: str | None = Query(default=None),
    campaign_status: Literal["ACTIVE", "RETIRED", "SUPERSEDED"] | None = Query(default=None),
    as_of_date: str | None = Query(default=None),
    requested_as_of_date: str | None = Query(
        default=None,
        description=(
            "Optional ISO date to evaluate expiry and readiness. When omitted, each definition's "
            "persisted campaign as-of date is used."
        ),
        examples=["2026-05-10"],
    ),
    actor_id: str | None = Query(
        default=None,
        description="Optional actor id to evaluate against campaign entitlement evidence.",
    ),
    active_on: str | None = Query(
        default=None,
        description="Optional ISO date used to classify discovery expiry posture.",
    ),
    inbox_status: CampaignApprovalInboxStatus | None = Query(
        default=None,
        description="Optional filter for one approval attention posture.",
    ),
    include_closed: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignApprovalInboxPage:
    active_on_date = parse_optional_campaign_discovery_date(
        value=active_on,
        field_name="active_on",
    )
    definitions = repository.list_definitions(
        campaign_id=campaign_id,
        status=campaign_status,
        as_of_date=as_of_date,
        limit=limit,
        offset=offset,
    )
    return build_bulk_review_campaign_approval_inbox_page(
        definitions=definitions,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=active_on_date,
        include_closed=include_closed,
        inbox_status=inbox_status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/campaign-workflow-board",
    response_model=DpmBulkReviewCampaignWorkflowBoardPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign workflow board",
    description=(
        "Returns a read-only cross-actor workflow board over persisted "
        "`BulkReviewCampaignDefinition:v1` records. The board composes the existing operating "
        "queue and approval-attention inbox into actor-aware next-action rows for launch, "
        "approval-decision capture, approval evidence remediation, expiry refresh, entitlement "
        "review, or closed posture. It does not discover the global portfolio universe, "
        "recalculate source facts, mutate approval state, create maker-checker workflow, approve "
        "trades, generate orders, or claim OMS execution."
    ),
)
def list_bulk_review_campaign_workflow_board(
    campaign_id: str | None = Query(default=None),
    campaign_status: Literal["ACTIVE", "RETIRED", "SUPERSEDED"] | None = Query(default=None),
    as_of_date: str | None = Query(default=None),
    requested_as_of_date: str | None = Query(
        default=None,
        description=(
            "Optional ISO date to evaluate readiness and expiry. When omitted, each definition's "
            "persisted campaign as-of date is used."
        ),
        examples=["2026-05-10"],
    ),
    actor_id: str | None = Query(
        default=None,
        description="Optional actor id to evaluate against campaign entitlement evidence.",
    ),
    active_on: str | None = Query(
        default=None,
        description="Optional ISO date used to classify discovery expiry posture.",
    ),
    board_status: CampaignWorkflowBoardStatus | None = Query(
        default=None,
        description="Optional filter for one workflow-board posture.",
    ),
    next_action: CampaignWorkflowNextAction | None = Query(
        default=None,
        description="Optional filter for one derived operator next action.",
    ),
    include_closed: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignWorkflowBoardPage:
    active_on_date = parse_optional_campaign_discovery_date(
        value=active_on,
        field_name="active_on",
    )
    definitions = repository.list_definitions(
        campaign_id=campaign_id,
        status=campaign_status,
        as_of_date=as_of_date,
        limit=limit,
        offset=offset,
    )
    return build_bulk_review_campaign_workflow_board_page(
        definitions=definitions,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=active_on_date,
        include_closed=include_closed,
        board_status=board_status,
        next_action=next_action,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/campaign-assignment-plan",
    response_model=DpmBulkReviewCampaignAssignmentPlanPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign assignment plan",
    description=(
        "Returns a read-only assignment and escalation plan over persisted "
        "`BulkReviewCampaignDefinition:v1` records. The plan derives assigned actors, escalation "
        "tier, SLA posture, and reason codes from the existing workflow board without mutating "
        "assignment state, creating escalation tasks, discovering the global portfolio universe, "
        "recalculating source facts, mutating approval state, creating maker-checker workflow, "
        "approving trades, generating orders, or claiming OMS execution."
    ),
)
def list_bulk_review_campaign_assignment_plan(
    campaign_id: str | None = Query(default=None),
    campaign_status: Literal["ACTIVE", "RETIRED", "SUPERSEDED"] | None = Query(default=None),
    as_of_date: str | None = Query(default=None),
    requested_as_of_date: str | None = Query(
        default=None,
        description=(
            "Optional ISO date to evaluate readiness and expiry. When omitted, each definition's "
            "persisted campaign as-of date is used."
        ),
        examples=["2026-05-10"],
    ),
    actor_id: str | None = Query(
        default=None,
        description="Optional actor id to evaluate against campaign entitlement evidence.",
    ),
    active_on: str | None = Query(
        default=None,
        description="Optional ISO date used to classify discovery expiry posture.",
    ),
    escalation_tier: CampaignAssignmentEscalationTier | None = Query(
        default=None,
        description="Optional filter for one read-only escalation tier.",
    ),
    next_action: CampaignWorkflowNextAction | None = Query(
        default=None,
        description="Optional filter for one derived operator next action.",
    ),
    include_closed: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignAssignmentPlanPage:
    active_on_date = parse_optional_campaign_discovery_date(
        value=active_on,
        field_name="active_on",
    )
    definitions = repository.list_definitions(
        campaign_id=campaign_id,
        status=campaign_status,
        as_of_date=as_of_date,
        limit=limit,
        offset=offset,
    )
    return build_bulk_review_campaign_assignment_plan_page(
        definitions=definitions,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=active_on_date,
        include_closed=include_closed,
        escalation_tier=escalation_tier,
        next_action=next_action,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/campaign-workflow-automation",
    response_model=DpmBulkReviewCampaignWorkflowAutomationPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign workflow automation readiness",
    description=(
        "Returns read-only Manage-side workflow automation readiness over persisted "
        "`BulkReviewCampaignDefinition:v1` records. The projection composes the assignment plan "
        "with existing controlled assignment-task state to identify where Manage may safely "
        "propose opening, monitoring, or escalating its own assignment tasks. It does not mutate "
        "tasks, orchestrate external workflow, discover the global portfolio universe, "
        "recalculate source facts, mutate approval state, mutate maker-checker control state, "
        "contact clients, approve trades, generate orders, or claim OMS execution. The response "
        "includes `capability_posture` so consumers can distinguish supported Manage assignment "
        "readiness from unsupported external workflow orchestration even when the page is empty; "
        "that posture names blocked external workflow capabilities, the required future "
        "`ExternalWorkflowOrchestrationRecord:v1` source product, and a deterministic content hash."
    ),
)
def list_bulk_review_campaign_workflow_automation(
    campaign_id: str | None = Query(default=None),
    campaign_status: Literal["ACTIVE", "RETIRED", "SUPERSEDED"] | None = Query(default=None),
    as_of_date: str | None = Query(default=None),
    requested_as_of_date: str | None = Query(
        default=None,
        description=(
            "Optional ISO date to evaluate readiness and expiry. When omitted, each definition's "
            "persisted campaign as-of date is used."
        ),
        examples=["2026-05-10"],
    ),
    actor_id: str | None = Query(
        default=None,
        description="Optional actor id to evaluate against campaign entitlement evidence.",
    ),
    active_on: str | None = Query(
        default=None,
        description="Optional ISO date used to classify discovery expiry posture.",
    ),
    automation_status: CampaignWorkflowAutomationStatus | None = Query(
        default=None,
        description="Optional filter for one Manage-side automation posture.",
    ),
    automation_action: CampaignWorkflowAutomationAction | None = Query(
        default=None,
        description="Optional filter for one proposed Manage-side automation action.",
    ),
    include_closed: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignWorkflowAutomationPage:
    active_on_date = parse_optional_campaign_discovery_date(
        value=active_on,
        field_name="active_on",
    )
    definitions = repository.list_definitions(
        campaign_id=campaign_id,
        status=campaign_status,
        as_of_date=as_of_date,
        limit=limit,
        offset=offset,
    )
    return build_bulk_review_campaign_workflow_automation_page(
        definitions=definitions,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=active_on_date,
        include_closed=include_closed,
        automation_status=automation_status,
        automation_action=automation_action,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_200_OK,
    summary="Get bulk-review campaign definition",
    description="Retrieves one immutable Manage-owned bulk-review campaign definition.",
)
def get_bulk_review_campaign_definition(
    campaign_id: str,
    campaign_version: str,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    return definition


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/approval-decisions",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_201_CREATED,
    summary="Record bulk-review campaign approval decision",
    description=(
        "Records an append-only approval decision on one active Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. This mutates campaign approval evidence only: it "
        "does not run maker-checker workflow, approve trades, generate orders, route orders, "
        "contact clients, or claim OMS execution."
    ),
)
def record_bulk_review_campaign_definition_approval_decision_endpoint(
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionApprovalDecisionRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    try:
        updated = record_bulk_review_campaign_definition_approval_decision(
            definition=definition,
            decision_type=request.decision_type,
            decision_ref=request.decision_ref,
            decided_by=request.decided_by,
            decision_reason=request.decision_reason,
            correlation_id=request.correlation_id,
            source_refs=request.source_refs,
        )
        persisted = repository.record_definition_approval_decision(definition=updated)
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc
    if persisted is None:
        raise campaign_definition_not_found_http_exception()
    return persisted


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/approval-decisions",
    response_model=DpmBulkReviewCampaignDefinitionApprovalDecisionPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign approval decisions",
    description=(
        "Returns a bounded append-only approval-decision page for one persisted Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. The response summarizes approval posture without "
        "creating maker-checker workflow, trade approval, order generation, order routing, client "
        "contact, or OMS execution claims."
    ),
)
def list_bulk_review_campaign_definition_approval_decisions(
    campaign_id: str,
    campaign_version: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionApprovalDecisionPage:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    return build_bulk_review_campaign_definition_approval_decision_page(
        definition=definition,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-actions",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_201_CREATED,
    summary="Record bulk-review campaign assignment action",
    description=(
        "Records an append-only assignment or escalation action on one active Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. This mutates campaign assignment posture only: it "
        "does not mutate approval state, run maker-checker workflow, approve trades, generate "
        "orders, route orders, contact clients, or claim OMS execution."
    ),
)
def record_bulk_review_campaign_definition_assignment_action_endpoint(
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionAssignmentActionRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    try:
        updated = record_bulk_review_campaign_definition_assignment_action(
            definition=definition,
            action_type=request.action_type,
            action_ref=request.action_ref,
            recorded_by=request.recorded_by,
            action_reason=request.action_reason,
            assigned_actor_ids=request.assigned_actor_ids,
            escalation_tier=request.escalation_tier,
            sla_posture=request.sla_posture,
            correlation_id=request.correlation_id,
            source_refs=request.source_refs,
        )
        persisted = repository.record_definition_assignment_action(definition=updated)
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc
    if persisted is None:
        raise campaign_definition_not_found_http_exception()
    return persisted


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-actions",
    response_model=DpmBulkReviewCampaignDefinitionAssignmentActionPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign assignment actions",
    description=(
        "Returns a bounded append-only assignment-action page for one persisted Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. The response summarizes current assigned actors, "
        "escalation tier, and SLA posture without creating maker-checker workflow, mutating "
        "approval state, trade approval, order generation, order routing, client contact, or OMS "
        "execution claims."
    ),
)
def list_bulk_review_campaign_definition_assignment_actions(
    campaign_id: str,
    campaign_version: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionAssignmentActionPage:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    return build_bulk_review_campaign_definition_assignment_action_page(
        definition=definition,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_201_CREATED,
    summary="Open bulk-review campaign assignment task",
    description=(
        "Opens a controlled Manage-side assignment or escalation task on one active "
        "`BulkReviewCampaignDefinition:v1`. The task lifecycle mutates assignment task state "
        "only and retains append-only transition evidence; it does not mutate approval state, "
        "run maker-checker workflow, approve trades, generate orders, route orders, contact "
        "clients, orchestrate external workflow systems, or claim OMS execution."
    ),
)
def open_bulk_review_campaign_definition_assignment_task_endpoint(
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionAssignmentTaskOpenRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    try:
        updated = open_bulk_review_campaign_definition_assignment_task(
            definition=definition,
            task_ref=request.task_ref,
            task_type=request.task_type,
            opened_by=request.opened_by,
            task_reason=request.task_reason,
            assigned_actor_ids=request.assigned_actor_ids,
            escalation_tier=request.escalation_tier,
            sla_posture=request.sla_posture,
            due_at=request.due_at,
            correlation_id=request.correlation_id,
            source_refs=request.source_refs,
        )
        persisted = repository.record_definition_assignment_task(definition=updated)
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc
    if persisted is None:
        raise campaign_definition_not_found_http_exception()
    return persisted


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks/{task_ref}/transitions",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_201_CREATED,
    summary="Transition bulk-review campaign assignment task",
    description=(
        "Records a controlled transition for one Manage-side assignment task and updates its "
        "current task state. Transitions are conflict-safe by transition ref and retain an "
        "append-only ledger without mutating approval state, approving trades, generating or "
        "routing orders, contacting clients, orchestrating external workflow systems, or claiming "
        "OMS execution."
    ),
)
def transition_bulk_review_campaign_definition_assignment_task_endpoint(
    campaign_id: str,
    campaign_version: str,
    task_ref: str,
    request: DpmBulkReviewCampaignDefinitionAssignmentTaskTransitionRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    try:
        updated = transition_bulk_review_campaign_definition_assignment_task(
            definition=definition,
            task_ref=task_ref,
            transition_type=request.transition_type,
            transition_ref=request.transition_ref,
            transitioned_by=request.transitioned_by,
            transition_reason=request.transition_reason,
            assigned_actor_ids=request.assigned_actor_ids,
            escalation_tier=request.escalation_tier,
            sla_posture=request.sla_posture,
            due_at=request.due_at,
            correlation_id=request.correlation_id,
            source_refs=request.source_refs,
        )
        persisted = repository.record_definition_assignment_task(definition=updated)
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc
    if persisted is None:
        raise campaign_definition_not_found_http_exception()
    return persisted


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks",
    response_model=DpmBulkReviewCampaignDefinitionAssignmentTaskPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign assignment tasks",
    description=(
        "Returns a bounded page of controlled Manage-side assignment and escalation tasks for one "
        "persisted `BulkReviewCampaignDefinition:v1`. The response summarizes current status, "
        "escalation, and SLA posture without creating maker-checker workflow, mutating approval "
        "state, trade approval, order generation, order routing, client contact, external "
        "workflow orchestration, or OMS execution claims."
    ),
)
def list_bulk_review_campaign_definition_assignment_tasks(
    campaign_id: str,
    campaign_version: str,
    status: CampaignAssignmentTaskStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionAssignmentTaskPage:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    return build_bulk_review_campaign_definition_assignment_task_page(
        definition=definition,
        status_filter=status,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/maker-checker-controls",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_201_CREATED,
    summary="Record bulk-review campaign maker-checker control",
    description=(
        "Records append-only maker-checker control evidence on one active Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. Completed reviews require distinct submitter and "
        "reviewer actors. This evidence does not approve trades, generate orders, route orders, "
        "contact clients, orchestrate external workflow systems, or claim OMS execution."
    ),
)
def record_bulk_review_campaign_definition_maker_checker_control_endpoint(
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionMakerCheckerControlRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    try:
        updated = record_bulk_review_campaign_definition_maker_checker_control(
            definition=definition,
            control_action=request.control_action,
            control_ref=request.control_ref,
            recorded_by=request.recorded_by,
            submitter_actor_id=request.submitter_actor_id,
            reviewer_actor_id=request.reviewer_actor_id,
            required_reviewer_role=request.required_reviewer_role,
            control_outcome=request.control_outcome,
            control_reason=request.control_reason,
            correlation_id=request.correlation_id,
            source_refs=request.source_refs,
        )
        persisted = repository.record_definition_maker_checker_control(definition=updated)
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc
    if persisted is None:
        raise campaign_definition_not_found_http_exception()
    return persisted


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/maker-checker-controls",
    response_model=DpmBulkReviewCampaignDefinitionMakerCheckerControlPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign maker-checker controls",
    description=(
        "Returns a bounded append-only maker-checker control page for one persisted Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. The response summarizes current control posture "
        "without trade approval, order generation, order routing, client contact, external "
        "workflow orchestration, or OMS execution claims."
    ),
)
def list_bulk_review_campaign_definition_maker_checker_controls(
    campaign_id: str,
    campaign_version: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionMakerCheckerControlPage:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    return build_bulk_review_campaign_definition_maker_checker_control_page(
        definition=definition,
        limit=limit,
        offset=offset,
    )


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
    campaign_id: str,
    campaign_version: str,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionLifecycleEventPage:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    return build_bulk_review_campaign_definition_lifecycle_events(definition=definition)


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
    campaign_id: str,
    campaign_version: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionLaunchHistoryPage:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    return build_bulk_review_campaign_definition_launch_history_page(
        definition=definition,
        limit=limit,
        offset=offset,
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
    campaign_id: str,
    campaign_version: str,
    requested_as_of_date: str = Query(
        description="ISO date that the future wave preview/create request would use.",
        examples=["2026-05-10"],
    ),
    actor_id: str | None = Query(
        default=None,
        description="Optional actor id to evaluate against campaign entitlement evidence.",
    ),
    active_on: str | None = Query(
        default=None,
        description="Optional ISO date used to classify campaign expiry posture.",
    ),
    include_launch_package: bool = Query(
        default=True,
        description=(
            "When true, include launch package guidance if preview readiness is READY and actor_id "
            "is supplied."
        ),
    ),
    correlation_id: str | None = Query(
        default=None,
        description="Optional correlation id to carry into launch package guidance.",
    ),
    launch_history_limit: int = Query(default=20, ge=1, le=200),
    launch_history_offset: int = Query(default=0, ge=0),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionWorkflowOverview:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    active_on_date = parse_optional_campaign_discovery_date(
        value=active_on,
        field_name="active_on",
    )
    return build_bulk_review_campaign_definition_workflow_overview(
        definition=definition,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=active_on_date,
        launch_history_limit=launch_history_limit,
        launch_history_offset=launch_history_offset,
        include_launch_package=include_launch_package,
        correlation_id=correlation_id,
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
    campaign_id: str,
    campaign_version: str,
    requested_as_of_date: str = Query(
        description="ISO date that the future wave preview/create request would use.",
        examples=["2026-05-10"],
    ),
    actor_id: str | None = Query(
        default=None,
        description="Optional actor id to evaluate against campaign entitlement evidence.",
    ),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionPreviewReadiness:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    return build_bulk_review_campaign_definition_preview_readiness(
        definition=definition,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
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
    campaign_id: str,
    campaign_version: str,
    requested_as_of_date: str = Query(
        description="ISO date that the future wave preview/create request would use.",
        examples=["2026-05-10"],
    ),
    actor_id: str = Query(
        description="Actor id to place in the preview/create request draft.",
        examples=["pm_001"],
    ),
    correlation_id: str | None = Query(
        default=None,
        description="Optional correlation id to carry into the create header draft.",
    ),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionLaunchPackage:
    definition = get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    return build_bulk_review_campaign_definition_launch_package(
        definition=definition,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        correlation_id=correlation_id,
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
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionLaunchRequest,
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmWaveResponse:
    definition = get_campaign_definition_or_404(
        repository=campaign_definition_repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    try:
        launch_command = build_bulk_review_campaign_definition_launch_command(
            definition=definition,
            requested_as_of_date=request.requested_as_of_date,
            actor_id=request.actor_id,
            correlation_id=request.correlation_id,
        )
    except DpmBulkReviewCampaignDefinitionLaunchBlocked as exc:
        raise campaign_definition_launch_blocked_http_exception(exc) from exc
    wave_request = DpmWavePreviewRequest.model_validate(
        launch_command.create_request.model_dump(mode="json")
    )
    try:
        portfolios = resolve_portfolio_inputs_for_request(
            request=wave_request,
            correlation_id=launch_command.correlation_id,
            advise_authority_client=None,
            risk_authority_client=None,
            campaign_definition_repository=campaign_definition_repository,
            core_resolver_factory=build_core_resolver_client,
        )
        wave, replay = wave_service.create_wave(
            trigger_type=wave_request.trigger_type,
            trigger_id=wave_request.trigger_id,
            rationale=wave_request.rationale,
            as_of_date=wave_request.as_of_date,
            actor_id=wave_request.actor_id,
            correlation_id=launch_command.correlation_id,
            portfolios=portfolios,
            idempotency_key=launch_command.idempotency_key,
            mandate_repository=mandate_repository,
            wave_repository=wave_repository,
        )
        launched_definition = record_bulk_review_campaign_definition_launch(
            definition=definition,
            wave_id=wave.wave_id,
            launched_by=wave_request.actor_id,
            requested_as_of_date=wave_request.as_of_date,
            correlation_id=launch_command.correlation_id,
            idempotency_key=launch_command.idempotency_key,
        )
        if launched_definition.content_hash != definition.content_hash:
            campaign_definition_repository.record_definition_launch(definition=launched_definition)
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc, conflict_codes=()) from exc
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(
            exc,
            message="Bulk-review campaign definition launch audit could not be recorded.",
        ) from exc
    return wave_response(wave=wave, durable=True, idempotent_replay=replay)


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
        "`BulkReviewCampaignMembership:v1` envelope from source-backed candidate portfolios and "
        "DPM portfolio-type filters. Unsupported trigger types remain blocked; the endpoint does "
        "not recompute house-view, holdings, risk, performance, simulation, approval, staging, or "
        "operations handoff."
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
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.", examples=["corr-wave-001"]
        ),
    ] = None,
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
    try:
        portfolios = resolve_portfolio_inputs_for_request(
            request=request,
            correlation_id=correlation_id,
            advise_authority_client=advise_authority_client,
            risk_authority_client=risk_authority_client,
            campaign_definition_repository=campaign_definition_repository,
            core_resolver_factory=build_core_resolver_client,
        )
        wave = wave_service.preview_wave(
            trigger_type=request.trigger_type,
            trigger_id=request.trigger_id,
            rationale=request.rationale,
            as_of_date=request.as_of_date,
            actor_id=request.actor_id,
            correlation_id=correlation_id,
            portfolios=portfolios,
            mandate_repository=mandate_repository,
        )
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc, conflict_codes=()) from exc
    return wave_response(wave=wave, durable=False)


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
        "a Manage-owned campaign membership wave from source-backed candidates. Required header: "
        "`Idempotency-Key`. Unsupported trigger types are rejected and missing source evidence "
        "produces blocked items, not false readiness."
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
    idempotency_key: Annotated[
        str,
        Header(
            description="Required idempotency token for durable wave create.",
            examples=["wave-idem-001"],
        ),
    ],
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.", examples=["corr-wave-001"]
        ),
    ] = None,
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
    try:
        portfolios = resolve_portfolio_inputs_for_request(
            request=request,
            correlation_id=correlation_id,
            advise_authority_client=advise_authority_client,
            risk_authority_client=risk_authority_client,
            campaign_definition_repository=campaign_definition_repository,
            core_resolver_factory=build_core_resolver_client,
        )
        wave, replayed = wave_service.create_wave(
            trigger_type=request.trigger_type,
            trigger_id=request.trigger_id,
            rationale=request.rationale,
            as_of_date=request.as_of_date,
            actor_id=request.actor_id,
            correlation_id=correlation_id,
            portfolios=portfolios,
            idempotency_key=idempotency_key,
            mandate_repository=mandate_repository,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc, conflict_codes=("WAVE_CREATE_CONFLICT",)) from exc
    return wave_response(wave=wave, durable=True, idempotent_replay=replayed)


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
    items = wave_service.search_waves(
        wave_repository=wave_repository,
        state=state,
        trigger_type=trigger_type,
        as_of_date=as_of_date,
        supportability_state=supportability_state,
        limit=limit,
        offset=offset,
    )
    return DpmWaveSearchResponse(
        items=[DpmWaveSearchItem.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
        returned_count=len(items),
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
    wave_id: str,
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
    wave_id: str,
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
    wave_id: str,
    request: DpmWaveSourceCheckRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-source-check-001"],
        ),
    ] = None,
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    try:
        wave, replayed = wave_service.source_check_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            correlation_id=x_correlation_id or f"corr_wave_source_check_{wave_id}",
            mandate_repository=mandate_repository,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc) from exc
    return wave_response(wave=wave, durable=True, idempotent_replay=replayed)


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
    wave_id: str,
    request: DpmWaveSimulationRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-simulate-001"],
        ),
    ] = None,
    construction_repository: ConstructionRepository = Depends(get_construction_repository),
    risk_authority_client: LotusRiskAuthorityClient | None = Depends(get_risk_authority_client),
    run_service: DpmRunSupportService = Depends(get_dpm_run_support_service),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    item_inputs: dict[str, RebalanceRequest | wave_service.DpmWaveSimulationInput] = {}
    for item_input in request.item_inputs:
        simulation_input = wave_service.DpmWaveSimulationInput(
            stateless_input=item_input.stateless_input,
            authority_context=item_input.authority_context,
        )
        if item_input.wave_item_id:
            item_inputs[item_input.wave_item_id] = simulation_input
        if item_input.portfolio_id:
            item_inputs[item_input.portfolio_id] = simulation_input
    try:
        wave, replayed = wave_service.simulate_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            correlation_id=x_correlation_id or f"corr_wave_simulate_{wave_id}",
            item_inputs=item_inputs,
            methods=request.methods,
            construction_repository=construction_repository,
            run_service=run_service,
            wave_repository=wave_repository,
            risk_authority_client=risk_authority_client,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc) from exc
    return wave_response(wave=wave, durable=True, idempotent_replay=replayed)


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
    wave_id: str,
    wave_item_id: str,
    request: DpmWaveSelectionRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-select-001"],
        ),
    ] = None,
    construction_repository: ConstructionRepository = Depends(get_construction_repository),
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    run_service: DpmRunSupportService = Depends(get_dpm_run_support_service),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    try:
        wave = wave_service.select_wave_item_alternative(
            wave_id=wave_id,
            wave_item_id=wave_item_id,
            alternative_id=request.alternative_id,
            actor_id=request.actor_id,
            reason_code=request.reason_code,
            comment=request.comment,
            correlation_id=x_correlation_id or f"corr_wave_select_{wave_id}_{wave_item_id}",
            generate_proof_pack=request.generate_proof_pack,
            construction_repository=construction_repository,
            proof_pack_repository=proof_pack_repository,
            mandate_repository=mandate_repository,
            run_service=run_service,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc) from exc
    return wave_response(wave=wave, durable=True)


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
    wave_id: str,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-approve-001"],
        ),
    ] = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    try:
        wave, replayed = wave_service.approve_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            reason_code=request.reason_code,
            comment=request.comment,
            correlation_id=x_correlation_id or f"corr_wave_approve_{wave_id}",
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc) from exc
    return wave_response(wave=wave, durable=True, idempotent_replay=replayed)


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
    wave_id: str,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-stage-001"],
        ),
    ] = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    try:
        wave, replayed = wave_service.stage_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            reason_code=request.reason_code,
            comment=request.comment,
            correlation_id=x_correlation_id or f"corr_wave_stage_{wave_id}",
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc) from exc
    return wave_response(wave=wave, durable=True, idempotent_replay=replayed)


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
    wave_id: str,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-handoff-001"],
        ),
    ] = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    try:
        wave, replayed = wave_service.handoff_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            reason_code=request.reason_code,
            comment=request.comment,
            correlation_id=x_correlation_id or f"corr_wave_handoff_{wave_id}",
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc) from exc
    return wave_response(wave=wave, durable=True, idempotent_replay=replayed)


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
    wave_id: str,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-cancel-001"],
        ),
    ] = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    try:
        wave, replayed = wave_service.cancel_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            reason_code=request.reason_code,
            comment=request.comment,
            correlation_id=x_correlation_id or f"corr_wave_cancel_{wave_id}",
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc) from exc
    return wave_response(wave=wave, durable=True, idempotent_replay=replayed)


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
    wave_id: str,
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
    wave_id: str,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    outcome_review_repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmWaveReportInput:
    try:
        return wave_service.get_report_input(
            wave_id=wave_id,
            wave_repository=wave_repository,
            proof_pack_repository=proof_pack_repository,
            outcome_review_repository=outcome_review_repository,
            mandate_repository=mandate_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc) from exc


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
    wave_id: str,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveSupportabilityResponse:
    return get_wave_supportability_response(
        wave_id=wave_id,
        wave_repository=wave_repository,
        logger=logger,
    )
