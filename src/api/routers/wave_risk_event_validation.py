from __future__ import annotations

from collections.abc import Mapping

from src.api.services import wave_service


def normalize_risk_event_exposure_weights(values: Mapping[str, float]) -> dict[str, float]:
    exposure_weights = {
        bucket.strip().upper(): weight for bucket, weight in values.items() if bucket.strip()
    }
    if not exposure_weights:
        raise wave_service.DpmWaveValidationError(
            "RISK_EVENT_EXPOSURE_WEIGHTS_REQUIRED",
            "RISK_EVENT candidate portfolios require source-supplied exposure_weights.",
        )
    if any(weight < 0 for weight in exposure_weights.values()):
        raise wave_service.DpmWaveValidationError(
            "RISK_EVENT_EXPOSURE_WEIGHTS_INVALID",
            "RISK_EVENT exposure_weights must be non-negative.",
        )
    return exposure_weights
