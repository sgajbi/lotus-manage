from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_campaign_definition_repository
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
    CampaignWorkflowAutomationAction,
    CampaignWorkflowAutomationStatus,
    DpmBulkReviewCampaignDefinitionRepository,
    DpmBulkReviewCampaignWorkflowAutomationPage,
    build_bulk_review_campaign_workflow_automation_page,
)

router = APIRouter()


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
