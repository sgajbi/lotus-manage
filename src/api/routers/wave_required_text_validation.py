from __future__ import annotations

from src.api.services import wave_service


def normalize_required_text(
    value: str | None,
    *,
    required_code: str,
    required_message: str,
) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise wave_service.DpmWaveValidationError(required_code, required_message)
    return normalized
