from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_wave_campaign_application_service
from src.api.routers.wave_campaign_definition_errors import (
    campaign_definition_conflict_http_exception,
    campaign_definition_evidence_value_http_exception,
    campaign_definition_not_found_http_exception,
)
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionMakerCheckerControlRequest,
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
    DpmCampaignDefinitionMakerCheckerControlCommand,
    DpmWaveCampaignApplicationNotFoundError,
    DpmWaveCampaignApplicationService,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmBulkReviewCampaignDefinitionMakerCheckerControlPage,
)

router = APIRouter()


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/maker-checker-controls",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Campaign definition not found."},
        409: {"description": "Maker-checker control reference conflict."},
        422: {"description": "Maker-checker control semantic validation failed."},
    },
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
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmBulkReviewCampaignDefinition:
    surface = "maker_checker_control"
    try:
        result = application_service.record_campaign_definition_maker_checker_control(
            command=DpmCampaignDefinitionMakerCheckerControlCommand(
                tenant_id=trusted_context.tenant_id,
                campaign_id=campaign_id,
                campaign_version=campaign_version,
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
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmBulkReviewCampaignDefinitionMakerCheckerControlPage:
    try:
        return application_service.list_campaign_definition_maker_checker_controls(
            tenant_id=trusted_context.tenant_id,
            campaign_id=campaign_id,
            campaign_version=campaign_version,
            limit=limit,
            offset=offset,
        )
    except DpmWaveCampaignApplicationNotFoundError as exc:
        raise campaign_definition_not_found_http_exception() from exc
