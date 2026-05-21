from __future__ import annotations

import logging
from typing import cast

from src.api.observability import record_wave_supportability
from src.api.routers.wave_http_errors import wave_lookup_http_exception
from src.api.routers.wave_response_contracts import DpmWaveSupportabilityResponse
from src.api.services import wave_service
from src.core.waves import DpmWaveRepository

WAVE_SUPPORTABILITY_SURFACE = "rebalance/waves/supportability"


def get_wave_supportability_response(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
    logger: logging.Logger,
) -> DpmWaveSupportabilityResponse:
    try:
        payload = wave_service.wave_supportability(
            wave_id=wave_id,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        record_wave_supportability(
            surface=WAVE_SUPPORTABILITY_SURFACE,
            supportability_state="not_found",
            reason="wave_not_found",
        )
        raise wave_lookup_http_exception(exc) from exc

    supportability_state = str(payload["supportability_state"])
    reason = str(payload["reason"])
    record_wave_supportability(
        surface=WAVE_SUPPORTABILITY_SURFACE,
        supportability_state=supportability_state,
        reason=reason,
    )
    logger.info(
        "wave.supportability.inspected",
        extra={
            "extra_fields": {
                "wave_state": payload["wave_state"],
                "supportability_state": supportability_state,
                "reason": reason,
                "issue_count": len(cast(list[object], payload["issues"])),
            }
        },
    )
    return DpmWaveSupportabilityResponse.model_validate(payload)
