from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_campaign_definition_repository
from src.api.routers.wave_campaign_approval_decision_evidence_routes import (
    router as approval_decision_router,
)
from src.api.routers.wave_campaign_action_http import (
    list_campaign_definition_assignment_actions_response,
    list_campaign_definition_assignment_tasks_response,
    list_campaign_definition_maker_checker_controls_response,
    open_campaign_definition_assignment_task_response,
    record_campaign_definition_assignment_action_response,
    record_campaign_definition_maker_checker_control_response,
    transition_campaign_definition_assignment_task_response,
)
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionAssignmentActionRequest,
    DpmBulkReviewCampaignDefinitionAssignmentTaskOpenRequest,
    DpmBulkReviewCampaignDefinitionAssignmentTaskTransitionRequest,
    DpmBulkReviewCampaignDefinitionMakerCheckerControlRequest,
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
    DpmBulkReviewCampaignDefinitionAssignmentActionPage,
    DpmBulkReviewCampaignDefinitionAssignmentTaskPage,
    DpmBulkReviewCampaignDefinitionMakerCheckerControlPage,
    DpmBulkReviewCampaignDefinitionRepository,
)


router = APIRouter(tags=["lotus-manage Rebalance Waves"])
router.include_router(approval_decision_router)


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
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    request: DpmBulkReviewCampaignDefinitionAssignmentActionRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    return record_campaign_definition_assignment_action_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        request=request,
        repository=repository,
    )


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
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    limit: CampaignEvidenceLimitQuery = 50,
    offset: CampaignEvidenceOffsetQuery = 0,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionAssignmentActionPage:
    return list_campaign_definition_assignment_actions_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        limit=limit,
        offset=offset,
        repository=repository,
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
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    request: DpmBulkReviewCampaignDefinitionAssignmentTaskOpenRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    return open_campaign_definition_assignment_task_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        request=request,
        repository=repository,
    )


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
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    task_ref: CampaignAssignmentTaskRefPath,
    request: DpmBulkReviewCampaignDefinitionAssignmentTaskTransitionRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    return transition_campaign_definition_assignment_task_response(
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
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionAssignmentTaskPage:
    return list_campaign_definition_assignment_tasks_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        status=status,
        limit=limit,
        offset=offset,
        repository=repository,
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
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    request: DpmBulkReviewCampaignDefinitionMakerCheckerControlRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    return record_campaign_definition_maker_checker_control_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        request=request,
        repository=repository,
    )


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
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    limit: CampaignEvidenceLimitQuery = 50,
    offset: CampaignEvidenceOffsetQuery = 0,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionMakerCheckerControlPage:
    return list_campaign_definition_maker_checker_controls_response(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
        limit=limit,
        offset=offset,
        repository=repository,
    )
