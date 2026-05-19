from __future__ import annotations

import pytest

from src.api.routers.wave_required_text_validation import normalize_required_text
from src.api.services import wave_service


def test_normalize_required_text_strips_supplied_value() -> None:
    assert (
        normalize_required_text(
            " PM_SG_DPM_001 ",
            required_code="VALUE_REQUIRED",
            required_message="Value is required.",
        )
        == "PM_SG_DPM_001"
    )


def test_normalize_required_text_raises_for_none() -> None:
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        normalize_required_text(
            None,
            required_code="VALUE_REQUIRED",
            required_message="Value is required.",
        )

    assert exc_info.value.code == "VALUE_REQUIRED"
    assert exc_info.value.message == "Value is required."


def test_normalize_required_text_raises_for_blank_value() -> None:
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        normalize_required_text(
            "   ",
            required_code="VALUE_REQUIRED",
            required_message="Value is required.",
        )

    assert exc_info.value.code == "VALUE_REQUIRED"
    assert exc_info.value.message == "Value is required."
