from __future__ import annotations

from src.api.routers.wave_http_errors import wave_lookup_http_exception
from src.api.routers.wave_response_contracts import (
    DpmWaveDetailResponse,
    DpmWaveItemsResponse,
    DpmWaveProofPackPostureResponse,
)
from src.api.services import wave_service
from src.core.waves import DpmWaveRepository


def get_wave_detail_response(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> DpmWaveDetailResponse:
    try:
        payload = wave_service.retrieve_wave_detail(
            wave_id=wave_id,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    return DpmWaveDetailResponse.model_validate(payload)


def get_wave_items_response(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> DpmWaveItemsResponse:
    try:
        payload = wave_service.list_wave_items(
            wave_id=wave_id,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    return DpmWaveItemsResponse.model_validate(payload)


def get_wave_proof_pack_posture_response(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> DpmWaveProofPackPostureResponse:
    try:
        payload = wave_service.proof_pack_posture(
            wave_id=wave_id,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    return DpmWaveProofPackPostureResponse.model_validate(payload)
