from __future__ import annotations

from collections.abc import Callable

from src.api.routers.wave_http_errors import wave_validation_http_exception
from src.api.routers.wave_portfolio_resolution import resolve_portfolio_inputs_for_request
from src.api.routers.wave_request_models import DpmWavePreviewRequest
from src.api.routers.wave_response_contracts import DpmWaveResponse, wave_response
from src.api.services import wave_service
from src.core.mandate_repository import DpmMandateRepository
from src.core.waves import DpmBulkReviewCampaignDefinitionRepository, DpmWaveRepository
from src.infrastructure.advise_authority import LotusAdviseAuthorityClient
from src.infrastructure.risk_authority import LotusRiskAuthorityClient


def preview_wave_response(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
    mandate_repository: DpmMandateRepository,
    advise_authority_client: LotusAdviseAuthorityClient | None,
    risk_authority_client: LotusRiskAuthorityClient | None,
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository,
    core_resolver_factory: Callable[[], object],
) -> DpmWaveResponse:
    try:
        portfolios = resolve_portfolio_inputs_for_request(
            request=request,
            correlation_id=correlation_id,
            advise_authority_client=advise_authority_client,
            risk_authority_client=risk_authority_client,
            campaign_definition_repository=campaign_definition_repository,
            core_resolver_factory=core_resolver_factory,
        )
        wave = wave_service.preview_wave(
            trigger_type=request.trigger_type,
            trigger_id=request.trigger_id,
            rationale=request.rationale,
            as_of_date=request.as_of_date,
            actor_id=request.actor_id,
            correlation_id=correlation_id,
            portfolios=portfolios,
            mandate_repository=mandate_repository,
        )
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc, conflict_codes=()) from exc
    return wave_response(wave=wave, durable=False)


def create_wave_response(
    *,
    request: DpmWavePreviewRequest,
    idempotency_key: str,
    correlation_id: str,
    mandate_repository: DpmMandateRepository,
    wave_repository: DpmWaveRepository,
    advise_authority_client: LotusAdviseAuthorityClient | None,
    risk_authority_client: LotusRiskAuthorityClient | None,
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository,
    core_resolver_factory: Callable[[], object],
) -> DpmWaveResponse:
    try:
        portfolios = resolve_portfolio_inputs_for_request(
            request=request,
            correlation_id=correlation_id,
            advise_authority_client=advise_authority_client,
            risk_authority_client=risk_authority_client,
            campaign_definition_repository=campaign_definition_repository,
            core_resolver_factory=core_resolver_factory,
        )
        wave, replayed = wave_service.create_wave(
            trigger_type=request.trigger_type,
            trigger_id=request.trigger_id,
            rationale=request.rationale,
            as_of_date=request.as_of_date,
            actor_id=request.actor_id,
            correlation_id=correlation_id,
            portfolios=portfolios,
            idempotency_key=idempotency_key,
            mandate_repository=mandate_repository,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc, conflict_codes=("WAVE_CREATE_CONFLICT",)) from exc
    return wave_response(wave=wave, durable=True, idempotent_replay=replayed)
