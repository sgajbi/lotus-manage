from __future__ import annotations

from collections.abc import Iterable

from src.api.services import wave_service


def normalize_required_portfolio_type(
    value: str | None,
    *,
    required_code: str,
    required_message: str,
) -> str:
    portfolio_type = (value or "").strip().upper()
    if not portfolio_type:
        raise wave_service.DpmWaveValidationError(required_code, required_message)
    return portfolio_type


def normalize_required_portfolio_types(
    values: Iterable[str],
    *,
    required_code: str,
    required_message: str,
) -> list[str]:
    portfolio_types = [value.strip().upper() for value in values if value.strip()]
    if not portfolio_types:
        raise wave_service.DpmWaveValidationError(required_code, required_message)
    return portfolio_types
