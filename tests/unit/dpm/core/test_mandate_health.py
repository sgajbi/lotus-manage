from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from src.core.dpm_source_context import (
    DpmCoreMandateBindingResponse,
    DpmCoreMarketDataCoverageWindowResponse,
    DpmCoreModelPortfolioTargetResponse,
)
from src.core.mandates import (
    DIMENSION_WEIGHTS,
    DpmMandateConstraintSet,
    DpmMandateDimensionScore,
    DpmMandateDigitalTwin,
    DpmMandateHealthInput,
    DpmMandateHealthSnapshot,
    DpmMandatePreferences,
    DpmMandateReviewPolicy,
    MandateHealthDimension,
    MandateHealthState,
    MandateRecommendedAction,
    calculate_mandate_health,
    compile_mandate_digital_twin_from_core,
    build_health_input_from_core_sources,
    monitoring_exceptions_from_health,
)


AS_OF = date(2026, 5, 3)


def _mandate_binding(**overrides: object) -> DpmCoreMandateBindingResponse:
    payload: dict[str, Any] = {
        "product_name": "DiscretionaryMandateBinding",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
        "client_id": "CIF_SG_000184",
        "mandate_type": "discretionary",
        "discretionary_authority_status": "active",
        "booking_center_code": "Singapore",
        "jurisdiction_code": "SG",
        "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
        "policy_pack_id": "POLICY_DPM_SG_BALANCED_V1",
        "risk_profile": "balanced",
        "investment_horizon": "long_term",
        "leverage_allowed": False,
        "tax_awareness_allowed": True,
        "settlement_awareness_required": True,
        "rebalance_frequency": "quarterly",
        "rebalance_bands": {
            "default_band": "0.0250000000",
            "cash_reserve_weight": "0.0200000000",
        },
        "effective_from": "2026-04-01",
        "binding_version": 3,
        "supportability": {
            "state": "READY",
            "reason": "MANDATE_BINDING_READY",
            "missing_data_families": [],
        },
        "lineage": {"contract_version": "DiscretionaryMandateBinding:v1"},
        "data_quality_status": "READY",
        "latest_evidence_timestamp": "2026-05-03T01:00:00Z",
    }
    payload.update(overrides)
    return DpmCoreMandateBindingResponse.model_validate(payload)


def _model_targets(**overrides: object) -> DpmCoreModelPortfolioTargetResponse:
    payload: dict[str, Any] = {
        "product_name": "DpmModelPortfolioTarget",
        "product_version": "v1",
        "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
        "model_portfolio_version": "2026.04",
        "as_of_date": "2026-05-03",
        "display_name": "Singapore Global Balanced DPM Model",
        "base_currency": "SGD",
        "risk_profile": "balanced",
        "mandate_type": "discretionary",
        "approval_status": "approved",
        "effective_from": "2026-04-01",
        "targets": [
            {
                "instrument_id": "EQ_US_AAPL",
                "target_weight": "0.6000000000",
                "min_weight": "0.5500000000",
                "max_weight": "0.6500000000",
                "target_status": "active",
                "quality_status": "accepted",
            },
            {
                "instrument_id": "FI_US_TREASURY_10Y",
                "target_weight": "0.4000000000",
                "min_weight": "0.3500000000",
                "max_weight": "0.4500000000",
                "target_status": "active",
                "quality_status": "accepted",
            },
        ],
        "supportability": {
            "state": "READY",
            "reason": "MODEL_TARGETS_READY",
            "target_count": 2,
            "total_target_weight": "1.0000000000",
        },
        "lineage": {"contract_version": "DpmModelPortfolioTarget:v1"},
        "data_quality_status": "READY",
        "latest_evidence_timestamp": "2026-05-03T01:00:00Z",
    }
    payload.update(overrides)
    return DpmCoreModelPortfolioTargetResponse.model_validate(payload)


