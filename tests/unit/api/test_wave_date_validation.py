from __future__ import annotations

from datetime import date

import pytest

from src.api.routers.wave_date_validation import parse_wave_as_of_date
from src.api.services import wave_service


def test_parse_wave_as_of_date_accepts_iso_date() -> None:
    assert parse_wave_as_of_date("2026-05-10") == date(2026, 5, 10)


def test_parse_wave_as_of_date_raises_wave_validation_error() -> None:
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        parse_wave_as_of_date("2026/05/10")

    assert exc_info.value.code == "INVALID_AS_OF_DATE"
    assert exc_info.value.message == "as_of_date must be an ISO date."
