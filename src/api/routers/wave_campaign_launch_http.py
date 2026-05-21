from __future__ import annotations

from collections.abc import Callable

from src.api.routers.wave_campaign_definition_http import (
    campaign_definition_conflict_http_exception,
    campaign_definition_launch_blocked_http_exception,
    get_campaign_definition_or_404,
)
from src.api.routers.wave_campaign_models import DpmBulkReviewCampaignDefinitionLaunchRequest
from src.api.routers.wave_http_errors import wave_validation_http_exception
from src.api.routers.wave_portfolio_resolution import resolve_portfolio_inputs_for_request
from src.api.routers.wave_request_models import DpmWavePreviewRequest
from src.api.routers.wave_response_contracts import DpmWaveResponse, wave_response
from src.api.services import wave_service
from src.core.mandate_repository import DpmMandateRepository
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmBulkReviewCampaignDefinitionLaunchBlocked,
    DpmBulkReviewCampaignDefinitionRepository,
    DpmWaveRepository,
    build_bulk_review_campaign_definition_launch_command,
    record_bulk_review_campaign_definition_launch,
)


def launch_bulk_review_campaign_definition_response(
    *,
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionLaunchRequest,
    mandate_repository: DpmMandateRepository,
    wave_repository: DpmWaveRepository,
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository,
    core_resolver_factory: Callable[[], object],
) -> DpmWaveResponse:
    definition = get_campaign_definition_or_404(
        repository=campaign_definition_repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    try:
        launch_command = build_bulk_review_campaign_definition_launch_command(
            definition=definition,
            requested_as_of_date=request.requested_as_of_date,
            actor_id=request.actor_id,
            correlation_id=request.correlation_id,
        )
    except DpmBulkReviewCampaignDefinitionLaunchBlocked as exc:
        raise campaign_definition_launch_blocked_http_exception(exc) from exc
    wave_request = DpmWavePreviewRequest.model_validate(
        launch_command.create_request.model_dump(mode="json")
    )
    try:
        portfolios = resolve_portfolio_inputs_for_request(
            request=wave_request,
            correlation_id=launch_command.correlation_id,
            advise_authority_client=None,
            risk_authority_client=None,
            campaign_definition_repository=campaign_definition_repository,
            core_resolver_factory=core_resolver_factory,
        )
        wave, replay = wave_service.create_wave(
            trigger_type=wave_request.trigger_type,
            trigger_id=wave_request.trigger_id,
            rationale=wave_request.rationale,
            as_of_date=wave_request.as_of_date,
            actor_id=wave_request.actor_id,
            correlation_id=launch_command.correlation_id,
            portfolios=portfolios,
            idempotency_key=launch_command.idempotency_key,
            mandate_repository=mandate_repository,
            wave_repository=wave_repository,
        )
        launched_definition = record_bulk_review_campaign_definition_launch(
            definition=definition,
            wave_id=wave.wave_id,
            launched_by=wave_request.actor_id,
            requested_as_of_date=wave_request.as_of_date,
            correlation_id=launch_command.correlation_id,
            idempotency_key=launch_command.idempotency_key,
        )
        if launched_definition.content_hash != definition.content_hash:
            campaign_definition_repository.record_definition_launch(definition=launched_definition)
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc, conflict_codes=()) from exc
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(
            exc,
            message="Bulk-review campaign definition launch audit could not be recorded.",
        ) from exc
    return wave_response(wave=wave, durable=True, idempotent_replay=replay)
