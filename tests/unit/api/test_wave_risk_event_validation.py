from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pytest

from src.api.routers.wave_risk_event_validation import (
    build_risk_event_candidate_payloads,
    build_risk_event_resolved_portfolios,
    normalize_risk_event_exposure_weights,
    risk_event_cohort_membership_failure,
)
from src.api.services import wave_service
from src.core.waves import DpmWaveSourceRef


@dataclass(frozen=True)
class Candidate:
    portfolio_id: str = "PB_SG_GLOBAL_BAL_001"
    mandate_id: str | None = "MANDATE_PB_SG_GLOBAL_BAL_001"
    portfolio_manager_id: str | None = "PM_SG_DPM_001"
    exposure_weights: dict[str, float] = field(
        default_factory=lambda: {" equity ": 0.55, " fixed_income": 0.35, "": 0.10}
    )
    source_refs: list[DpmWaveSourceRef] = field(
        default_factory=lambda: [
            DpmWaveSourceRef(
                source_system="lotus-core",
                source_type="RISK_EVENT_CANDIDATE_SET",
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
    source_ref: str = "risk-event-row-001"


@dataclass(frozen=True)
class Cohort:
    cohort_id: str | None = "risk-event-cohort-20260519"
    risk_event_id: str = "RISK_EVT_20260519"
    as_of_date: date = date(2026, 5, 19)
    product_name: str = "RiskEventAffectedCohort"
    product_version: str = "RiskEventAffectedCohort:v1"
    source_service: str = "lotus-risk"
    request_fingerprint: str | None = "sha256:risk-event-cohort"
    calculation_supportability: str = "ready"
    affected_portfolios: tuple[AffectedPortfolio, ...] = (AffectedPortfolio(),)
    excluded_portfolios: tuple[AffectedPortfolio, ...] = ()


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


@pytest.mark.parametrize("reverse", [False, True])
def test_build_risk_event_candidate_payloads_rejects_conflicting_duplicate_ids(
    reverse: bool,
) -> None:
    first = Candidate(mandate_id="MANDATE_OLD", exposure_weights={"EQUITY": 0.40})
    second = Candidate(mandate_id="MANDATE_NEW", exposure_weights={"EQUITY": 0.60})
    candidates = [second, first] if reverse else [first, second]
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        build_risk_event_candidate_payloads(candidates)
    assert exc_info.value.code == "RISK_EVENT_CANDIDATE_PORTFOLIO_DUPLICATE"


def test_build_risk_event_candidate_payloads_rejects_identical_duplicates() -> None:
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        build_risk_event_candidate_payloads([Candidate(), Candidate()])
    assert exc_info.value.code == "RISK_EVENT_CANDIDATE_PORTFOLIO_DUPLICATE"


@pytest.mark.parametrize("reverse", [False, True])
def test_duplicate_candidate_identity_is_rejected_before_other_candidate_validation(
    reverse: bool,
) -> None:
    candidates = [Candidate(exposure_weights={}), Candidate()]
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        build_risk_event_candidate_payloads(list(reversed(candidates)) if reverse else candidates)
    assert exc_info.value.code == "RISK_EVENT_CANDIDATE_PORTFOLIO_DUPLICATE"


@pytest.mark.parametrize(
    ("cohort", "expected_code"),
    [
        (
            Cohort(affected_portfolios=(AffectedPortfolio(), AffectedPortfolio())),
            "DPM_RISK_EVENT_COHORT_DUPLICATE_MEMBER",
        ),
        (
            Cohort(excluded_portfolios=(AffectedPortfolio(),)),
            "DPM_RISK_EVENT_COHORT_DUPLICATE_MEMBER",
        ),
        (
            Cohort(
                affected_portfolios=(),
                excluded_portfolios=(AffectedPortfolio(), AffectedPortfolio()),
            ),
            "DPM_RISK_EVENT_COHORT_DUPLICATE_MEMBER",
        ),
        (
            Cohort(affected_portfolios=(AffectedPortfolio(portfolio_id="UNKNOWN"),)),
            "DPM_RISK_EVENT_COHORT_UNKNOWN_MEMBER",
        ),
        (
            Cohort(affected_portfolios=(AffectedPortfolio(mandate_id="OTHER_MANDATE"),)),
            "DPM_RISK_EVENT_COHORT_MANDATE_MISMATCH",
        ),
        (
            Cohort(
                affected_portfolios=(),
                excluded_portfolios=(AffectedPortfolio(mandate_id="OTHER_MANDATE"),),
            ),
            "DPM_RISK_EVENT_COHORT_MANDATE_MISMATCH",
        ),
        (
            Cohort(risk_event_id="OTHER_EVENT"),
            "DPM_RISK_EVENT_COHORT_EVENT_MISMATCH",
        ),
        (
            Cohort(as_of_date=date(2026, 5, 18)),
            "DPM_RISK_EVENT_COHORT_DATE_MISMATCH",
        ),
    ],
)
def test_risk_event_cohort_membership_rejects_ambiguous_or_unrequested_source(
    cohort: Cohort, expected_code: str
) -> None:
    assert (
        risk_event_cohort_membership_failure(
            cohort=cohort,
            candidate_by_portfolio_id={"PB_SG_GLOBAL_BAL_001": Candidate()},
            risk_event_id="RISK_EVT_20260519",
            as_of_date=date(2026, 5, 19),
        )
        == expected_code
    )


def test_risk_event_cohort_membership_accepts_unique_affected_and_excluded_candidates() -> None:
    assert (
        risk_event_cohort_membership_failure(
            cohort=Cohort(
                excluded_portfolios=(
                    AffectedPortfolio(portfolio_id="OTHER", mandate_id="OTHER_MANDATE"),
                )
            ),
            candidate_by_portfolio_id={
                "PB_SG_GLOBAL_BAL_001": Candidate(),
                "OTHER": Candidate(portfolio_id="OTHER", mandate_id="OTHER_MANDATE"),
            },
            risk_event_id="RISK_EVT_20260519",
            as_of_date=date(2026, 5, 19),
        )
        is None
    )


def test_build_risk_event_resolved_portfolios_preserves_cohort_event_and_candidate_lineage() -> (
    None
):
    portfolios = build_risk_event_resolved_portfolios(
        cohort=Cohort(),
        candidate_by_portfolio_id={"PB_SG_GLOBAL_BAL_001": Candidate()},
        fallback_risk_event_id="RISK_EVT_FALLBACK",
    )

    assert portfolios == [
        {
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            "source_refs": [
                {
                    "source_system": "lotus-risk",
                    "source_type": "RiskEventAffectedCohort",
                    "source_id": "risk-event-cohort-20260519",
                    "source_version": "RiskEventAffectedCohort:v1",
                    "supportability_state": "READY",
                    "content_hash": "sha256:risk-event-cohort",
                },
                {
                    "source_system": "lotus-risk",
                    "source_type": "RISK_EVENT",
                    "source_id": "RISK_EVT_20260519",
                    "source_version": "RiskEventAffectedCohort:v1",
                    "supportability_state": "READY",
                    "content_hash": "sha256:risk-event-cohort",
                },
                {
                    "source_system": "lotus-risk",
                    "source_type": "RISK_EVENT_AFFECTED_PORTFOLIO",
                    "source_id": "risk-event-row-001",
                    "source_version": "RiskEventAffectedCohort:v1",
                    "supportability_state": "READY",
                    "content_hash": "sha256:risk-event-cohort",
                },
                {
                    "source_system": "lotus-core",
                    "source_type": "RISK_EVENT_CANDIDATE_SET",
                    "source_id": "candidate-set-20260519",
                    "source_version": "2026-05-19",
                    "supportability_state": "READY",
                    "content_hash": "sha256:candidate-set",
                },
            ],
        }
    ]


def test_build_risk_event_resolved_portfolios_falls_back_to_request_fingerprint() -> None:
    portfolios = build_risk_event_resolved_portfolios(
        cohort=Cohort(cohort_id=None),
        candidate_by_portfolio_id={"PB_SG_GLOBAL_BAL_001": Candidate()},
        fallback_risk_event_id="RISK_EVT_FALLBACK",
    )

    assert portfolios[0]["source_refs"][0]["source_id"] == "sha256:risk-event-cohort"


def test_build_risk_event_resolved_portfolios_falls_back_to_requested_event_id() -> None:
    portfolios = build_risk_event_resolved_portfolios(
        cohort=Cohort(cohort_id=None, request_fingerprint=None),
        candidate_by_portfolio_id={"PB_SG_GLOBAL_BAL_001": Candidate()},
        fallback_risk_event_id="RISK_EVT_FALLBACK",
    )

    assert portfolios[0]["source_refs"][0]["source_id"] == "RISK_EVT_FALLBACK"
    assert portfolios[0]["source_refs"][0]["content_hash"] is None
    assert portfolios[0]["source_refs"][1]["content_hash"] is None