def _market_data_coverage(**overrides: object) -> DpmCoreMarketDataCoverageWindowResponse:
    payload: dict[str, Any] = {
        "product_name": "MarketDataCoverageWindow",
        "product_version": "v1",
        "as_of_date": "2026-05-03",
        "valuation_currency": "SGD",
        "price_coverage": [],
        "fx_coverage": [],
        "supportability": {
            "state": "READY",
            "reason": "MARKET_DATA_READY",
            "requested_price_count": 2,
            "resolved_price_count": 2,
            "requested_fx_count": 0,
            "resolved_fx_count": 0,
        },
    }
    payload.update(overrides)
    return DpmCoreMarketDataCoverageWindowResponse.model_validate(payload)


def _twin(**overrides: object) -> DpmMandateDigitalTwin:
    payload: dict[str, Any] = {
        "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "mandate_version": "3",
        "as_of_date": AS_OF,
        "base_currency": "SGD",
        "reference_currency": "SGD",
        "risk_profile": "BALANCED",
        "investment_objective": "LONG_TERM_TOTAL_RETURN",
        "time_horizon": "LONG_TERM",
        "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
        "constraints": DpmMandateConstraintSet(
            cash_band_min_weight=Decimal("0.02"),
            cash_band_max_weight=Decimal("0.10"),
            turnover_budget=Decimal("0.15"),
            max_tracking_error=Decimal("0.05"),
        ),
        "preferences": DpmMandatePreferences(),
        "review_policy": DpmMandateReviewPolicy(next_review_due_date=date(2026, 6, 30)),
    }
    payload.update(overrides)
    return DpmMandateDigitalTwin.model_validate(payload)


def _ready_input(**overrides: object) -> DpmMandateHealthInput:
    payload: dict[str, Any] = {
        "twin": _twin(),
        "current_weights": {
            "EQ_US_AAPL": Decimal("0.60"),
            "FI_US_TREASURY_10Y": Decimal("0.40"),
        },
        "target_weights": {
            "EQ_US_AAPL": Decimal("0.60"),
            "FI_US_TREASURY_10Y": Decimal("0.40"),
        },
        "cash_weight": Decimal("0.05"),
    }
    payload.update(overrides)
    return DpmMandateHealthInput.model_validate(payload)


def _dimension(
    snapshot: DpmMandateHealthSnapshot,
    dimension: MandateHealthDimension,
) -> DpmMandateDimensionScore:
    return next(score for score in snapshot.dimension_scores if score.dimension == dimension)


def test_dimension_weights_are_complete_and_balanced() -> None:
    assert sum(DIMENSION_WEIGHTS.values()) == 100
    assert set(DIMENSION_WEIGHTS) == set(MandateHealthDimension)


def test_compile_mandate_twin_uses_core_source_truth_and_explicit_gap_codes() -> None:
    twin = compile_mandate_digital_twin_from_core(
        mandate=_mandate_binding(),
        model_targets=_model_targets(),
        as_of_date=AS_OF,
    )

    assert twin.mandate_id == "MANDATE_PB_SG_GLOBAL_BAL_001"
    assert twin.portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert twin.model_portfolio_id == "MODEL_PB_SG_GLOBAL_BAL_DPM"
    assert twin.base_currency == "SGD"
    assert twin.constraints.cash_band_min_weight == Decimal("0.0200000000")
    assert twin.review_policy.review_frequency == "QUARTERLY"
    assert [lineage.product_name for lineage in twin.source_lineage] == [
        "DiscretionaryMandateBinding",
        "DpmModelPortfolioTarget",
    ]
    assert "MANDATE_OBJECTIVE_PROFILE_NOT_YET_SOURCED" in twin.field_gap_codes


