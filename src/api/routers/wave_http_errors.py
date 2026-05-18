from __future__ import annotations

from fastapi import HTTPException, status

from src.api.services import wave_service


def wave_lookup_http_exception(exc: wave_service.DpmWaveLookupError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": exc.code, "message": exc.message},
    )


def wave_validation_http_exception(
    exc: wave_service.DpmWaveValidationError,
    *,
    conflict_codes: tuple[str, ...] = ("DPM_WAVE_VERSION_CONFLICT",),
) -> HTTPException:
    status_code = (
        status.HTTP_409_CONFLICT
        if exc.code in conflict_codes
        else status.HTTP_422_UNPROCESSABLE_CONTENT
    )
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": exc.message},
    )
