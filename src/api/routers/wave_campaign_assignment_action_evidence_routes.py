from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_wave_campaign_application_service
from src.api.routers.wave_campaign_definition_errors import (
    campaign_definition_conflict_http_exception,
    campaign_definition_evidence_value_http_exception,
    campaign_definition_not_found_http_exception,
)
from src.api.routers.wave_campaign_problem_details import campaign_problem_responses
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionAssignmentActionRequest,
)
from src.api.routers.wave_campaign_trusted_context import (
    CampaignTrustedContext,
    campaign_trusted_context_required,
)
from src.api.routers.wave_route_parameters import (
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
    DpmCampaignDefinitionAssignmentActionCommand,
    DpmWaveCampaignApplicationNotFoundError,
    DpmWaveCampaignApplicationService,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionAssignmentActionPage,
    DpmBulkReviewCampaignDefinitionConflictError,
)

router = APIRouter()


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-actions",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_201_CREATED,
    responses=campaign_problem_responses(
        {
            404: "Campaign definition not found.",
            409: "Assignment action reference conflict.",
            422: "Assignment action semantic validation failed.",
        }
    ),
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
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmBulkReviewCampaignDefinition:
    surface = "assignment_action"
    try:
        result = application_service.record_campaign_definition_assignment_action(
            command=DpmCampaignDefinitionAssignmentActionCommand(
                tenant_id=trusted_context.tenant_id,
                campaign_id=campaign_id,
                campaign_version=campaign_version,
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
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmBulkReviewCampaignDefinitionAssignmentActionPage:
    try:
        return application_service.list_campaign_definition_assignment_actions(
            tenant_id=trusted_context.tenant_id,
            campaign_id=campaign_id,
            campaign_version=campaign_version,
            limit=limit,
            offset=offset,
        )
    except DpmWaveCampaignApplicationNotFoundError as exc:
        raise campaign_definition_not_found_http_exception() from exc
