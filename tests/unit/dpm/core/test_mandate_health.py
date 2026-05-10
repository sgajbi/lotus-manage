from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from src.core.dpm_source_context import (
    DpmCoreClientRestrictionProfileResponse,
    DpmCoreMandateBindingResponse,
    DpmCoreMarketDataCoverageWindowResponse,
    DpmCoreModelPortfolioTargetResponse,
    DpmCorePortfolioCashflowProjectionResponse,
    DpmCoreSustainabilityPreferenceProfileResponse,
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


def _client_restriction_profile() -> DpmCoreClientRestrictionProfileResponse:
    return DpmCoreClientRestrictionProfileResponse.model_validate(
        {
            "product_name": "ClientRestrictionProfile",
            "product_version": "v1",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "client_id": "CIF_SG_000184",
            "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            "as_of_date": "2026-05-03",
            "restrictions": [
                {
                    "restriction_scope": "INSTRUMENT",
                    "restriction_code": "CLIENT_RESTRICTED_SECURITY",
                    "restriction_status": "ACTIVE",
                    "restriction_source": "CLIENT_PROFILE",
                    "applies_to_buy": True,
                    "applies_to_sell": False,
                    "instrument_ids": ["EQ_US_AAPL"],
                    "asset_classes": [],
                    "issuer_ids": [],
                    "country_codes": [],
                    "effective_from": "2026-04-01",
                    "restriction_version": 1,
                }
            ],
            "supportability": {
                "state": "READY",
                "reason": "CLIENT_RESTRICTION_PROFILE_READY",
                "restriction_count": 1,
                "missing_data_families": [],
            },
            "lineage": {"contract_version": "ClientRestrictionProfile:v1"},
            "data_quality_status": "READY",
            "latest_evidence_timestamp": "2026-05-03T01:05:00Z",
        }
    )


def _sustainability_preference_profile() -> DpmCoreSustainabilityPreferenceProfileResponse:
    return DpmCoreSustainabilityPreferenceProfileResponse.model_validate(
        {
            "product_name": "SustainabilityPreferenceProfile",
            "product_version": "v1",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "client_id": "CIF_SG_000184",
            "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            "as_of_date": "2026-05-03",
            "preferences": [
                {
                    "preference_framework": "BANK_SUSTAINABILITY",
                    "preference_code": "MIN_SUSTAINABLE_ALLOCATION",
                    "preference_status": "ACTIVE",
                    "preference_source": "CLIENT_PROFILE",
                    "minimum_allocation": "0.20",
                    "applies_to_asset_classes": ["EQUITY"],
                    "exclusion_codes": ["THERMAL_COAL"],
                    "positive_tilt_codes": [],
                    "effective_from": "2026-04-01",
                    "preference_version": 1,
                }
            ],
            "supportability": {
                "state": "READY",
                "reason": "SUSTAINABILITY_PREFERENCE_PROFILE_READY",
                "preference_count": 1,
                "missing_data_families": [],
            },
            "lineage": {"contract_version": "SustainabilityPreferenceProfile:v1"},
            "data_quality_status": "READY",
            "latest_evidence_timestamp": "2026-05-03T01:05:00Z",
        }
    )


def _inactive_sustainability_preference_profile() -> DpmCoreSustainabilityPreferenceProfileResponse:
    return DpmCoreSustainabilityPreferenceProfileResponse.model_validate(
        {
            "product_name": "SustainabilityPreferenceProfile",
            "product_version": "v1",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "client_id": "CIF_SG_000184",
            "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            "as_of_date": "2026-05-03",
            "preferences": [
                {
                    "preference_framework": "BANK_SUSTAINABILITY",
                    "preference_code": "LEGACY_EXCLUSION",
                    "preference_status": "INACTIVE",
                    "preference_source": "CLIENT_PROFILE",
                    "exclusion_codes": ["THERMAL_COAL"],
                    "positive_tilt_codes": [],
                    "effective_from": "2025-01-01",
                    "effective_to": "2026-01-01",
                    "preference_version": 1,
                }
            ],
            "supportability": {
                "state": "READY",
                "reason": "SUSTAINABILITY_PREFERENCE_PROFILE_READY",
                "preference_count": 1,
                "missing_data_families": [],
            },
            "lineage": {"contract_version": "SustainabilityPreferenceProfile:v1"},
            "data_quality_status": "READY",
            "latest_evidence_timestamp": "2026-05-03T01:05:00Z",
        }
    )


def _portfolio_cashflow_projection() -> DpmCorePortfolioCashflowProjectionResponse:
    return DpmCorePortfolioCashflowProjectionResponse.model_validate(
        {
            "product_name": "PortfolioCashflowProjection",
            "product_version": "v1",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "as_of_date": "2026-05-03",
            "range_start_date": "2026-05-03",
            "range_end_date": "2026-08-01",
            "include_projected": True,
            "portfolio_currency": "SGD",
            "points": [
                {
                    "projection_date": "2026-05-10",
                    "net_cashflow": "-25000.00",
                    "projected_cumulative_cashflow": "-25000.00",
                }
            ],
            "total_net_cashflow": "-25000.00",
            "projection_days": 90,
            "lineage": {"contract_version": "PortfolioCashflowProjection:v1"},
            "data_quality_status": "READY",
            "latest_evidence_timestamp": "2026-05-03T01:05:00Z",
        }
    )


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


def test_compile_mandate_twin_preserves_client_profile_cashflow_and_sustainability_lineage() -> (
    None
):
    twin = compile_mandate_digital_twin_from_core(
        mandate=_mandate_binding(),
        model_targets=_model_targets(),
        as_of_date=AS_OF,
        client_restriction_profile=_client_restriction_profile(),
        sustainability_preference_profile=_sustainability_preference_profile(),
        portfolio_cashflow_projection=_portfolio_cashflow_projection(),
    )

    assert "EQ_US_AAPL" in twin.constraints.restricted_instruments
    assert twin.preferences.sustainability_strategy == "BANK_SUSTAINABILITY"
    assert "MIN_SUSTAINABLE_ALLOCATION" in twin.preferences.bespoke_notes
    assert "CLIENT_RESTRICTION_PROFILE_NOT_YET_SOURCED" not in twin.field_gap_codes
    assert "SUSTAINABILITY_PREFERENCE_PROFILE_NOT_YET_SOURCED" not in twin.field_gap_codes
    assert "PORTFOLIO_CASHFLOW_PROJECTION_NOT_YET_SOURCED" not in twin.field_gap_codes
    assert [lineage.product_name for lineage in twin.source_lineage] == [
        "DiscretionaryMandateBinding",
        "DpmModelPortfolioTarget",
        "ClientRestrictionProfile",
        "SustainabilityPreferenceProfile",
        "PortfolioCashflowProjection",
    ]


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


def test_build_health_input_uses_source_backed_profile_and_cashflow_risk_signals() -> None:
    twin = compile_mandate_digital_twin_from_core(
        mandate=_mandate_binding(),
        model_targets=_model_targets(),
        as_of_date=AS_OF,
        client_restriction_profile=_client_restriction_profile(),
        sustainability_preference_profile=_sustainability_preference_profile(),
        portfolio_cashflow_projection=_portfolio_cashflow_projection(),
    )
    health_input = build_health_input_from_core_sources(
        twin=twin,
        model_targets=_model_targets(),
        client_restriction_profile=_client_restriction_profile(),
        sustainability_preference_profile=_sustainability_preference_profile(),
        portfolio_cashflow_projection=_portfolio_cashflow_projection(),
    ).model_copy(update={"cash_weight": Decimal("0.05")})

    snapshot = calculate_mandate_health(health_input)

    assert (
        _dimension(snapshot, MandateHealthDimension.ELIGIBILITY_RESTRICTIONS).reason_code
        == "RESTRICTED_INSTRUMENT_HELD"
    )
    assert _dimension(snapshot, MandateHealthDimension.CASH_LIQUIDITY).reason_code == (
        "PROJECTED_CASHFLOW_PRESSURE"
    )
    assert _dimension(snapshot, MandateHealthDimension.WORKFLOW_READINESS).reason_code == (
        "SUSTAINABILITY_REVIEW_REQUIRED"
    )


def test_inactive_sustainability_preferences_do_not_create_review_posture() -> None:
    profile = _inactive_sustainability_preference_profile()
    twin = compile_mandate_digital_twin_from_core(
        mandate=_mandate_binding(),
        model_targets=_model_targets(),
        as_of_date=AS_OF,
        sustainability_preference_profile=profile,
    )
    health_input = build_health_input_from_core_sources(
        twin=twin,
        model_targets=_model_targets(),
        sustainability_preference_profile=profile,
    )

    assert twin.preferences.sustainability_strategy is None
    assert health_input.sustainability_review_required is False


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
    with pytest.raises(ValueError, match="max_tracking_error must be between"):
        DpmMandateConstraintSet(max_tracking_error=Decimal("2"))
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
