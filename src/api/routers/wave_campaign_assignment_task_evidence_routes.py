from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_wave_campaign_application_service
from src.api.routers.wave_campaign_definition_errors import (
    campaign_definition_conflict_http_exception,
    campaign_definition_evidence_value_http_exception,
    campaign_definition_not_found_http_exception,
)
from src.api.routers.wave_campaign_problem_details import campaign_problem_responses
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
from src.api.routers.wave_campaign_workflow_telemetry import (
    campaign_workflow_http_exception,
    record_campaign_workflow_success,
    record_campaign_workflow_unexpected_error,
)
from src.api.services.wave_campaign_application import (
    DpmCampaignDefinitionAssignmentTaskOpenCommand,
    DpmCampaignDefinitionAssignmentTaskTransitionCommand,
    DpmWaveCampaignApplicationNotFoundError,
    DpmWaveCampaignApplicationService,
)
from src.core.waves import (
    CampaignAssignmentTaskStatus,
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionAssignmentTaskPage,
    DpmBulkReviewCampaignDefinitionConflictError,
)

router = APIRouter()


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_201_CREATED,
    responses=campaign_problem_responses(
        {
            404: "Campaign definition not found.",
            409: "Assignment task reference conflict.",
            422: "Assignment task semantic validation failed.",
        }
    ),
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
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmBulkReviewCampaignDefinition:
    surface = "assignment_task_open"
    try:
        result = application_service.open_campaign_definition_assignment_task(
            command=DpmCampaignDefinitionAssignmentTaskOpenCommand(
                tenant_id=trusted_context.tenant_id,
                campaign_id=campaign_id,
                campaign_version=campaign_version,
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
        )
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        http_exc = campaign_definition_conflict_http_exception(exc)
        raise campaign_workflow_http_exception(surface=surface, exc=http_exc) from exc
    except DpmWaveCampaignApplicationNotFoundError as exc:
        raise campaign_workflow_http_exception(
            surface=surface,
            exc=campaign_definition_not_found_http_exception(),
        ) from exc
    except ValueError as exc:
        http_exc = campaign_definition_evidence_value_http_exception(exc)
        raise campaign_workflow_http_exception(surface=surface, exc=http_exc) from exc
    except Exception:
        record_campaign_workflow_unexpected_error(surface=surface)
        raise
    record_campaign_workflow_success(surface=surface, replay=result.replay)
    return result.definition


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks/{task_ref}/transitions",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_201_CREATED,
    responses=campaign_problem_responses(
        {
            404: "Campaign definition or assignment task not found.",
            409: "Assignment task transition reference conflict.",
            422: "Assignment task transition semantic validation failed.",
        }
    ),
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
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmBulkReviewCampaignDefinition:
    surface = "assignment_task_transition"
    try:
        result = application_service.transition_campaign_definition_assignment_task(
            command=DpmCampaignDefinitionAssignmentTaskTransitionCommand(
                tenant_id=trusted_context.tenant_id,
                campaign_id=campaign_id,
                campaign_version=campaign_version,
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
        )
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        http_exc = campaign_definition_conflict_http_exception(exc)
        raise campaign_workflow_http_exception(surface=surface, exc=http_exc) from exc
    except DpmWaveCampaignApplicationNotFoundError as exc:
        raise campaign_workflow_http_exception(
            surface=surface,
            exc=campaign_definition_not_found_http_exception(),
        ) from exc
    except ValueError as exc:
        http_exc = campaign_definition_evidence_value_http_exception(exc)
        raise campaign_workflow_http_exception(surface=surface, exc=http_exc) from exc
    except Exception:
        record_campaign_workflow_unexpected_error(surface=surface)
        raise
    record_campaign_workflow_success(surface=surface, replay=result.replay)
    return result.definition


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
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmBulkReviewCampaignDefinitionAssignmentTaskPage:
    try:
        return application_service.list_campaign_definition_assignment_tasks(
            tenant_id=trusted_context.tenant_id,
            campaign_id=campaign_id,
            campaign_version=campaign_version,
            status=status,
            limit=limit,
            offset=offset,
        )
    except DpmWaveCampaignApplicationNotFoundError as exc:
        raise campaign_definition_not_found_http_exception() from exc
