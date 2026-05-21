from __future__ import annotations

from typing import Callable

from src.api.routers.wave_http_errors import (
    wave_lookup_http_exception,
    wave_validation_http_exception,
)
from src.api.routers.wave_request_models import DpmWaveWorkflowCommandRequest
from src.api.routers.wave_response_contracts import DpmWaveResponse, wave_response
from src.api.services import wave_service
from src.core.waves import DpmRebalanceWave, DpmWaveRepository

WaveWorkflowCommand = Callable[
    ...,
    tuple[DpmRebalanceWave, bool],
]


def run_wave_workflow_command_response(
    *,
    command: WaveWorkflowCommand,
    wave_id: str,
    request: DpmWaveWorkflowCommandRequest,
    correlation_id: str,
    wave_repository: DpmWaveRepository,
) -> DpmWaveResponse:
    try:
        wave, replayed = command(
            wave_id=wave_id,
            actor_id=request.actor_id,
            reason_code=request.reason_code,
            comment=request.comment,
            correlation_id=correlation_id,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc) from exc
    return wave_response(wave=wave, durable=True, idempotent_replay=replayed)
