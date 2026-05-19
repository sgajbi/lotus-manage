from __future__ import annotations

import pytest

from src.api.routers.wave_risk_event_validation import normalize_risk_event_exposure_weights
from src.api.services import wave_service


def test_normalize_risk_event_exposure_weights_strips_and_uppercases_buckets() -> None:
    assert normalize_risk_event_exposure_weights(
        {" equity ": 0.55, "": 0.25, " fixed_income": 0.35}
    ) == {
        "EQUITY": 0.55,
        "FIXED_INCOME": 0.35,
    }


def test_normalize_risk_event_exposure_weights_raises_when_empty() -> None:
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        normalize_risk_event_exposure_weights({" ": 0.25})

    assert exc_info.value.code == "RISK_EVENT_EXPOSURE_WEIGHTS_REQUIRED"
    assert (
        exc_info.value.message
        == "RISK_EVENT candidate portfolios require source-supplied exposure_weights."
    )


def test_normalize_risk_event_exposure_weights_raises_for_negative_weight() -> None:
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        normalize_risk_event_exposure_weights({"EQUITY": -0.1})

    assert exc_info.value.code == "RISK_EVENT_EXPOSURE_WEIGHTS_INVALID"
    assert exc_info.value.message == "RISK_EVENT exposure_weights must be non-negative."
