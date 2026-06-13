from __future__ import annotations

from decimal import Decimal

import pytest

from src.api.routers.wave_portfolio_resolution import (
    _require_tactical_house_view_candidate_portfolios,
    _require_tactical_house_view_source_refs,
    _required_tactical_house_view,
    _tactical_house_view_authority_request_for_wave,
)
from src.api.routers.wave_request_models import DpmWavePreviewRequest
from src.api.services import wave_service


def _tactical_house_view_request(
    **overrides: object,
) -> DpmWavePreviewRequest:
    payload: dict[str, object] = {
        "trigger_type": "TACTICAL_HOUSE_VIEW",
        "trigger_id": "wave-thv-20260519",
        "rationale": "Review discretionary mandates affected by tactical house view.",
        "as_of_date": "2026-05-19",
        "actor_id": "pm_001",
        "portfolio_types": [" discretionary ", "DPM"],
        "min_tactical_exposure_weight": 0.05,
        "tactical_house_view": {
            "tactical_view_id": "THV_20260519",
            "tactical_view_version": "v3",
            "theme_id": "QUALITY_ROTATION",
            "target_action": "INCREASE",
            "rationale": "Increase quality equity exposure.",
            "source_refs": [
                {
                    "source_system": "lotus-advise",
                    "source_type": "TACTICAL_HOUSE_VIEW_DECISION",
                    "source_id": "thv-quality-20260519",
                    "source_version": "v3",
                    "supportability_state": "READY",
                    "content_hash": "sha256:tactical-view",
                }
            ],
        },
        "portfolios": [
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                "portfolio_type": "DISCRETIONARY",
                "discretionary_mandate": True,
                "current_exposure_weight": 0.18,
                "alignment_signal": "UNDERWEIGHT",
                "source_refs": [
                    {
                        "source_system": "lotus-core",
                        "source_type": "HoldingsAsOf",
                        "source_id": "holdings-as-of-20260519",
                        "source_version": "2026-05-19",
                        "supportability_state": "READY",
                        "content_hash": "sha256:holdings",
                    }
                ],
            }
        ],
    }
    payload.update(overrides)
    return DpmWavePreviewRequest.model_validate(payload)


def test_tactical_house_view_authority_request_for_wave_maps_source_context() -> None:
    request = _tactical_house_view_request()

    authority_request = _tactical_house_view_authority_request_for_wave(request)

    assert authority_request.tactical_view["as_of_date"] == "2026-05-19"
    assert authority_request.tactical_view["source_refs"] == [
        {
            "source_system": "lotus-advise",
            "source_type": "TACTICAL_HOUSE_VIEW_DECISION",
            "source_id": "thv-quality-20260519",
            "source_version": "v3",
            "supportability_state": "READY",
            "content_hash": "sha256:tactical-view",
        }
    ]
    assert authority_request.candidate_portfolios[0]["portfolio_id"] == ("PB_SG_GLOBAL_BAL_001")
    assert authority_request.eligible_portfolio_types == ["DISCRETIONARY", "DPM"]
    assert authority_request.min_exposure_weight == Decimal("0.05")


def test_tactical_house_view_resolution_helpers_reject_missing_source_evidence() -> None:
    request = _tactical_house_view_request(tactical_house_view=None)
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        _required_tactical_house_view(request)
    assert exc_info.value.code == "TACTICAL_HOUSE_VIEW_REQUIRED"

    request = _tactical_house_view_request(portfolios=[])
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        _require_tactical_house_view_candidate_portfolios(request)
    assert exc_info.value.code == "TACTICAL_HOUSE_VIEW_CANDIDATE_PORTFOLIOS_REQUIRED"

    request = _tactical_house_view_request(
        tactical_house_view={
            **_tactical_house_view_request().tactical_house_view.model_dump(mode="json"),
            "source_refs": [],
        }
    )
    tactical_view = _required_tactical_house_view(request)
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        _require_tactical_house_view_source_refs(tactical_view)
    assert exc_info.value.code == "TACTICAL_HOUSE_VIEW_SOURCE_REFS_REQUIRED"
