from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_campaign_definition_repository
from src.api.routers.wave_campaign_discovery_routes import router as discovery_router
from src.api.routers.wave_campaign_operating_queue_routes import (
    router as operating_queue_router,
)
from src.api.routers.wave_campaign_read_model_query import load_campaign_read_model_query
from src.api.routers.wave_route_parameters import (
    CampaignActiveOnQuery,
    CampaignActorIdQuery,
    CampaignDefinitionAsOfDateQuery,
    CampaignDefinitionFilterIdQuery,
    CampaignDefinitionStatusQuery,
    CampaignIncludeClosedQuery,
    CampaignReadModelLimitQuery,
    CampaignReadModelOffsetQuery,
    CampaignRequestedAsOfDateQuery,
)
from src.core.waves import (
    CampaignApprovalInboxStatus,
    CampaignAssignmentEscalationTier,
    CampaignWorkflowAutomationAction,
    CampaignWorkflowAutomationStatus,
    CampaignWorkflowBoardStatus,
    CampaignWorkflowNextAction,
    DpmBulkReviewCampaignApprovalInboxPage,
    DpmBulkReviewCampaignAssignmentPlanPage,
    DpmBulkReviewCampaignDefinitionRepository,
    DpmBulkReviewCampaignWorkflowAutomationPage,
    DpmBulkReviewCampaignWorkflowBoardPage,
    build_bulk_review_campaign_approval_inbox_page,
    build_bulk_review_campaign_assignment_plan_page,
    build_bulk_review_campaign_workflow_automation_page,
    build_bulk_review_campaign_workflow_board_page,
)


router = APIRouter(tags=["lotus-manage Rebalance Waves"])


router.include_router(discovery_router)
router.include_router(operating_queue_router)


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
    campaign_id: CampaignDefinitionFilterIdQuery = None,
    campaign_status: CampaignDefinitionStatusQuery = None,
    as_of_date: CampaignDefinitionAsOfDateQuery = None,
    requested_as_of_date: CampaignRequestedAsOfDateQuery = None,
    actor_id: CampaignActorIdQuery = None,
    active_on: CampaignActiveOnQuery = None,
    inbox_status: CampaignApprovalInboxStatus | None = Query(
        default=None,
        description="Optional filter for one approval attention posture.",
    ),
    include_closed: CampaignIncludeClosedQuery = False,
    limit: CampaignReadModelLimitQuery = 50,
    offset: CampaignReadModelOffsetQuery = 0,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignApprovalInboxPage:
    campaign_query = load_campaign_read_model_query(
        repository=repository,
        campaign_id=campaign_id,
        campaign_status=campaign_status,
        as_of_date=as_of_date,
        active_on=active_on,
        limit=limit,
        offset=offset,
    )
    return build_bulk_review_campaign_approval_inbox_page(
        definitions=campaign_query.definitions,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=campaign_query.active_on,
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
    campaign_id: CampaignDefinitionFilterIdQuery = None,
    campaign_status: CampaignDefinitionStatusQuery = None,
    as_of_date: CampaignDefinitionAsOfDateQuery = None,
    requested_as_of_date: CampaignRequestedAsOfDateQuery = None,
    actor_id: CampaignActorIdQuery = None,
    active_on: CampaignActiveOnQuery = None,
    board_status: CampaignWorkflowBoardStatus | None = Query(
        default=None,
        description="Optional filter for one workflow-board posture.",
    ),
    next_action: CampaignWorkflowNextAction | None = Query(
        default=None,
        description="Optional filter for one derived operator next action.",
    ),
    include_closed: CampaignIncludeClosedQuery = False,
    limit: CampaignReadModelLimitQuery = 50,
    offset: CampaignReadModelOffsetQuery = 0,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignWorkflowBoardPage:
    campaign_query = load_campaign_read_model_query(
        repository=repository,
        campaign_id=campaign_id,
        campaign_status=campaign_status,
        as_of_date=as_of_date,
        active_on=active_on,
        limit=limit,
        offset=offset,
    )
    return build_bulk_review_campaign_workflow_board_page(
        definitions=campaign_query.definitions,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=campaign_query.active_on,
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
    campaign_id: CampaignDefinitionFilterIdQuery = None,
    campaign_status: CampaignDefinitionStatusQuery = None,
    as_of_date: CampaignDefinitionAsOfDateQuery = None,
    requested_as_of_date: CampaignRequestedAsOfDateQuery = None,
    actor_id: CampaignActorIdQuery = None,
    active_on: CampaignActiveOnQuery = None,
    escalation_tier: CampaignAssignmentEscalationTier | None = Query(
        default=None,
        description="Optional filter for one read-only escalation tier.",
    ),
    next_action: CampaignWorkflowNextAction | None = Query(
        default=None,
        description="Optional filter for one derived operator next action.",
    ),
    include_closed: CampaignIncludeClosedQuery = False,
    limit: CampaignReadModelLimitQuery = 50,
    offset: CampaignReadModelOffsetQuery = 0,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignAssignmentPlanPage:
    campaign_query = load_campaign_read_model_query(
        repository=repository,
        campaign_id=campaign_id,
        campaign_status=campaign_status,
        as_of_date=as_of_date,
        active_on=active_on,
        limit=limit,
        offset=offset,
    )
    return build_bulk_review_campaign_assignment_plan_page(
        definitions=campaign_query.definitions,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=campaign_query.active_on,
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
        "`ExternalWorkflowOrchestrationRecord:v1` source product, promotion requirements for "
        "future source-owner/downstream realization, and a deterministic content hash."
    ),
)
def list_bulk_review_campaign_workflow_automation(
    campaign_id: CampaignDefinitionFilterIdQuery = None,
    campaign_status: CampaignDefinitionStatusQuery = None,
    as_of_date: CampaignDefinitionAsOfDateQuery = None,
    requested_as_of_date: CampaignRequestedAsOfDateQuery = None,
    actor_id: CampaignActorIdQuery = None,
    active_on: CampaignActiveOnQuery = None,
    automation_status: CampaignWorkflowAutomationStatus | None = Query(
        default=None,
        description="Optional filter for one Manage-side automation posture.",
    ),
    automation_action: CampaignWorkflowAutomationAction | None = Query(
        default=None,
        description="Optional filter for one proposed Manage-side automation action.",
    ),
    include_closed: CampaignIncludeClosedQuery = False,
    limit: CampaignReadModelLimitQuery = 50,
    offset: CampaignReadModelOffsetQuery = 0,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignWorkflowAutomationPage:
    campaign_query = load_campaign_read_model_query(
        repository=repository,
        campaign_id=campaign_id,
        campaign_status=campaign_status,
        as_of_date=as_of_date,
        active_on=active_on,
        limit=limit,
        offset=offset,
    )
    return build_bulk_review_campaign_workflow_automation_page(
        definitions=campaign_query.definitions,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=campaign_query.active_on,
        include_closed=include_closed,
        automation_status=automation_status,
        automation_action=automation_action,
        limit=limit,
        offset=offset,
    )
