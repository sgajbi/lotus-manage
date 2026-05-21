from __future__ import annotations

from typing import Literal

from src.api.routers.wave_response_contracts import DpmWaveSearchItem, DpmWaveSearchResponse
from src.api.services import wave_service
from src.core.waves import DpmWaveRepository


def search_waves_response(
    *,
    wave_repository: DpmWaveRepository,
    state: str | None,
    trigger_type: str | None,
    as_of_date: str | None,
    supportability_state: Literal["ready", "degraded", "blocked"] | None,
    limit: int,
    offset: int,
) -> DpmWaveSearchResponse:
    items = wave_service.search_waves(
        wave_repository=wave_repository,
        state=state,
        trigger_type=trigger_type,
        as_of_date=as_of_date,
        supportability_state=supportability_state,
        limit=limit,
        offset=offset,
    )
    return DpmWaveSearchResponse(
        items=[DpmWaveSearchItem.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
        returned_count=len(items),
    )
