from __future__ import annotations

from fastapi import status

from src.api.routers.wave_http_errors import (
    wave_lookup_http_exception,
    wave_validation_http_exception,
)
from src.api.services import wave_service


def test_wave_lookup_http_exception_maps_not_found_payload() -> None:
    exc = wave_service.DpmWaveLookupError("DPM_WAVE_NOT_FOUND", "Wave was not found.")

    http_exc = wave_lookup_http_exception(exc)

    assert http_exc.status_code == status.HTTP_404_NOT_FOUND
    assert http_exc.detail == {
        "code": "DPM_WAVE_NOT_FOUND",
        "message": "Wave was not found.",
    }


def test_wave_validation_http_exception_maps_default_version_conflict() -> None:
    exc = wave_service.DpmWaveValidationError(
        "DPM_WAVE_VERSION_CONFLICT",
        "Wave changed while updating.",
    )

    http_exc = wave_validation_http_exception(exc)

    assert http_exc.status_code == status.HTTP_409_CONFLICT
    assert http_exc.detail == {
        "code": "DPM_WAVE_VERSION_CONFLICT",
        "message": "Wave changed while updating.",
    }


def test_wave_validation_http_exception_uses_route_specific_conflict_codes() -> None:
    exc = wave_service.DpmWaveValidationError(
        "WAVE_CREATE_CONFLICT",
        "Idempotency conflict.",
    )

    create_http_exc = wave_validation_http_exception(
        exc,
        conflict_codes=("WAVE_CREATE_CONFLICT",),
    )
    preview_http_exc = wave_validation_http_exception(exc, conflict_codes=())

    assert create_http_exc.status_code == status.HTTP_409_CONFLICT
    assert preview_http_exc.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
