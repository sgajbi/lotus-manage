from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from src.core.dpm_source_context import (
    DpmCoreBenchmarkAssignmentResponse,
    DpmCoreClientIncomeNeedsScheduleResponse,
    DpmCoreClientRestrictionProfileResponse,
    DpmCoreLiquidityReserveRequirementResponse,
    DpmCoreMandateBindingResponse,
    DpmCoreMarketDataCoverageWindowResponse,
    DpmCoreModelPortfolioTargetResponse,
    DpmCorePlannedWithdrawalScheduleResponse,
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
    DpmMandateSourceHealthContext,
    MandateHealthDimension,
    MandateHealthState,
    MandateRecommendedAction,
    _benchmark_assignment_source_lineage,
    _benchmark_assignment_source_record_id,
    _build_digital_twin_source_lineage,
    _health_input_source_readiness,
    _mandate_twin_constraint_set,
    _mandate_binding_profile_gap_codes,
    _mandate_twin_preferences,
    _mandate_optional_source_product_gap_codes,
    _mandate_source_schedule_gap_codes,
    _mandate_twin_field_gap_codes,
    _market_data_source_readiness,
    _optional_digital_twin_source_lineage,
    _requires_sustainability_review,
    calculate_mandate_health,
    build_health_input_from_core_sources,
    compile_mandate_digital_twin_from_core,
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
        "mandate_objective": (
            "Preserve and grow global balanced wealth within controlled drawdown limits."
        ),
        "risk_profile": "balanced",
        "investment_horizon": "long_term",
        "review_cadence": "quarterly",
        "last_review_date": "2026-03-31",
        "next_review_due_date": "2026-06-30",
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


def _benchmark_assignment(**overrides: object) -> DpmCoreBenchmarkAssignmentResponse:
    payload: dict[str, Any] = {
        "product_name": "BenchmarkAssignment",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "benchmark_id": "BMK_PB_GLOBAL_BALANCED_60_40",
        "as_of_date": "2026-05-03",
        "effective_from": "2026-01-01",
        "assignment_source": "mandate_admin",
        "assignment_status": "active",
        "source_system": "lotus-core",
        "assignment_recorded_at": "2026-05-03T01:00:00Z",
        "assignment_version": 1,
        "contract_version": "rfc_062_v1",
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-05-03T01:00:00Z",
    }
    payload.update(overrides)
    return DpmCoreBenchmarkAssignmentResponse.model_validate(payload)


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


def _client_restriction_profile(
    **overrides: object,
) -> DpmCoreClientRestrictionProfileResponse:
    payload: dict[str, object] = {
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
    payload.update(overrides)
    return DpmCoreClientRestrictionProfileResponse.model_validate(payload)


def _sustainability_preference_profile(
    **overrides: object,
) -> DpmCoreSustainabilityPreferenceProfileResponse:
    payload: dict[str, object] = {
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
    payload.update(overrides)
    return DpmCoreSustainabilityPreferenceProfileResponse.model_validate(payload)


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


def _client_income_needs_schedule() -> DpmCoreClientIncomeNeedsScheduleResponse:
    return DpmCoreClientIncomeNeedsScheduleResponse.model_validate(
        {
            "product_name": "ClientIncomeNeedsSchedule",
            "product_version": "v1",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "client_id": "CIF_SG_000184",
            "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            "as_of_date": "2026-05-03",
            "schedules": [
                {
                    "schedule_id": "income-need-001",
                    "need_type": "RETIREMENT_INCOME",
                    "need_status": "active",
                    "amount": "12000.00",
                    "currency": "SGD",
                    "frequency": "monthly",
                    "start_date": "2026-05-01",
                    "priority": 1,
                }
            ],
            "supportability": {
                "state": "READY",
                "reason": "CLIENT_INCOME_NEEDS_SCHEDULE_READY",
                "schedule_count": 1,
            },
            "lineage": {"contract_version": "ClientIncomeNeedsSchedule:v1"},
            "data_quality_status": "READY",
            "latest_evidence_timestamp": "2026-05-03T01:05:00Z",
        }
    )


def _liquidity_reserve_requirement() -> DpmCoreLiquidityReserveRequirementResponse:
    return DpmCoreLiquidityReserveRequirementResponse.model_validate(
        {
            "product_name": "LiquidityReserveRequirement",
            "product_version": "v1",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "client_id": "CIF_SG_000184",
            "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            "as_of_date": "2026-05-03",
            "requirements": [
                {
                    "reserve_requirement_id": "reserve-001",
                    "reserve_type": "CLIENT_LIQUIDITY_RESERVE",
                    "reserve_status": "active",
                    "required_amount": "50000.00",
                    "currency": "SGD",
                    "horizon_days": 90,
                    "priority": 1,
                    "policy_source": "BANK_APPROVED_RESERVE_POLICY",
                    "effective_from": "2026-01-01",
                    "requirement_version": 1,
                }
            ],
            "supportability": {
                "state": "READY",
                "reason": "LIQUIDITY_RESERVE_REQUIREMENT_READY",
                "requirement_count": 1,
            },
            "lineage": {"contract_version": "LiquidityReserveRequirement:v1"},
            "data_quality_status": "READY",
            "latest_evidence_timestamp": "2026-05-03T01:05:00Z",
        }
    )


def _planned_withdrawal_schedule() -> DpmCorePlannedWithdrawalScheduleResponse:
    return DpmCorePlannedWithdrawalScheduleResponse.model_validate(
        {
            "product_name": "PlannedWithdrawalSchedule",
            "product_version": "v1",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "client_id": "CIF_SG_000184",
            "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            "as_of_date": "2026-05-03",
            "horizon_days": 365,
            "withdrawals": [
                {
                    "withdrawal_schedule_id": "withdrawal-001",
                    "withdrawal_type": "CLIENT_DRAWDOWN",
                    "withdrawal_status": "planned",
                    "amount": "25000.00",
                    "currency": "SGD",
                    "scheduled_date": "2026-06-01",
                }
            ],
            "supportability": {
                "state": "READY",
                "reason": "PLANNED_WITHDRAWAL_SCHEDULE_READY",
                "withdrawal_count": 1,
            },
            "lineage": {"contract_version": "PlannedWithdrawalSchedule:v1"},
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
        benchmark_assignment=_benchmark_assignment(),
    )

    assert twin.mandate_id == "MANDATE_PB_SG_GLOBAL_BAL_001"
    assert twin.portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert twin.model_portfolio_id == "MODEL_PB_SG_GLOBAL_BAL_DPM"
    assert twin.benchmark_id == "BMK_PB_GLOBAL_BALANCED_60_40"
    assert twin.base_currency == "SGD"
    assert twin.investment_objective == (
        "Preserve and grow global balanced wealth within controlled drawdown limits."
    )
    assert twin.constraints.cash_band_min_weight == Decimal("0.0200000000")
    assert twin.review_policy.review_frequency == "QUARTERLY"
    assert twin.review_policy.last_review_date == date(2026, 3, 31)
    assert twin.review_policy.next_review_due_date == date(2026, 6, 30)
    assert [lineage.product_name for lineage in twin.source_lineage] == [
        "DiscretionaryMandateBinding",
        "DpmModelPortfolioTarget",
        "BenchmarkAssignment",
    ]
    assert "MANDATE_OBJECTIVE_PROFILE_NOT_YET_SOURCED" not in twin.field_gap_codes
    assert "MANDATE_REVIEW_SCHEDULE_NOT_YET_SOURCED" not in twin.field_gap_codes


def test_compile_mandate_twin_preserves_explicit_gap_codes_for_missing_profile_fields() -> None:
    twin = compile_mandate_digital_twin_from_core(
        mandate=_mandate_binding(
            mandate_objective=None,
            review_cadence=None,
            next_review_due_date=None,
        ),
        model_targets=_model_targets(),
        as_of_date=AS_OF,
    )

    assert twin.investment_objective == "LONG_TERM_TOTAL_RETURN"
    assert twin.review_policy.review_frequency == "QUARTERLY"
    assert "MANDATE_OBJECTIVE_PROFILE_NOT_YET_SOURCED" in twin.field_gap_codes
    assert "MANDATE_REVIEW_SCHEDULE_NOT_YET_SOURCED" in twin.field_gap_codes
    assert "BENCHMARK_ASSIGNMENT_NOT_YET_SOURCED" in twin.field_gap_codes


def test_mandate_twin_field_gap_codes_project_missing_core_products() -> None:
    assert _mandate_twin_field_gap_codes(
        mandate=_mandate_binding(
            mandate_objective=None,
            review_cadence=None,
            next_review_due_date=None,
        ),
        client_restriction_profile=None,
        sustainability_preference_profile=None,
        portfolio_cashflow_projection=None,
        client_income_needs_schedule=None,
        liquidity_reserve_requirement=None,
        planned_withdrawal_schedule=None,
        benchmark_assignment=None,
    ) == [
        "CLIENT_INCOME_NEED_PROFILE_NOT_YET_SOURCED",
        "LIQUIDITY_RESERVE_REQUIREMENT_NOT_YET_SOURCED",
        "PLANNED_WITHDRAWAL_SCHEDULE_NOT_YET_SOURCED",
        "MANDATE_OBJECTIVE_PROFILE_NOT_YET_SOURCED",
        "MANDATE_REVIEW_SCHEDULE_NOT_YET_SOURCED",
        "CLIENT_RESTRICTION_PROFILE_NOT_YET_SOURCED",
        "SUSTAINABILITY_PREFERENCE_PROFILE_NOT_YET_SOURCED",
        "PORTFOLIO_CASHFLOW_PROJECTION_NOT_YET_SOURCED",
        "BENCHMARK_ASSIGNMENT_NOT_YET_SOURCED",
    ]


def test_mandate_source_schedule_gap_codes_project_missing_source_products() -> None:
    assert _mandate_source_schedule_gap_codes(
        client_income_needs_schedule=None,
        liquidity_reserve_requirement=None,
        planned_withdrawal_schedule=None,
    ) == [
        "CLIENT_INCOME_NEED_PROFILE_NOT_YET_SOURCED",
        "LIQUIDITY_RESERVE_REQUIREMENT_NOT_YET_SOURCED",
        "PLANNED_WITHDRAWAL_SCHEDULE_NOT_YET_SOURCED",
    ]
    assert (
        _mandate_source_schedule_gap_codes(
            client_income_needs_schedule=_client_income_needs_schedule(),
            liquidity_reserve_requirement=_liquidity_reserve_requirement(),
            planned_withdrawal_schedule=_planned_withdrawal_schedule(),
        )
        == []
    )


def test_mandate_binding_profile_gap_codes_project_missing_profile_fields() -> None:
    assert _mandate_binding_profile_gap_codes(
        _mandate_binding(
            mandate_objective=None,
            review_cadence=None,
            next_review_due_date=None,
        )
    ) == [
        "MANDATE_OBJECTIVE_PROFILE_NOT_YET_SOURCED",
        "MANDATE_REVIEW_SCHEDULE_NOT_YET_SOURCED",
    ]
    assert _mandate_binding_profile_gap_codes(_mandate_binding()) == []


def test_mandate_optional_source_product_gap_codes_project_missing_products() -> None:
    assert _mandate_optional_source_product_gap_codes(
        client_restriction_profile=None,
        sustainability_preference_profile=None,
        portfolio_cashflow_projection=None,
        benchmark_assignment=None,
    ) == [
        "CLIENT_RESTRICTION_PROFILE_NOT_YET_SOURCED",
        "SUSTAINABILITY_PREFERENCE_PROFILE_NOT_YET_SOURCED",
        "PORTFOLIO_CASHFLOW_PROJECTION_NOT_YET_SOURCED",
        "BENCHMARK_ASSIGNMENT_NOT_YET_SOURCED",
    ]
    assert (
        _mandate_optional_source_product_gap_codes(
            client_restriction_profile=_client_restriction_profile(),
            sustainability_preference_profile=_sustainability_preference_profile(),
            portfolio_cashflow_projection=_portfolio_cashflow_projection(),
            benchmark_assignment=_benchmark_assignment(),
        )
        == []
    )


def test_mandate_twin_field_gap_codes_clear_when_core_products_are_sourced() -> None:
    assert (
        _mandate_twin_field_gap_codes(
            mandate=_mandate_binding(),
            client_restriction_profile=_client_restriction_profile(),
            sustainability_preference_profile=_sustainability_preference_profile(),
            portfolio_cashflow_projection=_portfolio_cashflow_projection(),
            client_income_needs_schedule=_client_income_needs_schedule(),
            liquidity_reserve_requirement=_liquidity_reserve_requirement(),
            planned_withdrawal_schedule=_planned_withdrawal_schedule(),
            benchmark_assignment=_benchmark_assignment(),
        )
        == []
    )


def test_mandate_twin_constraint_set_projects_cash_band_and_active_restrictions() -> None:
    constraints = _mandate_twin_constraint_set(
        mandate=_mandate_binding(
            rebalance_bands={
                "default_band": "0.0250000000",
                "cash_reserve_weight": "0.1200000000",
            }
        ),
        client_restriction_profile=_client_restriction_profile(
            restrictions=[
                {
                    "restriction_scope": "instrument",
                    "restriction_code": "NO_SINGLE_NAME_EQUITY",
                    "restriction_status": "ACTIVE",
                    "restriction_source": "client_mandate",
                    "applies_to_buy": True,
                    "applies_to_sell": False,
                    "instrument_ids": ["EQ_US_MSFT", "EQ_US_AAPL"],
                    "asset_classes": [],
                    "issuer_ids": [],
                    "country_codes": [],
                    "effective_from": "2026-04-01",
                    "restriction_version": 1,
                    "source_record_id": "restriction-active",
                },
                {
                    "restriction_scope": "instrument",
                    "restriction_code": "LEGACY_RESTRICTION",
                    "restriction_status": "INACTIVE",
                    "restriction_source": "client_mandate",
                    "applies_to_buy": True,
                    "applies_to_sell": False,
                    "instrument_ids": ["EQ_US_TSLA"],
                    "asset_classes": [],
                    "issuer_ids": [],
                    "country_codes": [],
                    "effective_from": "2025-01-01",
                    "effective_to": "2026-01-01",
                    "restriction_version": 1,
                    "source_record_id": "restriction-inactive",
                },
            ]
        ),
    )

    assert constraints.cash_band_min_weight == Decimal("0.1200000000")
    assert constraints.cash_band_max_weight == Decimal("0.1200000000")
    assert constraints.turnover_budget == Decimal("0.15")
    assert constraints.restricted_instruments == ["EQ_US_AAPL", "EQ_US_MSFT"]


def test_mandate_twin_preferences_project_active_sustainability_preferences() -> None:
    preferences = _mandate_twin_preferences(
        _sustainability_preference_profile(
            preferences=[
                {
                    "preference_framework": "BANK_SUSTAINABILITY",
                    "preference_code": "MIN_SUSTAINABLE_ALLOCATION",
                    "preference_status": "ACTIVE",
                    "preference_source": "CLIENT_PROFILE",
                    "minimum_allocation": "0.3000000000",
                    "applies_to_asset_classes": ["EQUITY"],
                    "exclusion_codes": [],
                    "positive_tilt_codes": [],
                    "effective_from": "2026-04-01",
                    "preference_version": 1,
                    "source_record_id": "sustainability-active",
                },
                {
                    "preference_framework": "BANK_SUSTAINABILITY",
                    "preference_code": "LEGACY_EXCLUSION",
                    "preference_status": "INACTIVE",
                    "preference_source": "CLIENT_PROFILE",
                    "minimum_allocation": "0.1000000000",
                    "applies_to_asset_classes": ["EQUITY"],
                    "exclusion_codes": [],
                    "positive_tilt_codes": [],
                    "effective_from": "2025-01-01",
                    "effective_to": "2026-01-01",
                    "preference_version": 1,
                    "source_record_id": "sustainability-inactive",
                },
            ]
        )
    )

    assert preferences.sustainability_strategy == "BANK_SUSTAINABILITY"
    assert preferences.bespoke_notes == ["MIN_SUSTAINABLE_ALLOCATION"]


def test_build_digital_twin_source_lineage_includes_all_core_products() -> None:
    benchmark = _benchmark_assignment()
    lineage = _build_digital_twin_source_lineage(
        mandate=_mandate_binding(),
        model_targets=_model_targets(),
        client_restriction_profile=_client_restriction_profile(),
        sustainability_preference_profile=_sustainability_preference_profile(),
        portfolio_cashflow_projection=_portfolio_cashflow_projection(),
        client_income_needs_schedule=_client_income_needs_schedule(),
        liquidity_reserve_requirement=_liquidity_reserve_requirement(),
        planned_withdrawal_schedule=_planned_withdrawal_schedule(),
        benchmark_assignment=benchmark,
    )

    assert [entry.product_name for entry in lineage] == [
        "DiscretionaryMandateBinding",
        "DpmModelPortfolioTarget",
        "ClientRestrictionProfile",
        "SustainabilityPreferenceProfile",
        "PortfolioCashflowProjection",
        "ClientIncomeNeedsSchedule",
        "LiquidityReserveRequirement",
        "PlannedWithdrawalSchedule",
        benchmark.product_name,
    ]
    assert lineage[-1].source_record_id == (
        "PB_SG_GLOBAL_BAL_001:BMK_PB_GLOBAL_BALANCED_60_40:2026-01-01:1"
    )


def test_optional_digital_twin_source_lineage_skips_missing_products() -> None:
    lineage = _optional_digital_twin_source_lineage(
        _client_restriction_profile(),
        None,
        _portfolio_cashflow_projection(),
    )

    assert [entry.product_name for entry in lineage] == [
        "ClientRestrictionProfile",
        "PortfolioCashflowProjection",
    ]


def test_benchmark_assignment_source_lineage_preserves_source_identity() -> None:
    benchmark = _benchmark_assignment()

    assert _benchmark_assignment_source_record_id(benchmark) == (
        "PB_SG_GLOBAL_BAL_001:BMK_PB_GLOBAL_BALANCED_60_40:2026-01-01:1"
    )
    lineage = _benchmark_assignment_source_lineage(benchmark)
    assert lineage.product_name == benchmark.product_name
    assert lineage.source_system == "lotus-core"
    assert lineage.lineage == {"contract_version": benchmark.contract_version}


def test_build_digital_twin_source_lineage_includes_only_required_products_when_optionals_missing() -> (
    None
):
    lineage = _build_digital_twin_source_lineage(
        mandate=_mandate_binding(),
        model_targets=_model_targets(),
    )

    assert [entry.product_name for entry in lineage] == [
        "DiscretionaryMandateBinding",
        "DpmModelPortfolioTarget",
    ]
    assert all(entry.lineage.get("contract_version") for entry in lineage)


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
        client_income_needs_schedule=_client_income_needs_schedule(),
        liquidity_reserve_requirement=_liquidity_reserve_requirement(),
        planned_withdrawal_schedule=_planned_withdrawal_schedule(),
    )

    assert "EQ_US_AAPL" in twin.constraints.restricted_instruments
    assert twin.preferences.sustainability_strategy == "BANK_SUSTAINABILITY"
    assert "MIN_SUSTAINABLE_ALLOCATION" in twin.preferences.bespoke_notes
    assert "CLIENT_RESTRICTION_PROFILE_NOT_YET_SOURCED" not in twin.field_gap_codes
    assert "SUSTAINABILITY_PREFERENCE_PROFILE_NOT_YET_SOURCED" not in twin.field_gap_codes
    assert "PORTFOLIO_CASHFLOW_PROJECTION_NOT_YET_SOURCED" not in twin.field_gap_codes
    assert "CLIENT_INCOME_NEED_PROFILE_NOT_YET_SOURCED" not in twin.field_gap_codes
    assert "LIQUIDITY_RESERVE_REQUIREMENT_NOT_YET_SOURCED" not in twin.field_gap_codes
    assert "PLANNED_WITHDRAWAL_SCHEDULE_NOT_YET_SOURCED" not in twin.field_gap_codes
    assert [lineage.product_name for lineage in twin.source_lineage] == [
        "DiscretionaryMandateBinding",
        "DpmModelPortfolioTarget",
        "ClientRestrictionProfile",
        "SustainabilityPreferenceProfile",
        "PortfolioCashflowProjection",
        "ClientIncomeNeedsSchedule",
        "LiquidityReserveRequirement",
        "PlannedWithdrawalSchedule",
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


def test_market_data_source_readiness_projects_missing_stale_and_degraded_sources() -> None:
    readiness = _market_data_source_readiness(
        _market_data_coverage(
            supportability={
                "state": "DEGRADED",
                "reason": "MARKET_DATA_PARTIAL",
                "requested_price_count": 2,
                "resolved_price_count": 1,
                "requested_fx_count": 1,
                "resolved_fx_count": 0,
                "missing_instrument_ids": ["FI_US_TREASURY_10Y"],
                "missing_currency_pairs": ["USD/SGD"],
                "stale_instrument_ids": ["EQ_US_AAPL"],
                "stale_currency_pairs": ["EUR/SGD"],
            }
        )
    )

    assert readiness.state == "DEGRADED"
    assert readiness.missing_source_families == ["FI_US_TREASURY_10Y", "USD/SGD"]
    assert readiness.degraded_source_families == ["MARKET_DATA_COVERAGE"]
    assert readiness.stale_source_families == ["EQ_US_AAPL", "EUR/SGD"]


def test_health_input_source_readiness_degrades_ready_only_for_unavailable_optionals() -> None:
    ready_readiness = _health_input_source_readiness(
        market_data_coverage=None,
        unavailable_source_families=["CLIENT_RESTRICTION_PROFILE"],
    )
    incomplete_readiness = _health_input_source_readiness(
        market_data_coverage=_market_data_coverage(
            supportability={
                "state": "INCOMPLETE",
                "reason": "PRICE_MISSING",
                "requested_price_count": 2,
                "resolved_price_count": 1,
                "requested_fx_count": 0,
                "resolved_fx_count": 0,
                "missing_instrument_ids": ["EQ_US_AAPL"],
            }
        ),
        unavailable_source_families=["SUSTAINABILITY_PREFERENCE_PROFILE"],
    )

    assert ready_readiness.state == "DEGRADED"
    assert ready_readiness.degraded_source_families == ["CLIENT_RESTRICTION_PROFILE"]
    assert incomplete_readiness.state == "INCOMPLETE"
    assert incomplete_readiness.missing_source_families == ["EQ_US_AAPL"]
    assert incomplete_readiness.degraded_source_families == ["SUSTAINABILITY_PREFERENCE_PROFILE"]


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


@pytest.mark.parametrize(
    "preference_updates",
    [
        {"minimum_allocation": "0.20"},
        {"maximum_allocation": "0.70"},
        {"exclusion_codes": ["THERMAL_COAL"]},
        {"positive_tilt_codes": ["LOW_CARBON"]},
    ],
)
def test_sustainability_review_required_for_active_source_controls(
    preference_updates: dict[str, object],
) -> None:
    base_preference: dict[str, object] = {
        "preference_framework": "BANK_SUSTAINABILITY",
        "preference_code": "SOURCE_CONTROL",
        "preference_status": "ACTIVE",
        "preference_source": "CLIENT_PROFILE",
        "minimum_allocation": None,
        "maximum_allocation": None,
        "applies_to_asset_classes": ["EQUITY"],
        "exclusion_codes": [],
        "positive_tilt_codes": [],
        "effective_from": "2026-04-01",
        "preference_version": 1,
    }
    base_preference.update(preference_updates)

    assert _requires_sustainability_review(
        _sustainability_preference_profile(preferences=[base_preference])
    )


def test_sustainability_review_ignores_missing_inactive_and_control_free_preferences() -> None:
    control_free_active = {
        "preference_framework": "BANK_SUSTAINABILITY",
        "preference_code": "DISCLOSURE_ONLY",
        "preference_status": "ACTIVE",
        "preference_source": "CLIENT_PROFILE",
        "applies_to_asset_classes": ["EQUITY"],
        "exclusion_codes": [],
        "positive_tilt_codes": [],
        "effective_from": "2026-04-01",
        "preference_version": 1,
    }

    assert _requires_sustainability_review(None) is False
    assert _requires_sustainability_review(_inactive_sustainability_preference_profile()) is False
    assert (
        _requires_sustainability_review(
            _sustainability_preference_profile(preferences=[control_free_active])
        )
        is False
    )


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


def test_mandate_health_preserves_risk_performance_source_analytics_posture() -> None:
    snapshot = calculate_mandate_health(
        _ready_input(tracking_error=Decimal("0.08"), performance_under_review=True)
    )

    posture = snapshot.source_analytics_posture

    assert posture.product_family == "MANDATE_HEALTH_RISK_PERFORMANCE_CONTEXT"
    assert posture.risk_tracking_error_supplied is True
    assert posture.performance_attention_signal_supplied is True
    assert posture.risk_health_context_supplied is False
    assert posture.performance_health_context_supplied is False
    assert posture.risk_context_preservation == "SUPPORTED_WHEN_SUPPLIED"
    assert posture.performance_context_preservation == "SUPPORTED_WHEN_SUPPLIED"
    assert posture.source_context_preservation == "SOURCE_PRODUCT_CONTEXT_PRESERVED_WHEN_SUPPLIED"
    assert posture.source_context_refs == []
    assert [product.model_dump() for product in posture.required_source_products] == [
        {
            "source_system": "lotus-risk",
            "source_product_name": "MandateRiskHealthContext",
            "source_product_version": "v1",
            "required_for_ready": False,
        },
        {
            "source_system": "lotus-performance",
            "source_product_name": "MandatePerformanceHealthContext",
            "source_product_version": "v1",
            "required_for_ready": False,
        },
    ]
    assert "LOCAL_TRACKING_ERROR_CALCULATION" in posture.blocked_capabilities
    assert "LOCAL_PERFORMANCE_ATTRIBUTION_CALCULATION" in posture.blocked_capabilities
    assert "RISK_PERFORMANCE_METHODOLOGY_REMAINS_SOURCE_OWNED" in posture.reason_codes


def test_mandate_health_preserves_source_product_health_contexts() -> None:
    risk_fingerprint = "sha256:risk-context"
    performance_fingerprint = "sha256:performance-context"
    snapshot = calculate_mandate_health(
        _ready_input(
            risk_health_context={
                "source_system": "lotus-risk",
                "source_product_name": "MandateRiskHealthContext",
                "source_product_version": "v1",
                "as_of_date": "2026-05-03",
                "health_state": "attention",
                "threshold_breached": True,
                "request_fingerprint": risk_fingerprint,
                "source_metric": {"tracking_error": "0.073"},
                "methodology_posture": {
                    "methodology_owner": "lotus-risk",
                    "methodology_ref": "tracking-error-v1",
                },
                "benchmark_context": {"benchmark_id": "BMK_PB_GLOBAL_BALANCED_60_40"},
                "reason_codes": ["TRACKING_ERROR_ABOVE_LIMIT"],
            },
            performance_health_context={
                "source_system": "lotus-performance",
                "source_product_name": "MandatePerformanceHealthContext",
                "source_product_version": "v1",
                "as_of_date": "2026-05-03",
                "health_state": "attention",
                "threshold_breached": True,
                "request_fingerprint": performance_fingerprint,
                "source_metric": {"active_return": "-0.021"},
                "methodology_posture": {
                    "methodology_owner": "lotus-performance",
                    "methodology_ref": "active-return-v1",
                },
                "benchmark_context": {"benchmark_id": "BMK_PB_GLOBAL_BALANCED_60_40"},
                "reason_codes": ["ACTIVE_RETURN_BELOW_THRESHOLD"],
            },
        )
    )

    posture = snapshot.source_analytics_posture
    risk_ref = f"lotus-risk:MandateRiskHealthContext:v1:{risk_fingerprint}"
    performance_ref = (
        f"lotus-performance:MandatePerformanceHealthContext:v1:{performance_fingerprint}"
    )

    assert posture.risk_tracking_error_supplied is True
    assert posture.performance_attention_signal_supplied is True
    assert posture.risk_health_context_supplied is True
    assert posture.performance_health_context_supplied is True
    assert posture.source_context_refs == [risk_ref, performance_ref]
    assert [metadata.model_dump(mode="json") for metadata in posture.source_context_metadata] == [
        {
            "source_ref": risk_ref,
            "source_system": "lotus-risk",
            "source_product_name": "MandateRiskHealthContext",
            "source_product_version": "v1",
            "request_fingerprint": risk_fingerprint,
            "as_of_date": "2026-05-03",
        },
        {
            "source_ref": performance_ref,
            "source_system": "lotus-performance",
            "source_product_name": "MandatePerformanceHealthContext",
            "source_product_version": "v1",
            "request_fingerprint": performance_fingerprint,
            "as_of_date": "2026-05-03",
        },
    ]
    assert "MANDATE_RISK_HEALTH_CONTEXT_SOURCE_PRODUCT_PRESERVED" in posture.reason_codes
    assert "MANDATE_PERFORMANCE_HEALTH_CONTEXT_SOURCE_PRODUCT_PRESERVED" in posture.reason_codes

    risk_score = _dimension(snapshot, MandateHealthDimension.RISK_DRIFT)
    performance_score = _dimension(snapshot, MandateHealthDimension.PERFORMANCE_ATTENTION)
    assert risk_score.state == MandateHealthState.PENDING_REVIEW
    assert risk_score.reason_code == "SOURCE_RISK_HEALTH_ATTENTION"
    assert risk_score.evidence_refs == [risk_ref]
    assert performance_score.state == MandateHealthState.PENDING_REVIEW
    assert performance_score.reason_code == "SOURCE_PERFORMANCE_HEALTH_ATTENTION"
    assert performance_score.evidence_refs == [performance_ref]


def test_source_health_context_rejects_wrong_product_identity() -> None:
    with pytest.raises(
        ValueError,
        match="lotus-risk context must use MandateRiskHealthContext",
    ):
        DpmMandateSourceHealthContext.model_validate(
            {
                "source_system": "lotus-risk",
                "source_product_name": "MandatePerformanceHealthContext",
                "health_state": "ready",
                "request_fingerprint": "sha256:risk-context",
            }
        )


@pytest.mark.parametrize("request_fingerprint", ["sha256:", "sha256:   "])
def test_source_health_context_rejects_empty_sha256_fingerprint(
    request_fingerprint: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="request_fingerprint must be a non-empty sha256 fingerprint",
    ):
        DpmMandateSourceHealthContext.model_validate(
            {
                "source_system": "lotus-risk",
                "source_product_name": "MandateRiskHealthContext",
                "health_state": "ready",
                "request_fingerprint": request_fingerprint,
            }
        )


def test_mandate_health_input_rejects_source_context_in_wrong_slot() -> None:
    with pytest.raises(
        ValueError,
        match="risk_health_context must use lotus-risk MandateRiskHealthContext",
    ):
        _ready_input(
            risk_health_context={
                "source_system": "lotus-performance",
                "source_product_name": "MandatePerformanceHealthContext",
                "health_state": "ready",
                "request_fingerprint": "sha256:performance-context",
            }
        )


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
