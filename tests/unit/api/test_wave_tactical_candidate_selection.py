from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from src.api.routers.wave_tactical_candidate_selection import (
    build_tactical_house_view_candidate_payloads,
)
from src.api.services import wave_service
from src.core.waves import DpmWaveSourceRef


@dataclass(frozen=True)
class Candidate:
    portfolio_id: str = "PB_SG_GLOBAL_BAL_001"
    mandate_id: str | None = "MANDATE_PB_SG_GLOBAL_BAL_001"
    portfolio_type: str | None = " discretionary "
    discretionary_mandate: bool | None = True
    current_exposure_weight: float | None = 0.18
    alignment_signal: str = "UNDERWEIGHT"
    source_refs: list[DpmWaveSourceRef] = field(
        default_factory=lambda: [
            DpmWaveSourceRef(
                source_system="lotus-core",
                source_type="TACTICAL_CANDIDATE_SET",
                source_id="candidate-set-20260519",
                source_version="2026-05-19",
                supportability_state="READY",
                content_hash="sha256:candidate-set",
            )
        ]
    )


def test_build_tactical_house_view_candidate_payloads_maps_source_backed_candidate() -> None:
    payloads = build_tactical_house_view_candidate_payloads([Candidate()])

    assert payloads == [
        {
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            "portfolio_type": "DISCRETIONARY",
            "discretionary_mandate": True,
            "current_exposure_weight": "0.18",
            "alignment_signal": "UNDERWEIGHT",
            "source_refs": [
                {
                    "source_system": "lotus-core",
                    "source_type": "TACTICAL_CANDIDATE_SET",
                    "source_id": "candidate-set-20260519",
                    "source_version": "2026-05-19",
                    "supportability_state": "READY",
                    "content_hash": "sha256:candidate-set",
                }
            ],
            "reason_codes": ["TACTICAL_HOUSE_VIEW_CANDIDATE_SOURCE_BACKED"],
        }
    ]


def test_build_tactical_house_view_candidate_payloads_preserves_missing_weight() -> None:
    payloads = build_tactical_house_view_candidate_payloads(
        [Candidate(current_exposure_weight=None)]
    )

    assert payloads[0]["current_exposure_weight"] is None


@pytest.mark.parametrize(
    ("candidate", "code", "message"),
    [
        (
            Candidate(portfolio_type=" "),
            "TACTICAL_HOUSE_VIEW_PORTFOLIO_TYPE_REQUIRED",
            "TACTICAL_HOUSE_VIEW candidate portfolios require source-owned portfolio_type.",
        ),
        (
            Candidate(discretionary_mandate=None),
            "TACTICAL_HOUSE_VIEW_DISCRETIONARY_MANDATE_REQUIRED",
            "TACTICAL_HOUSE_VIEW candidate portfolios require source-owned discretionary_mandate.",
        ),
        (
            Candidate(source_refs=[]),
            "TACTICAL_HOUSE_VIEW_CANDIDATE_SOURCE_REFS_REQUIRED",
            "TACTICAL_HOUSE_VIEW candidate portfolios require source_refs.",
        ),
    ],
)
def test_build_tactical_house_view_candidate_payloads_requires_source_evidence(
    candidate: Candidate,
    code: str,
    message: str,
) -> None:
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        build_tactical_house_view_candidate_payloads([candidate])

    assert exc_info.value.code == code
    assert exc_info.value.message == message
