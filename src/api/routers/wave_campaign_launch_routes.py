from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import (
    get_mandate_repository,
    get_wave_campaign_application_service,
    get_wave_repository,
)
from src.api.routers.wave_campaign_definition_errors import (
    campaign_definition_conflict_http_exception,
    campaign_definition_launch_blocked_http_exception,
    campaign_definition_not_found_http_exception,
)
from src.api.routers.wave_campaign_models import DpmBulkReviewCampaignDefinitionLaunchRequest
from src.api.routers.wave_campaign_trusted_context import (
    CampaignTrustedContext,
    campaign_trusted_context_required,
)
from src.api.routers.wave_campaign_workflow_telemetry import (
    campaign_workflow_http_exception,
    record_campaign_workflow_success,
    record_campaign_workflow_unexpected_error,
    record_campaign_workflow_validation_failure,
)
from src.api.routers.wave_http_errors import wave_validation_http_exception
from src.api.routers.wave_response_contracts import DpmWaveResponse
from src.api.routers.wave_response_contracts import wave_response
from src.api.routers.wave_route_parameters import (
    CampaignDefinitionIdPath,
    CampaignDefinitionVersionPath,
)
from src.api.services import wave_service
from src.api.services.wave_campaign_application import (
    DpmCampaignDefinitionLaunchCommand,
    DpmWaveCampaignApplicationNotFoundError,
    DpmWaveCampaignApplicationService,
)
from src.core.mandate_repository import DpmMandateRepository
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmBulkReviewCampaignDefinitionLaunchBlocked,
    DpmWaveRepository,
)


router = APIRouter(tags=["lotus-manage Rebalance Waves"])


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
    campaign_id: CampaignDefinitionIdPath,
    campaign_version: CampaignDefinitionVersionPath,
    request: DpmBulkReviewCampaignDefinitionLaunchRequest,
    trusted_context: CampaignTrustedContext = Depends(campaign_trusted_context_required),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    application_service: DpmWaveCampaignApplicationService = Depends(
        get_wave_campaign_application_service
    ),
) -> DpmWaveResponse:
    surface = "launch"
    try:
        result = application_service.launch_campaign_definition(
            command=DpmCampaignDefinitionLaunchCommand(
                tenant_id=trusted_context.tenant_id,
                campaign_id=campaign_id,
                campaign_version=campaign_version,
                requested_as_of_date=request.requested_as_of_date,
                actor_id=request.actor_id,
                correlation_id=request.correlation_id,
            ),
            mandate_repository=mandate_repository,
            wave_repository=wave_repository,
        )
    except DpmBulkReviewCampaignDefinitionLaunchBlocked as exc:
        http_exc = campaign_definition_launch_blocked_http_exception(exc)
        raise campaign_workflow_http_exception(surface=surface, exc=http_exc) from exc
    except DpmWaveCampaignApplicationNotFoundError as exc:
        raise campaign_workflow_http_exception(
            surface=surface,
            exc=campaign_definition_not_found_http_exception(),
        ) from exc
    except wave_service.DpmWaveValidationError as exc:
        http_exc = wave_validation_http_exception(exc, conflict_codes=())
        record_campaign_workflow_validation_failure(
            surface=surface,
            reason="wave_validation_error",
        )
        raise http_exc from exc
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        http_exc = campaign_definition_conflict_http_exception(
            exc,
            message="Bulk-review campaign definition launch audit could not be recorded.",
        )
        raise campaign_workflow_http_exception(surface=surface, exc=http_exc) from exc
    except HTTPException as exc:
        raise campaign_workflow_http_exception(surface=surface, exc=exc) from exc
    except Exception:
        record_campaign_workflow_unexpected_error(surface=surface)
        raise
    record_campaign_workflow_success(surface=surface, replay=result.replay)
    return wave_response(wave=result.wave, durable=True, idempotent_replay=result.replay)
