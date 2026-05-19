from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from src.api.routers.wave_tactical_candidate_selection import (
    build_tactical_house_view_candidate_payloads,
    build_tactical_house_view_resolved_portfolios,
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


@dataclass(frozen=True)
class AffectedPortfolio:
    portfolio_id: str = "PB_SG_GLOBAL_BAL_001"
    mandate_id: str | None = "MANDATE_PB_SG_GLOBAL_BAL_001"
    inclusion_reason_codes: tuple[str, ...] = ("TACTICAL_UNDERWEIGHT",)
    source_refs: tuple[dict[str, object], ...] = (
        {
            "source_system": "lotus-core",
            "source_type": "HoldingsAsOf",
            "source_id": "holdings-as-of-20260519",
            "source_version": "2026-05-19",
            "supportability_state": "READY",
            "content_hash": "sha256:holdings",
        },
    )


@dataclass(frozen=True)
class Cohort:
    cohort_id: str = "tactical-cohort-20260519"
    tactical_view_id: str = "THV_20260519"
    tactical_view_version: str = "v3"
    theme_id: str = "QUALITY_ROTATION"
    target_action: str = "REBALANCE"
    product_name: str = "TacticalHouseViewAffectedCohort"
    product_version: str = "v1"
    source_service: str = "lotus-advise"
    content_hash: str | None = "sha256:tactical-cohort"
    supportability_state: str = "READY"
    supportability_reason_codes: tuple[str, ...] = ("TACTICAL_HOUSE_VIEW_READY",)
    affected_portfolios: tuple[AffectedPortfolio, ...] = (AffectedPortfolio(),)


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


def test_build_tactical_house_view_resolved_portfolios_preserves_lineage_and_diagnostics() -> None:
    portfolios = build_tactical_house_view_resolved_portfolios(Cohort())

    assert portfolios == [
        {
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            "source_refs": [
                {
                    "source_system": "lotus-advise",
                    "source_type": "TacticalHouseViewAffectedCohort",
                    "source_id": "tactical-cohort-20260519",
                    "source_version": "v1",
                    "supportability_state": "READY",
                    "content_hash": "sha256:tactical-cohort",
                },
                {
                    "source_system": "lotus-advise",
                    "source_type": "TACTICAL_HOUSE_VIEW",
                    "source_id": "THV_20260519",
                    "source_version": "v3",
                    "supportability_state": "READY",
                    "content_hash": "sha256:tactical-cohort",
                },
                {
                    "source_system": "lotus-advise",
                    "source_type": "TACTICAL_HOUSE_VIEW_AFFECTED_PORTFOLIO",
                    "source_id": "tactical-cohort-20260519:PB_SG_GLOBAL_BAL_001",
                    "source_version": "v1",
                    "supportability_state": "READY",
                    "content_hash": "sha256:tactical-cohort",
                },
                {
                    "source_system": "lotus-core",
                    "source_type": "HoldingsAsOf",
                    "source_id": "holdings-as-of-20260519",
                    "source_version": "2026-05-19",
                    "supportability_state": "READY",
                    "content_hash": "sha256:holdings",
                },
            ],
            "diagnostics": {
                "source_owner": "lotus-advise",
                "source_product": "TacticalHouseViewAffectedCohort:v1",
                "tactical_view_id": "THV_20260519",
                "tactical_view_version": "v3",
                "theme_id": "QUALITY_ROTATION",
                "target_action": "REBALANCE",
                "cohort_supportability_state": "READY",
                "cohort_reason_codes": ["TACTICAL_HOUSE_VIEW_READY"],
                "inclusion_reason_codes": ["TACTICAL_UNDERWEIGHT"],
            },
        }
    ]


def test_build_tactical_house_view_resolved_portfolios_preserves_missing_content_hash() -> None:
    portfolios = build_tactical_house_view_resolved_portfolios(Cohort(content_hash=None))

    assert portfolios[0]["source_refs"][0]["content_hash"] is None
    assert portfolios[0]["source_refs"][1]["content_hash"] is None
    assert portfolios[0]["source_refs"][2]["content_hash"] is None
