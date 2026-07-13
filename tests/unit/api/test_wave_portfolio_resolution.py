from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import HTTPException

from src.api.routers.wave_portfolio_resolution import (
    _require_risk_event_cohort_ready,
    _require_tactical_house_view_candidate_portfolios,
    _require_tactical_house_view_source_refs,
    _risk_event_authority_request_for_wave,
    _required_tactical_house_view,
    _tactical_house_view_authority_request_for_wave,
    resolve_portfolio_inputs_for_request,
)
from src.api.routers.wave_request_models import DpmWavePreviewRequest
from src.api.services import wave_service
from src.api.services.wave_campaign_application import DpmWaveCampaignApplicationService
from src.infrastructure.waves import InMemoryDpmBulkReviewCampaignDefinitionRepository


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


def _risk_event_request(
    **overrides: object,
) -> DpmWavePreviewRequest:
    payload: dict[str, object] = {
        "trigger_type": "RISK_EVENT",
        "trigger_id": "wave-risk-event-20260519",
        "rationale": "Review portfolios affected by a source-owned rate shock event.",
        "as_of_date": "2026-05-19",
        "actor_id": "pm_001",
        "risk_event_id": " RISK_EVT_20260519 ",
        "minimum_impact_score": 0.35,
        "portfolios": [
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                "portfolio_manager_id": "PM_SG_DPM_001",
                "exposure_weights": {" equity ": 0.55, "fixed_income": 0.35},
                "source_refs": [
                    {
                        "source_system": "lotus-core",
                        "source_type": "RISK_EVENT_CANDIDATE_SET",
                        "source_id": "candidate-set-20260519",
                        "source_version": "2026-05-19",
                        "supportability_state": "READY",
                        "content_hash": "sha256:candidate-set",
                    }
                ],
            }
        ],
    }
    payload.update(overrides)
    return DpmWavePreviewRequest.model_validate(payload)


class _RiskEventCohort:
    risk_event_id = "RISK_EVT_20260519"
    product_name = "RiskEventAffectedCohort"
    product_version = "RiskEventAffectedCohort:v1"
    source_service = "lotus-risk"
    request_fingerprint = "sha256:risk-event-cohort"
    reason_codes = ("RISK_EVENT_AFFECTED_COHORT_READY",)

    def __init__(
        self,
        *,
        calculation_supportability: str = "ready",
        affected_portfolios: tuple[object, ...] = (object(),),
    ) -> None:
        self.cohort_id = "risk-event-cohort-20260519"
        self.calculation_supportability = calculation_supportability
        self.affected_portfolios = affected_portfolios


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


def test_risk_event_authority_request_for_wave_maps_source_context() -> None:
    request = _risk_event_request()

    authority_request = _risk_event_authority_request_for_wave(request)

    assert authority_request.risk_event_id == "RISK_EVT_20260519"
    assert authority_request.as_of_date.isoformat() == "2026-05-19"
    assert authority_request.minimum_impact_score == Decimal("0.35")
    assert authority_request.candidate_payloads.risk_portfolios == [
        {
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            "portfolio_manager_id": "PM_SG_DPM_001",
            "exposure_weights": {"EQUITY": 0.55, "FIXED_INCOME": 0.35},
        }
    ]


def test_portfolio_resolution_dispatch_preserves_explicit_portfolio_payloads() -> None:
    request = _tactical_house_view_request(
        trigger_type="EXPLICIT_PORTFOLIO_LIST",
        tactical_house_view=None,
    )

    resolved = resolve_portfolio_inputs_for_request(
        request=request,
        correlation_id="corr-wave-dispatch",
        advise_authority_client=None,
        risk_authority_client=None,
        campaign_application_service=DpmWaveCampaignApplicationService(
            campaign_definition_repository=InMemoryDpmBulkReviewCampaignDefinitionRepository()
        ),
        core_resolver_factory=object,
    )

    assert resolved == [portfolio.model_dump(mode="json") for portfolio in request.portfolios]


def test_risk_event_resolution_helpers_reject_missing_source_evidence() -> None:
    request = _risk_event_request(risk_event_id=" ")
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        _risk_event_authority_request_for_wave(request)
    assert exc_info.value.code == "RISK_EVENT_ID_REQUIRED"

    request = _risk_event_request(portfolios=[])
    with pytest.raises(wave_service.DpmWaveValidationError) as exc_info:
        _risk_event_authority_request_for_wave(request)
    assert exc_info.value.code == "RISK_EVENT_CANDIDATE_PORTFOLIOS_REQUIRED"


def test_risk_event_cohort_ready_helper_rejects_incomplete_or_empty_source_cohort() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _require_risk_event_cohort_ready(
            _RiskEventCohort(
                calculation_supportability="blocked",
                affected_portfolios=(object(),),
            )
        )
    assert exc_info.value.status_code == 424
    assert exc_info.value.detail["code"] == "DPM_RISK_EVENT_COHORT_INCOMPLETE"
    assert exc_info.value.detail["reason_codes"] == ["RISK_EVENT_AFFECTED_COHORT_READY"]

    with pytest.raises(HTTPException) as exc_info:
        _require_risk_event_cohort_ready(_RiskEventCohort(affected_portfolios=()))
    assert exc_info.value.status_code == 424
    assert exc_info.value.detail["code"] == "DPM_RISK_EVENT_COHORT_EMPTY"


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