def test_build_health_input_from_market_data_coverage_preserves_degraded_sources() -> None:
    health_input = build_health_input_from_core_sources(
        twin=_twin(),
        model_targets=_model_targets(),
        market_data_coverage=_market_data_coverage(
            supportability={
                "state": "DEGRADED",
                "reason": "PRICE_STALE",
                "requested_price_count": 2,
                "resolved_price_count": 2,
                "requested_fx_count": 1,
                "resolved_fx_count": 1,
                "stale_instrument_ids": ["EQ_US_AAPL"],
                "stale_currency_pairs": ["USD/SGD"],
            }
        ),
    )

    assert health_input.source_readiness_state == "DEGRADED"
    assert health_input.degraded_source_families == ["MARKET_DATA_COVERAGE"]
    assert health_input.stale_source_families == ["EQ_US_AAPL", "USD/SGD"]


def test_ready_mandate_has_all_ready_dimensions_and_no_recommended_action() -> None:
    snapshot = calculate_mandate_health(_ready_input())

    assert snapshot.health_state == MandateHealthState.READY
    assert snapshot.health_score == 100
    assert snapshot.recommended_action == MandateRecommendedAction.NONE
    assert not snapshot.top_reasons
    assert {score.dimension for score in snapshot.dimension_scores} == set(MandateHealthDimension)


def test_mandate_constraints_reject_invalid_ratio_and_cash_band() -> None:
    with pytest.raises(ValueError, match="cash_band_min_weight"):
        DpmMandateConstraintSet(cash_band_min_weight=Decimal("2"))
    with pytest.raises(ValueError, match="cash_band_min_weight must not exceed"):
        DpmMandateConstraintSet(
            cash_band_min_weight=Decimal("0.20"),
            cash_band_max_weight=Decimal("0.10"),
        )


def test_health_source_staleness_risk_ready_and_workflow_blocked_edges() -> None:
    stale_snapshot = calculate_mandate_health(
        _ready_input(source_readiness_state="DEGRADED", stale_source_families=["PRICE"])
    )
    risk_ready_snapshot = calculate_mandate_health(_ready_input(tracking_error=Decimal("0.01")))
    workflow_blocked_snapshot = calculate_mandate_health(_ready_input(workflow_blocked=True))

    assert _dimension(stale_snapshot, MandateHealthDimension.SOURCE_READINESS).reason_code == (
        "DPM_SOURCE_STALE"
    )
    assert _dimension(risk_ready_snapshot, MandateHealthDimension.RISK_DRIFT).state == (
        MandateHealthState.READY
    )
    assert _dimension(
        workflow_blocked_snapshot, MandateHealthDimension.WORKFLOW_READINESS
    ).state == (MandateHealthState.BLOCKED)


