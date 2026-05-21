from __future__ import annotations

from src.api.routers.wave_http_errors import (
    wave_lookup_http_exception,
    wave_validation_http_exception,
)
from src.api.routers.wave_request_models import DpmWaveSourceCheckRequest
from src.api.routers.wave_response_contracts import DpmWaveResponse, wave_response
from src.api.services import wave_service
from src.core.mandate_repository import DpmMandateRepository
from src.core.waves import DpmWaveRepository


def source_check_wave_response(
    *,
    wave_id: str,
    request: DpmWaveSourceCheckRequest,
    correlation_id: str,
    mandate_repository: DpmMandateRepository,
    wave_repository: DpmWaveRepository,
) -> DpmWaveResponse:
    try:
        wave, replayed = wave_service.source_check_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            correlation_id=correlation_id,
            mandate_repository=mandate_repository,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc) from exc
    return wave_response(wave=wave, durable=True, idempotent_replay=replayed)
