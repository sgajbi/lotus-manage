from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_campaign_definition_repository
from src.api.routers.wave_campaign_assignment_task_http import (
    list_campaign_definition_assignment_tasks_response,
    open_campaign_definition_assignment_task_response,
    transition_campaign_definition_assignment_task_response,
)
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionAssignmentTaskOpenRequest,
    DpmBulkReviewCampaignDefinitionAssignmentTaskTransitionRequest,
)
from src.api.routers.wave_campaign_trusted_context import (
    CampaignTrustedContext,
    campaign_trusted_context_required,
)
from src.api.routers.wave_route_parameters import (
    CampaignAssignmentTaskRefPath,
    CampaignDefinitionIdPath,
    CampaignDefinitionVersionPath,
    CampaignEvidenceLimitQuery,
    CampaignEvidenceOffsetQuery,
)
from src.core.waves import (
    CampaignAssignmentTaskStatus,
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionAssignmentTaskPage,
    DpmBulkReviewCampaignDefinitionRepository,
)

router = APIRouter()


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Campaign definition not found."},
        409: {"description": "Assignment task reference conflict."},
        422: {"description": "Assignment task semantic validation failed."},
    },
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
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    request: DpmBulkReviewCampaignDefinitionAssignmentTaskOpenRequest,
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    return open_campaign_definition_assignment_task_response(
        tenant_id=trusted_context.tenant_id,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        request=request,
        repository=repository,
    )


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks/{task_ref}/transitions",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Campaign definition or assignment task not found."},
        409: {"description": "Assignment task transition reference conflict."},
        422: {"description": "Assignment task transition semantic validation failed."},
    },
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
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    task_ref: CampaignAssignmentTaskRefPath,
    request: DpmBulkReviewCampaignDefinitionAssignmentTaskTransitionRequest,
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    return transition_campaign_definition_assignment_task_response(
        tenant_id=trusted_context.tenant_id,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        task_ref=task_ref,
        request=request,
        repository=repository,
    )


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
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    status: CampaignAssignmentTaskStatus | None = Query(default=None),
    limit: CampaignEvidenceLimitQuery = 50,
    offset: CampaignEvidenceOffsetQuery = 0,
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionAssignmentTaskPage:
    return list_campaign_definition_assignment_tasks_response(
        tenant_id=trusted_context.tenant_id,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        status=status,
        limit=limit,
        offset=offset,
        repository=repository,
    )
