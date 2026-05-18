from __future__ import annotations

from datetime import date

from src.api.services import wave_service


def parse_wave_as_of_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise wave_service.DpmWaveValidationError(
            "INVALID_AS_OF_DATE",
            "as_of_date must be an ISO date.",
        ) from exc