@pytest.mark.parametrize(
    ("overrides", "dimension", "reason_code", "state", "action"),
    [
        (
            {
                "source_readiness_state": "INCOMPLETE",
                "missing_source_families": ["PRICE_COVERAGE"],
            },
            MandateHealthDimension.SOURCE_READINESS,
            "DPM_SOURCE_INCOMPLETE",
            MandateHealthState.BLOCKED,
            MandateRecommendedAction.FIX_SOURCE_DATA,
        ),
        (
            {"current_weights": {"EQ_US_AAPL": Decimal("0.72")}},
            MandateHealthDimension.ALLOCATION_DRIFT,
            "ALLOCATION_DRIFT",
            MandateHealthState.PENDING_REVIEW,
            MandateRecommendedAction.SIMULATE_REBALANCE,
        ),
        (
            {"tracking_error": Decimal("0.08")},
            MandateHealthDimension.RISK_DRIFT,
            "TRACKING_ERROR_ABOVE_LIMIT",
            MandateHealthState.PENDING_REVIEW,
            MandateRecommendedAction.SIMULATE_REBALANCE,
        ),
        (
            {"cash_weight": Decimal("0.00")},
            MandateHealthDimension.CASH_LIQUIDITY,
            "CASH_BELOW_BAND",
            MandateHealthState.PENDING_REVIEW,
            MandateRecommendedAction.SIMULATE_REBALANCE,
        ),
        (
            {"tax_lot_missing_security_ids": ["EQ_US_AAPL"]},
            MandateHealthDimension.TAX_TURNOVER,
            "TAX_LOTS_INCOMPLETE",
            MandateHealthState.BLOCKED,
            MandateRecommendedAction.REVIEW_MANDATE,
        ),
        (
            {"restricted_held_instruments": ["EQ_RESTRICTED"]},
            MandateHealthDimension.ELIGIBILITY_RESTRICTIONS,
            "RESTRICTED_INSTRUMENT_HELD",
            MandateHealthState.BLOCKED,
            MandateRecommendedAction.REVIEW_RESTRICTION,
        ),
        (
            {"performance_under_review": True},
            MandateHealthDimension.PERFORMANCE_ATTENTION,
            "PERFORMANCE_UNDER_REVIEW",
            MandateHealthState.PENDING_REVIEW,
            MandateRecommendedAction.SIMULATE_REBALANCE,
        ),
        (
            {"approval_required": True},
            MandateHealthDimension.WORKFLOW_READINESS,
            "APPROVAL_REQUIRED",
            MandateHealthState.PENDING_REVIEW,
            MandateRecommendedAction.REVIEW_WORKFLOW,
        ),
        (
            {
                "twin": _twin(
                    review_policy=DpmMandateReviewPolicy(next_review_due_date=date(2026, 4, 30))
                )
            },
            MandateHealthDimension.REVIEW_CADENCE,
            "MANDATE_REVIEW_OVERDUE",
            MandateHealthState.PENDING_REVIEW,
            MandateRecommendedAction.REVIEW_WORKFLOW,
        ),
        (
            {"model_effective_to": date(2026, 4, 30)},
            MandateHealthDimension.MODEL_FRESHNESS,
            "MODEL_VERSION_STALE",
            MandateHealthState.PENDING_REVIEW,
            MandateRecommendedAction.SIMULATE_REBALANCE,
        ),
    ],
)
def test_each_health_dimension_generates_domain_specific_attention(
    overrides: dict[str, Any],
    dimension: MandateHealthDimension,
    reason_code: str,
    state: MandateHealthState,
    action: MandateRecommendedAction,
) -> None:
    snapshot = calculate_mandate_health(_ready_input(**overrides))

    dimension_score = _dimension(snapshot, dimension)
    assert dimension_score.reason_code == reason_code
    assert dimension_score.state == state
    assert snapshot.health_score < 100
    assert any(reason.reason_code == reason_code for reason in snapshot.top_reasons)
    assert any(reason.recommended_action == action for reason in snapshot.top_reasons)


def test_hard_gate_overrides_high_remaining_scores() -> None:
    snapshot = calculate_mandate_health(_ready_input(restricted_held_instruments=["EQ_RESTRICTED"]))

    assert snapshot.health_state == MandateHealthState.BLOCKED
    assert snapshot.recommended_action == MandateRecommendedAction.REVIEW_RESTRICTION
    assert _dimension(snapshot, MandateHealthDimension.ELIGIBILITY_RESTRICTIONS).score == 0


def test_turnover_near_limit_is_pending_review_not_blocked() -> None:
    snapshot = calculate_mandate_health(_ready_input(turnover_budget_used=Decimal("0.13")))

    assert snapshot.health_state == MandateHealthState.PENDING_REVIEW
    assert _dimension(snapshot, MandateHealthDimension.TAX_TURNOVER).reason_code == (
        "TURNOVER_BUDGET_NEAR_LIMIT"
    )


def test_monitoring_exceptions_are_derived_from_health_reasons_with_lineage() -> None:
    twin = _twin()
    snapshot = calculate_mandate_health(
        _ready_input(twin=twin, restricted_held_instruments=["EQ_RESTRICTED"])
    )

    exceptions = monitoring_exceptions_from_health(
        snapshot,
        source_lineage=twin.source_lineage,
    )

    assert exceptions
    assert exceptions[0].portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert exceptions[0].dimension == MandateHealthDimension.ELIGIBILITY_RESTRICTIONS
    assert exceptions[0].reason_code == "RESTRICTED_INSTRUMENT_HELD"
