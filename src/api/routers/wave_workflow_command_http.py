from __future__ import annotations

from typing import Protocol

from src.api.routers.wave_http_errors import (
    wave_lookup_http_exception,
    wave_validation_http_exception,
)
from src.api.routers.wave_request_models import DpmWaveWorkflowCommandRequest
from src.api.routers.wave_response_contracts import DpmWaveResponse, wave_response
from src.api.services import wave_service
from src.core.waves import DpmRebalanceWave, DpmWaveRepository


class WaveWorkflowCommand(Protocol):
    """The four workflow commands, named argument by argument.

    This was `Callable[..., tuple[DpmRebalanceWave, bool]]`. The ellipsis erases
    the parameter list, so when the commands gained a required `tenant_id` the
    dispatcher kept calling them without it and mypy had nothing to check the
    call against - the four endpoints failed at request time instead. Spelling
    the arguments out makes a future required argument a type error here.
    """

    def __call__(
        self,
        *,
        wave_id: str,
        actor_id: str,
        reason_code: str,
        comment: str | None,
        correlation_id: str,
        wave_repository: DpmWaveRepository,
        tenant_id: str,
    ) -> tuple[DpmRebalanceWave, bool]: ...


def run_wave_workflow_command_response(
    *,
    command: WaveWorkflowCommand,
    wave_id: str,
    request: DpmWaveWorkflowCommandRequest,
    correlation_id: str,
    wave_repository: DpmWaveRepository,
    tenant_id: str,
) -> DpmWaveResponse:
    try:
        wave, replayed = command(
            wave_id=wave_id,
            actor_id=request.actor_id,
            reason_code=request.reason_code,
            comment=request.comment,
            correlation_id=correlation_id,
            wave_repository=wave_repository,
            tenant_id=tenant_id,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc) from exc
    return wave_response(wave=wave, durable=True, idempotent_replay=replayed)
