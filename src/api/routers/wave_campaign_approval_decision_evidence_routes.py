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
    DpmBulkReviewCampaignDefinitionApprovalDecisionRequest,
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
    DpmCampaignDefinitionApprovalDecisionCommand,
    DpmWaveCampaignApplicationNotFoundError,
    DpmWaveCampaignApplicationService,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionApprovalDecisionPage,
    DpmBulkReviewCampaignDefinitionConflictError,
)

router = APIRouter()


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/approval-decisions",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_201_CREATED,
    responses=campaign_problem_responses(
        {
            404: "Campaign definition not found.",
            409: "Approval decision reference conflict.",
            422: "Approval decision semantic validation failed.",
        }
    ),
    summary="Record bulk-review campaign approval decision",
    description=(
        "Records an append-only approval decision on one active Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. This mutates campaign approval evidence only: it "
        "does not run maker-checker workflow, approve trades, generate orders, route orders, "
        "contact clients, or claim OMS execution."
    ),
)
def record_bulk_review_campaign_definition_approval_decision_endpoint(
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    request: DpmBulkReviewCampaignDefinitionApprovalDecisionRequest,
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmBulkReviewCampaignDefinition:
    surface = "approval_decision"
    try:
        result = application_service.record_campaign_definition_approval_decision(
            command=DpmCampaignDefinitionApprovalDecisionCommand(
                tenant_id=trusted_context.tenant_id,
                campaign_id=campaign_id,
                campaign_version=campaign_version,
                decision_type=request.decision_type,
                decision_ref=request.decision_ref,
                decided_by=request.decided_by,
                decision_reason=request.decision_reason,
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
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    limit: CampaignEvidenceLimitQuery = 50,
    offset: CampaignEvidenceOffsetQuery = 0,
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmBulkReviewCampaignDefinitionApprovalDecisionPage:
    try:
        return application_service.list_campaign_definition_approval_decisions(
            tenant_id=trusted_context.tenant_id,
            campaign_id=campaign_id,
            campaign_version=campaign_version,
            limit=limit,
            offset=offset,
        )
    except DpmWaveCampaignApplicationNotFoundError as exc:
        raise campaign_definition_not_found_http_exception() from exc
