from __future__ import annotations

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_wave_campaign_application_service
from src.api.routers.wave_campaign_definition_errors import (
    campaign_definition_conflict_http_exception,
    campaign_definition_lifecycle_http_exception,
    campaign_definition_not_found_http_exception,
    campaign_definition_value_http_exception,
)
from src.api.routers.wave_campaign_trusted_context import (
    CampaignTrustedContext,
    campaign_trusted_context_required,
)
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionRetirementRequest,
    DpmBulkReviewCampaignDefinitionSupersessionRequest,
)
from src.api.services.wave_campaign_application import (
    DpmCampaignDefinitionRetireCommand,
    DpmCampaignDefinitionSupersedeCommand,
    DpmWaveCampaignApplicationNotFoundError,
    DpmWaveCampaignApplicationService,
)
from src.api.routers.wave_route_parameters import (
    CampaignDefinitionIdPath,
    CampaignDefinitionVersionPath,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionConflictError,
)
from src.core.waves.campaign_definition_lifecycle import (
    DpmBulkReviewCampaignDefinitionLifecycleError,
)


router = APIRouter(tags=["lotus-manage Rebalance Waves"])


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
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    request: DpmBulkReviewCampaignDefinitionRetirementRequest,
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmBulkReviewCampaignDefinition:
    try:
        return application_service.retire_campaign_definition(
            command=DpmCampaignDefinitionRetireCommand(
                tenant_id=trusted_context.tenant_id,
                campaign_id=campaign_id,
                campaign_version=campaign_version,
                retired_by=request.retired_by,
                retirement_reason=request.retirement_reason,
                correlation_id=request.correlation_id,
            )
        )
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except DpmBulkReviewCampaignDefinitionLifecycleError as exc:
        raise campaign_definition_lifecycle_http_exception(exc) from exc
    except DpmWaveCampaignApplicationNotFoundError as exc:
        raise campaign_definition_not_found_http_exception() from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc


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
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    request: DpmBulkReviewCampaignDefinitionSupersessionRequest,
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmBulkReviewCampaignDefinition:
    try:
        return application_service.supersede_campaign_definition(
            command=DpmCampaignDefinitionSupersedeCommand(
                tenant_id=trusted_context.tenant_id,
                campaign_id=campaign_id,
                campaign_version=campaign_version,
                replacement_version=request.superseded_by_campaign_version,
                superseded_by=request.superseded_by,
                supersession_reason=request.supersession_reason,
                correlation_id=request.correlation_id,
            )
        )
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except DpmBulkReviewCampaignDefinitionLifecycleError as exc:
        raise campaign_definition_lifecycle_http_exception(exc) from exc
    except DpmWaveCampaignApplicationNotFoundError as exc:
        raise campaign_definition_not_found_http_exception() from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc
