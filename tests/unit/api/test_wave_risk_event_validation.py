from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from src.api.routers.wave_risk_event_validation import (
    build_risk_event_candidate_payloads,
    normalize_risk_event_exposure_weights,
)
from src.api.services import wave_service


@dataclass(frozen=True)
class Candidate:
    portfolio_id: str = "PB_SG_GLOBAL_BAL_001"
    mandate_id: str | None = "MANDATE_PB_SG_GLOBAL_BAL_001"
    portfolio_manager_id: str | None = "PM_SG_DPM_001"
    exposure_weights: dict[str, float] = field(
        default_factory=lambda: {" equity ": 0.55, " fixed_income": 0.35, "": 0.10}
    )


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


def test_build_risk_event_candidate_payloads_maps_candidates_for_source_authority() -> None:
    candidate = Candidate()

    payloads = build_risk_event_candidate_payloads([candidate])

    assert payloads.candidate_by_portfolio_id == {"PB_SG_GLOBAL_BAL_001": candidate}
    assert payloads.risk_portfolios == [
        {
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            "portfolio_manager_id": "PM_SG_DPM_001",
            "exposure_weights": {"EQUITY": 0.55, "FIXED_INCOME": 0.35},
        }
    ]


def test_build_risk_event_candidate_payloads_uses_last_candidate_by_portfolio_id() -> None:
    first = Candidate(mandate_id="MANDATE_OLD", exposure_weights={"EQUITY": 0.40})
    second = Candidate(mandate_id="MANDATE_NEW", exposure_weights={"EQUITY": 0.60})

    payloads = build_risk_event_candidate_payloads([first, second])

    assert payloads.candidate_by_portfolio_id["PB_SG_GLOBAL_BAL_001"] == second
    assert payloads.risk_portfolios == [
        {
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "mandate_id": "MANDATE_OLD",
            "portfolio_manager_id": "PM_SG_DPM_001",
            "exposure_weights": {"EQUITY": 0.40},
        },
        {
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "mandate_id": "MANDATE_NEW",
            "portfolio_manager_id": "PM_SG_DPM_001",
            "exposure_weights": {"EQUITY": 0.60},
        },
    ]
