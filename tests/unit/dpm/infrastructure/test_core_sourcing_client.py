from datetime import date
from decimal import Decimal

import httpx
import pytest

from src.core.dpm_source_context import DpmStatefulInput
from src.infrastructure.core_sourcing import (
    DpmCoreResolverClient,
    DpmCoreResolverConfig,
    DpmCoreResolverError,
    DpmCoreResolverUnavailableError,
)


def _context_payload() -> dict:
    return {
        "portfolio_snapshot": {
            "snapshot_id": "core-pf-snap-001",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "base_currency": "SGD",
            "positions": [{"instrument_id": "EQ_1", "quantity": "100"}],
            "cash_balances": [{"currency": "SGD", "amount": "10000"}],
        },
        "market_data_snapshot": {
            "snapshot_id": "core-md-snap-001",
            "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "SGD"}],
            "fx_rates": [],
        },
        "model_portfolio": {"targets": [{"instrument_id": "EQ_1", "weight": "1.0"}]},
        "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
        "source_lineage": {
            "portfolio_snapshot_id": "core-pf-snap-001",
            "market_data_snapshot_id": "core-md-snap-001",
        },
        "supportability": {"state": "READY", "reason": "DPM_CORE_CONTEXT_READY"},
    }


def _core_snapshot_payload() -> dict:
    return {
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "as_of_date": "2026-04-10",
        "snapshot_id": "core-pf-snap-001",
        "valuation_context": {"portfolio_currency": "SGD", "reporting_currency": "SGD"},
        "sections": {
            "positions_baseline": [
                {
                    "security_id": "EQ_US_AAPL",
                    "quantity": "100",
                    "market_value_local": "18712",
                    "currency": "USD",
                },
                {
                    "security_id": "CASH_SGD_BOOK_OPERATING",
                    "quantity": "10000",
                    "market_value_local": "10000",
                    "currency": "SGD",
                },
            ],
            "portfolio_totals": {"baseline_total_market_value_base": "35298.2052"},
        },
    }


def _model_portfolio_target_payload() -> dict:
    return {
        "product_name": "DpmModelPortfolioTarget",
        "product_version": "v1",
        "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
        "model_portfolio_version": "2026.04",
        "as_of_date": "2026-04-10",
        "display_name": "Singapore Global Balanced DPM Model",
        "base_currency": "SGD",
        "risk_profile": "balanced",
        "mandate_type": "discretionary",
        "rebalance_frequency": "monthly",
        "approval_status": "approved",
        "approved_at": "2026-04-10T09:00:00Z",
        "effective_from": "2026-04-10",
        "effective_to": None,
        "targets": [
            {
                "instrument_id": "EQ_US_AAPL",
                "target_weight": "0.6000000000",
                "min_weight": "0.5500000000",
                "max_weight": "0.6500000000",
                "target_status": "active",
                "quality_status": "accepted",
                "source_record_id": "target-aapl",
            },
            {
                "instrument_id": "FI_US_TREASURY_10Y",
                "target_weight": "0.4000000000",
                "min_weight": "0.3500000000",
                "max_weight": "0.4500000000",
                "target_status": "active",
                "quality_status": "accepted",
                "source_record_id": "target-treasury",
            },
        ],
        "supportability": {
            "state": "READY",
            "reason": "MODEL_TARGETS_READY",
            "target_count": 2,
            "total_target_weight": "1.0000000000",
        },
        "lineage": {
            "source_system": "investment_office_model_system",
            "contract_version": "rfc_087_v1",
        },
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-04-10T09:00:00Z",
    }


def _mandate_binding_payload() -> dict:
    return {
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
        "rebalance_frequency": "monthly",
        "rebalance_bands": {
            "default_band": "0.0250000000",
            "cash_reserve_weight": "0.0200000000",
        },
        "effective_from": "2026-04-01",
        "effective_to": None,
        "binding_version": 1,
        "supportability": {
            "state": "READY",
            "reason": "MANDATE_BINDING_READY",
            "missing_data_families": [],
        },
        "lineage": {
            "source_system": "mandate_admin",
            "source_record_id": "mandate_001_v1",
            "contract_version": "rfc_087_v1",
        },
        "data_quality_status": "ACCEPTED",
        "latest_evidence_timestamp": "2026-04-01T09:00:00Z",
    }


def _benchmark_assignment_payload() -> dict:
    return {
        "product_name": "BenchmarkAssignment",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "benchmark_id": "BMK_PB_GLOBAL_BALANCED_60_40",
        "as_of_date": "2026-04-10",
        "effective_from": "2026-01-01",
        "effective_to": None,
        "assignment_source": "mandate_admin",
        "assignment_status": "active",
        "policy_pack_id": "POLICY_DPM_SG_BALANCED_V1",
        "source_system": "lotus-core",
        "assignment_recorded_at": "2026-04-01T09:00:00Z",
        "assignment_version": 1,
        "contract_version": "rfc_062_v1",
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-04-01T09:00:00Z",
    }


def _pm_book_membership_payload() -> dict:
    return {
        "product_name": "PortfolioManagerBookMembership",
        "product_version": "v1",
        "tenant_id": "default",
        "as_of_date": "2026-05-03",
        "portfolio_manager_id": "PM_SG_DPM_001",
        "booking_center_code": "Singapore",
        "members": [
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "client_id": "CIF_SG_000184",
                "booking_center_code": "Singapore",
                "portfolio_type": "DISCRETIONARY",
                "status": "ACTIVE",
                "open_date": "2024-01-15",
                "close_date": None,
                "base_currency": "USD",
                "source_record_id": "pm-book:001",
            }
        ],
        "supportability": {
            "state": "READY",
            "reason": "PM_BOOK_MEMBERSHIP_READY",
            "returned_portfolio_count": 1,
            "filters_applied": {"portfolio_types": ["DISCRETIONARY"]},
        },
        "lineage": {"source_system": "relationship_book", "contract_version": "rfc_041_v1"},
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-05-03T09:00:00Z",
        "source_batch_fingerprint": "sha256:pm-book",
        "snapshot_id": "pm-book-snapshot-20260503",
    }


def _cio_model_change_cohort_payload() -> dict:
    return {
        "product_name": "CioModelChangeAffectedCohort",
        "product_version": "v1",
        "tenant_id": "default",
        "as_of_date": "2026-05-03",
        "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
        "model_portfolio_version": "2026.05",
        "model_change_event_id": "cio_model_change:MODEL_PB_SG_GLOBAL_BAL_DPM:2026.05",
        "approval_state": "approved",
        "approved_at": "2026-05-01T08:00:00Z",
        "effective_from": "2026-05-01",
        "effective_to": None,
        "affected_mandates": [
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                "client_id": "CIF_SG_000184",
                "booking_center_code": "Singapore",
                "jurisdiction_code": "SG",
                "discretionary_authority_status": "active",
                "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
                "policy_pack_id": "POLICY_DPM_SG_BALANCED_V1",
                "risk_profile": "balanced",
                "effective_from": "2026-05-01",
                "effective_to": None,
                "binding_version": 3,
                "source_record_id": "mandate-binding-001",
            }
        ],
        "supportability": {
            "state": "READY",
            "reason": "CIO_MODEL_CHANGE_COHORT_READY",
            "returned_mandate_count": 1,
            "filters_applied": ["model_portfolio_id", "as_of_date"],
        },
        "lineage": {"source_system": "cio_model_admin", "contract_version": "rfc_041_v1"},
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-05-03T09:00:00Z",
        "source_batch_fingerprint": "sha256:cio-model-change",
        "snapshot_id": "cio-model-change-snapshot-20260503",
    }


def _instrument_eligibility_payload() -> dict:
    return {
        "product_name": "InstrumentEligibilityProfile",
        "product_version": "v1",
        "as_of_date": "2026-04-10",
        "tenant_id": "tenant_sg_pb",
        "eligibility": [
            {
                "security_id": "EQ_US_AAPL",
                "found": True,
                "eligibility_status": "APPROVED",
                "product_shelf_status": "APPROVED",
                "buy_allowed": True,
                "sell_allowed": True,
                "restriction_reason_codes": [],
                "settlement_days": 2,
                "settlement_calendar_id": "US_NYSE",
                "liquidity_tier": "L1",
                "issuer_id": "APPLE",
                "issuer_name": "Apple Inc.",
                "ultimate_parent_issuer_id": "APPLE_PARENT",
                "ultimate_parent_issuer_name": "Apple Inc.",
                "asset_class": "Equity",
                "country_of_risk": "US",
                "effective_from": "2026-04-01",
                "effective_to": None,
                "source_record_id": "AAPL-elig-20260401",
                "quality_status": "accepted",
            }
        ],
        "supportability": {
            "state": "READY",
            "reason": "INSTRUMENT_ELIGIBILITY_READY",
            "requested_count": 1,
            "found_count": 1,
            "missing_security_ids": [],
        },
        "lineage": {
            "source_system": "instrument_eligibility",
            "contract_version": "rfc_087_v1",
        },
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-04-10T09:00:00Z",
    }


def _portfolio_tax_lots_payload() -> dict:
    return {
        "product_name": "PortfolioTaxLotWindow",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "as_of_date": "2026-04-10",
        "lots": [
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "security_id": "EQ_US_AAPL",
                "instrument_id": "EQ_US_AAPL",
                "lot_id": "LOT-AAPL-001",
                "open_quantity": "100.0000000000",
                "original_quantity": "100.0000000000",
                "acquisition_date": "2026-03-25",
                "cost_basis_base": "15005.5000000000",
                "cost_basis_local": "15005.5000000000",
                "local_currency": "USD",
                "tax_lot_status": "OPEN",
                "source_transaction_id": "TXN-BUY-AAPL-001",
                "source_lineage": {
                    "source_system": "position_lot_state",
                    "calculation_policy_id": "BUY_DEFAULT_POLICY",
                },
            }
        ],
        "page": {
            "page_size": 250,
            "sort_key": "acquisition_date:asc,lot_id:asc",
            "returned_component_count": 1,
            "request_scope_fingerprint": "tax-lot-scope-001",
            "next_page_token": None,
        },
        "supportability": {
            "state": "READY",
            "reason": "TAX_LOTS_READY",
            "requested_security_count": 1,
            "returned_lot_count": 1,
            "missing_security_ids": [],
        },
        "lineage": {
            "source_system": "position_lot_state",
            "contract_version": "rfc_087_v1",
        },
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-04-10T09:00:00Z",
    }


def _market_data_coverage_payload() -> dict:
    return {
        "product_name": "MarketDataCoverageWindow",
        "product_version": "v1",
        "as_of_date": "2026-04-10",
        "valuation_currency": "SGD",
        "price_coverage": [
            {
                "instrument_id": "EQ_US_AAPL",
                "found": True,
                "price_date": "2026-04-10",
                "price": "187.1200000000",
                "currency": "USD",
                "age_days": 0,
                "quality_status": "READY",
            }
        ],
        "fx_coverage": [
            {
                "from_currency": "USD",
                "to_currency": "SGD",
                "found": True,
                "rate_date": "2026-04-10",
                "rate": "1.3521000000",
                "age_days": 0,
                "quality_status": "READY",
            }
        ],
        "supportability": {
            "state": "READY",
            "reason": "MARKET_DATA_READY",
            "requested_price_count": 1,
            "resolved_price_count": 1,
            "requested_fx_count": 1,
            "resolved_fx_count": 1,
            "missing_instrument_ids": [],
            "stale_instrument_ids": [],
            "missing_currency_pairs": [],
            "stale_currency_pairs": [],
        },
        "lineage": {
            "source_system": "market_prices+fx_rates",
            "contract_version": "rfc_087_v1",
        },
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-04-10T09:00:00Z",
    }


def _transaction_cost_curve_payload() -> dict:
    return {
        "product_name": "TransactionCostCurve",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "as_of_date": "2026-04-10",
        "window": {"start_date": "2026-01-10", "end_date": "2026-04-10"},
        "curve_points": [
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "security_id": "EQ_US_AAPL",
                "transaction_type": "BUY",
                "currency": "USD",
                "observation_count": 2,
                "total_notional": "25000.0000000000",
                "total_cost": "12.5000000000",
                "average_cost_bps": "5.0000",
                "min_cost_bps": "4.5000",
                "max_cost_bps": "5.5000",
                "first_observed_date": "2026-03-25",
                "last_observed_date": "2026-04-10",
                "sample_transaction_ids": ["TXN-BUY-AAPL-001", "TXN-BUY-AAPL-002"],
                "source_lineage": {
                    "source_system": "transactions",
                    "contract_version": "rfc_040_wtbd_007_v1",
                },
            }
        ],
        "page": {
            "page_size": 250,
            "sort_key": "security_id:asc,transaction_type:asc,currency:asc",
            "returned_component_count": 1,
            "request_scope_fingerprint": "transaction-cost-scope-001",
            "next_page_token": None,
        },
        "supportability": {
            "state": "READY",
            "reason": "TRANSACTION_COST_CURVE_READY",
            "requested_security_count": 1,
            "returned_curve_point_count": 1,
            "missing_security_ids": [],
        },
        "lineage": {
            "source_system": "transactions",
            "contract_version": "rfc_040_wtbd_007_v1",
        },
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-04-10T09:00:00Z",
        "source_batch_fingerprint": "sha256:transaction-cost-curve",
    }


def _cashflow_projection_payload() -> dict:
    return {
        "product_name": "PortfolioCashflowProjection",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "as_of_date": "2026-04-10",
        "range_start_date": "2026-04-10",
        "range_end_date": "2026-07-09",
        "include_projected": True,
        "portfolio_currency": "SGD",
        "points": [
            {
                "projection_date": "2026-04-17",
                "net_cashflow": "-18000.0000000000",
                "projected_cumulative_cashflow": "-18000.0000000000",
            }
        ],
        "total_net_cashflow": "-18000.0000000000",
        "projection_days": 90,
        "notes": "Projected window includes settlement-dated future external cash movements.",
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-04-10T09:00:00Z",
        "source_batch_fingerprint": "cashflow_projection:PB_SG_GLOBAL_BAL_001:2026-04-10",
    }


def _client_restriction_profile_payload() -> dict:
    return {
        "product_name": "ClientRestrictionProfile",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "client_id": "CIF_SG_000184",
        "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
        "as_of_date": "2026-04-10",
        "restrictions": [
            {
                "restriction_scope": "instrument",
                "restriction_code": "NO_PRIVATE_CREDIT_BUY",
                "restriction_status": "active",
                "restriction_source": "client_mandate",
                "applies_to_buy": True,
                "applies_to_sell": False,
                "instrument_ids": ["PRIVATE_CREDIT_FUND"],
                "asset_classes": [],
                "issuer_ids": [],
                "country_codes": [],
                "effective_from": "2026-01-01",
                "effective_to": None,
                "restriction_version": 1,
                "source_record_id": "client-restriction:1",
            }
        ],
        "supportability": {
            "state": "READY",
            "reason": "CLIENT_RESTRICTION_PROFILE_READY",
            "restriction_count": 1,
            "missing_data_families": [],
        },
        "lineage": {"contract_version": "rfc_040_client_restriction_profile_v1"},
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-04-10T09:00:00Z",
        "source_batch_fingerprint": "sha256:client-restrictions",
    }


def _sustainability_preference_profile_payload() -> dict:
    return {
        "product_name": "SustainabilityPreferenceProfile",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "client_id": "CIF_SG_000184",
        "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
        "as_of_date": "2026-04-10",
        "preferences": [
            {
                "preference_framework": "LOTUS_SUSTAINABILITY_V1",
                "preference_code": "MIN_SUSTAINABLE_ALLOCATION",
                "preference_status": "active",
                "preference_source": "client_mandate",
                "minimum_allocation": "0.2000000000",
                "maximum_allocation": None,
                "applies_to_asset_classes": ["Equity"],
                "exclusion_codes": [],
                "positive_tilt_codes": [],
                "effective_from": "2026-01-01",
                "effective_to": None,
                "preference_version": 1,
                "source_record_id": "sustainability:1",
            }
        ],
        "supportability": {
            "state": "READY",
            "reason": "SUSTAINABILITY_PREFERENCE_PROFILE_READY",
            "preference_count": 1,
            "missing_data_families": [],
        },
        "lineage": {"contract_version": "rfc_040_sustainability_preference_profile_v1"},
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-04-10T09:00:00Z",
        "source_batch_fingerprint": "sha256:sustainability-preferences",
    }


def _client_income_needs_schedule_payload() -> dict:
    return {
        "product_name": "ClientIncomeNeedsSchedule",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "client_id": "CIF_SG_000184",
        "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
        "as_of_date": "2026-04-10",
        "schedules": [
            {
                "schedule_id": "income-need-001",
                "need_type": "RETIREMENT_INCOME",
                "need_status": "active",
                "amount": "12000.0000000000",
                "currency": "SGD",
                "frequency": "monthly",
                "start_date": "2026-04-01",
                "end_date": None,
                "priority": 1,
                "funding_policy": "BANK_APPROVED_INCOME_POLICY",
                "source_record_id": "income-need:1",
            }
        ],
        "supportability": {
            "state": "READY",
            "reason": "CLIENT_INCOME_NEEDS_SCHEDULE_READY",
            "schedule_count": 1,
            "missing_data_families": [],
        },
        "lineage": {"contract_version": "rfc_042_client_income_needs_v1"},
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-04-10T09:00:00Z",
        "source_batch_fingerprint": "sha256:client-income-needs",
    }


def _liquidity_reserve_requirement_payload() -> dict:
    return {
        "product_name": "LiquidityReserveRequirement",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "client_id": "CIF_SG_000184",
        "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
        "as_of_date": "2026-04-10",
        "requirements": [
            {
                "reserve_requirement_id": "reserve-001",
                "reserve_type": "CLIENT_LIQUIDITY_RESERVE",
                "reserve_status": "active",
                "required_amount": "50000.0000000000",
                "currency": "SGD",
                "horizon_days": 90,
                "priority": 1,
                "policy_source": "BANK_APPROVED_RESERVE_POLICY",
                "effective_from": "2026-01-01",
                "effective_to": None,
                "requirement_version": 1,
                "source_record_id": "reserve:1",
            }
        ],
        "supportability": {
            "state": "READY",
            "reason": "LIQUIDITY_RESERVE_REQUIREMENT_READY",
            "requirement_count": 1,
            "missing_data_families": [],
        },
        "lineage": {"contract_version": "rfc_042_liquidity_reserve_v1"},
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-04-10T09:00:00Z",
        "source_batch_fingerprint": "sha256:liquidity-reserve",
    }


def _planned_withdrawal_schedule_payload() -> dict:
    return {
        "product_name": "PlannedWithdrawalSchedule",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "client_id": "CIF_SG_000184",
        "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
        "as_of_date": "2026-04-10",
        "horizon_days": 365,
        "withdrawals": [
            {
                "withdrawal_schedule_id": "withdrawal-001",
                "withdrawal_type": "CLIENT_DRAWDOWN",
                "withdrawal_status": "planned",
                "amount": "25000.0000000000",
                "currency": "SGD",
                "scheduled_date": "2026-06-01",
                "recurrence_frequency": None,
                "purpose_code": "CLIENT_LIQUIDITY",
                "source_record_id": "withdrawal:1",
            }
        ],
        "supportability": {
            "state": "READY",
            "reason": "PLANNED_WITHDRAWAL_SCHEDULE_READY",
            "withdrawal_count": 1,
            "missing_data_families": [],
        },
        "lineage": {"contract_version": "rfc_042_planned_withdrawal_v1"},
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-04-10T09:00:00Z",
        "source_batch_fingerprint": "sha256:planned-withdrawals",
    }


def _external_hedge_execution_readiness_payload() -> dict:
    return {
        "product_name": "ExternalHedgeExecutionReadiness",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "client_id": "CIF_SG_000184",
        "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
        "as_of_date": "2026-04-10",
        "reporting_currency": "SGD",
        "exposure_currencies": ["USD"],
        "readiness_checks": [],
        "supportability": {
            "state": "UNAVAILABLE",
            "reason": "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
            "missing_data_families": [
                "external_currency_exposure",
                "external_hedge_policy",
                "external_fx_forward_curve",
                "external_eligible_hedge_instrument",
                "external_hedge_execution_readiness",
            ],
            "blocked_capabilities": [
                "hedge_advice",
                "forward_pricing",
                "counterparty_selection",
                "best_execution",
                "oms_acknowledgement",
                "fills",
                "settlement",
                "autonomous_treasury_action",
            ],
        },
        "lineage": {
            "source_system": "external-bank-treasury",
            "integration_status": "not_ingested",
            "runtime_posture": "fail_closed",
        },
        "data_quality_status": "MISSING",
        "latest_evidence_timestamp": None,
        "source_batch_fingerprint": "sha256:external-hedge-readiness",
    }


def _stateful_input() -> DpmStatefulInput:
    return DpmStatefulInput(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of=date(2026, 3, 25),
        mandate_id="mandate_balanced_discretionary",
        model_portfolio_id="model_balanced_sgd",
        tenant_id="tenant_001",
        booking_center_code="SG",
    )


def _composed_context_response_for(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/mandate-binding"):
        return httpx.Response(200, json=_mandate_binding_payload())
    if path.endswith("/targets"):
        return httpx.Response(200, json=_model_portfolio_target_payload())
    if path.endswith("/core-snapshot"):
        return httpx.Response(200, json=_core_snapshot_payload())
    if path.endswith("/eligibility-bulk"):
        return httpx.Response(200, json=_instrument_eligibility_payload())
    if path.endswith("/tax-lots"):
        return httpx.Response(200, json=_portfolio_tax_lots_payload())
    if path.endswith("/coverage"):
        return httpx.Response(200, json=_market_data_coverage_payload())
    if path.endswith("/transaction-cost-curve"):
        return httpx.Response(200, json=_transaction_cost_curve_payload())
    if path.endswith("/cashflow-projection"):
        return httpx.Response(200, json=_cashflow_projection_payload())
    if path.endswith("/client-income-needs-schedule"):
        return httpx.Response(200, json=_client_income_needs_schedule_payload())
    if path.endswith("/liquidity-reserve-requirement"):
        return httpx.Response(200, json=_liquidity_reserve_requirement_payload())
    if path.endswith("/planned-withdrawal-schedule"):
        return httpx.Response(200, json=_planned_withdrawal_schedule_payload())
    if path.endswith("/external-hedge-execution-readiness"):
        return httpx.Response(200, json=_external_hedge_execution_readiness_payload())
    if path.endswith("/client-restriction-profile"):
        return httpx.Response(200, json=_client_restriction_profile_payload())
    if path.endswith("/sustainability-preference-profile"):
        return httpx.Response(200, json=_sustainability_preference_profile_payload())
    return httpx.Response(404, json={"detail": "unexpected path"})


def test_core_resolver_posts_selector_payload_and_correlation_header():
    seen: list[tuple[str, str | None, bytes]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(
            (
                str(request.url),
                request.headers.get("X-Correlation-Id"),
                request.read(),
            )
        )
        return _composed_context_response_for(request)

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(
            base_url="https://core.example.test",
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    context = client.resolve_execution_context(
        stateful_input=_stateful_input(),
        correlation_id="corr-core-001",
    )

    assert [url for url, _, _ in seen] == [
        "https://core.example.test/integration/portfolios/PB_SG_GLOBAL_BAL_001/mandate-binding",
        "https://core.example.test/integration/model-portfolios/model_balanced_sgd/targets",
        "https://core.example.test/integration/portfolios/PB_SG_GLOBAL_BAL_001/core-snapshot",
        "https://core.example.test/integration/instruments/eligibility-bulk",
        "https://core.example.test/integration/portfolios/PB_SG_GLOBAL_BAL_001/tax-lots",
        "https://core.example.test/integration/market-data/coverage",
        "https://core.example.test/integration/portfolios/PB_SG_GLOBAL_BAL_001/transaction-cost-curve",
        "https://core.example.test/portfolios/PB_SG_GLOBAL_BAL_001/cashflow-projection?as_of_date=2026-03-25&horizon_days=90&include_projected=true",
        "https://core.example.test/integration/portfolios/PB_SG_GLOBAL_BAL_001/client-income-needs-schedule",
        "https://core.example.test/integration/portfolios/PB_SG_GLOBAL_BAL_001/liquidity-reserve-requirement",
        "https://core.example.test/integration/portfolios/PB_SG_GLOBAL_BAL_001/planned-withdrawal-schedule",
        "https://core.example.test/integration/portfolios/PB_SG_GLOBAL_BAL_001/external-hedge-execution-readiness",
        "https://core.example.test/integration/portfolios/PB_SG_GLOBAL_BAL_001/client-restriction-profile",
        "https://core.example.test/integration/portfolios/PB_SG_GLOBAL_BAL_001/sustainability-preference-profile",
    ]
    assert {correlation_id for _, correlation_id, _ in seen} == {"corr-core-001"}
    assert b'"sections":["positions_baseline","portfolio_totals"]' in seen[2][2]
    assert b'"security_ids":["EQ_US_AAPL"]' in seen[4][2]
    assert b'"currency_pairs":[{"from_currency":"USD","to_currency":"SGD"}]' in seen[5][2]
    assert b'"window":{"start_date":"2025-02-18","end_date":"2026-03-25"}' in seen[6][2]
    assert b'"transaction_types":["BUY","SELL"]' in seen[6][2]
    assert b'"mandate_id":"mandate_balanced_discretionary"' in seen[8][2]
    assert b'"include_inactive_schedules":false' in seen[8][2]
    assert b'"include_inactive_requirements":false' in seen[9][2]
    assert b'"horizon_days":365' in seen[10][2]
    assert b'"include_inactive_withdrawals":false' in seen[10][2]
    assert b'"reporting_currency":"SGD"' in seen[11][2]
    assert b'"exposure_currencies":["USD"]' in seen[11][2]
    assert b'"include_inactive_restrictions":false' in seen[12][2]
    assert b'"include_inactive_preferences":false' in seen[13][2]
    assert context.source_lineage.portfolio_snapshot_id == "core-pf-snap-001"
    assert context.source_lineage.model_portfolio_id == "MODEL_PB_SG_GLOBAL_BAL_DPM"
    assert context.portfolio_snapshot.cash_balances[0].currency == "SGD"
    assert context.transaction_cost_curve is not None
    assert context.transaction_cost_curve.supportability.state == "READY"
    assert context.portfolio_cashflow_projection is not None
    assert context.portfolio_cashflow_projection.product_name == "PortfolioCashflowProjection"
    assert context.portfolio_cashflow_projection.include_projected is True
    assert context.client_income_needs_schedule is not None
    assert context.client_income_needs_schedule.supportability.schedule_count == 1
    assert context.liquidity_reserve_requirement is not None
    assert context.liquidity_reserve_requirement.supportability.requirement_count == 1
    assert context.planned_withdrawal_schedule is not None
    assert context.planned_withdrawal_schedule.supportability.withdrawal_count == 1
    assert context.external_hedge_execution_readiness is not None
    assert context.external_hedge_execution_readiness.supportability.state == "UNAVAILABLE"
    assert (
        "oms_acknowledgement"
        in context.external_hedge_execution_readiness.supportability.blocked_capabilities
    )
    assert context.client_restriction_profile is not None
    assert context.client_restriction_profile.supportability.state == "READY"
    assert context.sustainability_preference_profile is not None
    assert context.sustainability_preference_profile.supportability.state == "READY"


def test_core_resolver_routes_cashflow_projection_to_query_base_url():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return _composed_context_response_for(request)

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(
            base_url="https://core-control.example.test",
            query_base_url="https://core-query.example.test",
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    context = client.resolve_execution_context(
        stateful_input=_stateful_input(),
        correlation_id="corr-core-query-001",
    )

    assert context.portfolio_cashflow_projection is not None
    assert (
        "https://core-query.example.test/portfolios/PB_SG_GLOBAL_BAL_001/"
        "cashflow-projection?as_of_date=2026-03-25&horizon_days=90&include_projected=true"
    ) in seen
    assert all(
        url.startswith("https://core-control.example.test/")
        for url in seen
        if "cashflow-projection" not in url
    )


def test_core_resolver_cashflow_projection_path_can_be_disabled():
    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(
            base_url="https://core.example.test",
            portfolio_cashflow_projection_path_template="",
        ),
        client=httpx.Client(transport=httpx.MockTransport(_composed_context_response_for)),
    )

    with pytest.raises(
        DpmCoreResolverUnavailableError,
        match="DPM_CORE_CASHFLOW_PROJECTION_UNAVAILABLE",
    ):
        client.resolve_portfolio_cashflow_projection(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=date(2026, 4, 10),
            correlation_id=None,
        )


def test_core_resolver_cashflow_projection_maps_get_failures():
    unavailable_client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test", max_attempts=1),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(503, json={"detail": "maintenance"})
            )
        ),
    )
    incomplete_client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(404, json={"detail": "missing"})
            )
        ),
    )

    with pytest.raises(
        DpmCoreResolverUnavailableError,
        match="DPM_CORE_CASHFLOW_PROJECTION_UNAVAILABLE",
    ):
        unavailable_client.resolve_portfolio_cashflow_projection(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=date(2026, 4, 10),
            correlation_id=None,
        )

    with pytest.raises(DpmCoreResolverError, match="DPM_CORE_CASHFLOW_PROJECTION_INCOMPLETE"):
        incomplete_client.resolve_portfolio_cashflow_projection(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=date(2026, 4, 10),
            correlation_id=None,
        )


def test_core_resolver_retries_transient_unavailable_response():
    calls: dict[str, int] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        calls[request.url.path] = calls.get(request.url.path, 0) + 1
        if request.url.path.endswith("/mandate-binding") and calls[request.url.path] == 1:
            return httpx.Response(503, json={"detail": "not ready"})
        return _composed_context_response_for(request)

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(
            base_url="https://core.example.test",
            max_attempts=2,
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    context = client.resolve_execution_context(
        stateful_input=_stateful_input(),
        correlation_id=None,
    )

    assert calls["/integration/portfolios/PB_SG_GLOBAL_BAL_001/mandate-binding"] == 2
    assert context.supportability.state == "READY"


def test_core_resolver_rejects_legacy_monolithic_route():
    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(
            base_url="https://core.example.test",
            path_template="/integration/portfolios/{portfolio_id}/dpm-execution-context",
        ),
        client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200))),
    )

    with pytest.raises(
        DpmCoreResolverUnavailableError,
        match="DPM_CORE_RESOLVER_UNAVAILABLE",
    ):
        client.resolve_execution_context(
            stateful_input=_stateful_input(),
            correlation_id=None,
        )


def test_core_resolver_rejects_missing_composed_snapshot_route():
    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(
            base_url="https://core.example.test",
            portfolio_snapshot_path_template="",
        ),
        client=httpx.Client(transport=httpx.MockTransport(_composed_context_response_for)),
    )

    with pytest.raises(
        DpmCoreResolverUnavailableError,
        match="DPM_CORE_RESOLVER_UNAVAILABLE",
    ):
        client.resolve_execution_context(
            stateful_input=_stateful_input(),
            correlation_id=None,
        )


def test_core_resolver_fetches_model_portfolio_targets_from_dedicated_source_product():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["correlation_id"] = request.headers.get("X-Correlation-Id")
        seen["payload"] = request.read()
        return httpx.Response(200, json=_model_portfolio_target_payload())

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = client.resolve_model_portfolio_targets(
        model_portfolio_id="MODEL_PB_SG_GLOBAL_BAL_DPM",
        as_of_date=date(2026, 4, 10),
        tenant_id="tenant_sg_pb",
        correlation_id="corr-targets-001",
    )

    assert seen["url"] == (
        "https://core.example.test/integration/model-portfolios/MODEL_PB_SG_GLOBAL_BAL_DPM/targets"
    )
    assert seen["correlation_id"] == "corr-targets-001"
    assert b'"as_of_date":"2026-04-10"' in seen["payload"]
    assert b'"tenant_id":"tenant_sg_pb"' in seen["payload"]
    assert response.product_name == "DpmModelPortfolioTarget"
    assert response.supportability.state == "READY"
    assert [target.instrument_id for target in response.targets] == [
        "EQ_US_AAPL",
        "FI_US_TREASURY_10Y",
    ]


def test_core_resolver_fetches_mandate_binding_from_dedicated_source_product():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["correlation_id"] = request.headers.get("X-Correlation-Id")
        seen["payload"] = request.read()
        return httpx.Response(200, json=_mandate_binding_payload())

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = client.resolve_mandate_binding(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=date(2026, 4, 10),
        tenant_id="tenant_sg_pb",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        booking_center_code="Singapore",
        include_policy_pack=True,
        correlation_id="corr-mandate-001",
    )

    assert seen["url"] == (
        "https://core.example.test/integration/portfolios/PB_SG_GLOBAL_BAL_001/mandate-binding"
    )
    assert seen["correlation_id"] == "corr-mandate-001"
    assert b'"as_of_date":"2026-04-10"' in seen["payload"]
    assert b'"tenant_id":"tenant_sg_pb"' in seen["payload"]
    assert b'"mandate_id":"MANDATE_PB_SG_GLOBAL_BAL_001"' in seen["payload"]
    assert b'"booking_center_code":"Singapore"' in seen["payload"]
    assert b'"include_policy_pack":true' in seen["payload"]
    assert response.product_name == "DiscretionaryMandateBinding"
    assert response.supportability.state == "READY"
    assert response.policy_pack_id == "POLICY_DPM_SG_BALANCED_V1"
    assert response.rebalance_bands.default_band == Decimal("0.0250000000")


def test_core_resolver_fetches_benchmark_assignment_source_product():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["correlation_id"] = request.headers.get("X-Correlation-Id")
        seen["payload"] = request.read()
        return httpx.Response(200, json=_benchmark_assignment_payload())

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = client.resolve_benchmark_assignment(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=date(2026, 4, 10),
        reporting_currency="SGD",
        correlation_id="corr-benchmark-001",
    )

    assert seen["url"] == (
        "https://core.example.test/integration/portfolios/PB_SG_GLOBAL_BAL_001/benchmark-assignment"
    )
    assert seen["correlation_id"] == "corr-benchmark-001"
    assert b'"as_of_date":"2026-04-10"' in seen["payload"]
    assert b'"reporting_currency":"SGD"' in seen["payload"]
    assert response.product_name == "BenchmarkAssignment"
    assert response.benchmark_id == "BMK_PB_GLOBAL_BALANCED_60_40"


def test_core_resolver_fetches_portfolio_manager_book_membership_source_product():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["correlation_id"] = request.headers.get("X-Correlation-Id")
        seen["payload"] = request.read()
        return httpx.Response(200, json=_pm_book_membership_payload())

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = client.resolve_portfolio_manager_book_membership(
        portfolio_manager_id="PM_SG_DPM_001",
        as_of_date=date(2026, 5, 3),
        tenant_id="default",
        booking_center_code="Singapore",
        portfolio_types=["DISCRETIONARY"],
        include_inactive=False,
        correlation_id="corr-pm-book-001",
    )

    assert seen["url"] == (
        "https://core.example.test/integration/portfolio-manager-books/PM_SG_DPM_001/memberships"
    )
    assert seen["correlation_id"] == "corr-pm-book-001"
    assert b'"as_of_date":"2026-05-03"' in seen["payload"]
    assert b'"tenant_id":"default"' in seen["payload"]
    assert b'"booking_center_code":"Singapore"' in seen["payload"]
    assert b'"portfolio_types":["DISCRETIONARY"]' in seen["payload"]
    assert b'"include_inactive":false' in seen["payload"]
    assert response.product_name == "PortfolioManagerBookMembership"
    assert response.supportability.state == "READY"
    assert response.members[0].portfolio_id == "PB_SG_GLOBAL_BAL_001"


def test_core_resolver_fetches_cio_model_change_affected_cohort_source_product():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["correlation_id"] = request.headers.get("X-Correlation-Id")
        seen["payload"] = request.read()
        return httpx.Response(200, json=_cio_model_change_cohort_payload())

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = client.resolve_cio_model_change_affected_cohort(
        model_portfolio_id="MODEL_PB_SG_GLOBAL_BAL_DPM",
        as_of_date=date(2026, 5, 3),
        tenant_id="default",
        booking_center_code="Singapore",
        include_inactive_mandates=False,
        correlation_id="corr-cio-model-change-001",
    )

    assert seen["url"] == (
        "https://core.example.test/integration/model-portfolios/"
        "MODEL_PB_SG_GLOBAL_BAL_DPM/affected-mandates"
    )
    assert seen["correlation_id"] == "corr-cio-model-change-001"
    assert b'"as_of_date":"2026-05-03"' in seen["payload"]
    assert b'"tenant_id":"default"' in seen["payload"]
    assert b'"booking_center_code":"Singapore"' in seen["payload"]
    assert b'"include_inactive_mandates":false' in seen["payload"]
    assert response.product_name == "CioModelChangeAffectedCohort"
    assert response.supportability.state == "READY"
    assert response.affected_mandates[0].portfolio_id == "PB_SG_GLOBAL_BAL_001"


def test_core_resolver_fetches_instrument_eligibility_from_dedicated_source_product():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["correlation_id"] = request.headers.get("X-Correlation-Id")
        seen["payload"] = request.read()
        return httpx.Response(200, json=_instrument_eligibility_payload())

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = client.resolve_instrument_eligibility(
        security_ids=["EQ_US_AAPL"],
        as_of_date=date(2026, 4, 10),
        tenant_id="tenant_sg_pb",
        include_restricted_rationale=False,
        correlation_id="corr-eligibility-001",
    )

    assert seen["url"] == "https://core.example.test/integration/instruments/eligibility-bulk"
    assert seen["correlation_id"] == "corr-eligibility-001"
    assert b'"as_of_date":"2026-04-10"' in seen["payload"]
    assert b'"security_ids":["EQ_US_AAPL"]' in seen["payload"]
    assert b'"tenant_id":"tenant_sg_pb"' in seen["payload"]
    assert b'"include_restricted_rationale":false' in seen["payload"]
    assert response.product_name == "InstrumentEligibilityProfile"
    assert response.supportability.state == "READY"
    assert response.eligibility[0].security_id == "EQ_US_AAPL"


def test_core_resolver_fetches_portfolio_tax_lots_from_dedicated_source_product():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["correlation_id"] = request.headers.get("X-Correlation-Id")
        seen["payload"] = request.read()
        return httpx.Response(200, json=_portfolio_tax_lots_payload())

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = client.resolve_portfolio_tax_lots(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=date(2026, 4, 10),
        security_ids=["EQ_US_AAPL"],
        lot_status_filter="OPEN",
        include_closed_lots=False,
        page_size=250,
        page_token=None,
        tenant_id="tenant_sg_pb",
        correlation_id="corr-tax-lots-001",
    )

    assert seen["url"] == (
        "https://core.example.test/integration/portfolios/PB_SG_GLOBAL_BAL_001/tax-lots"
    )
    assert seen["correlation_id"] == "corr-tax-lots-001"
    assert b'"as_of_date":"2026-04-10"' in seen["payload"]
    assert b'"security_ids":["EQ_US_AAPL"]' in seen["payload"]
    assert b'"lot_status_filter":"OPEN"' in seen["payload"]
    assert b'"include_closed_lots":false' in seen["payload"]
    assert b'"page":{"page_size":250,"page_token":null}' in seen["payload"]
    assert b'"tenant_id":"tenant_sg_pb"' in seen["payload"]
    assert response.product_name == "PortfolioTaxLotWindow"
    assert response.supportability.state == "READY"
    assert response.lots[0].lot_id == "LOT-AAPL-001"


def test_core_resolver_fetches_market_data_coverage_from_dedicated_source_product():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["correlation_id"] = request.headers.get("X-Correlation-Id")
        seen["payload"] = request.read()
        return httpx.Response(200, json=_market_data_coverage_payload())

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = client.resolve_market_data_coverage(
        instrument_ids=["EQ_US_AAPL"],
        currency_pairs=[("USD", "SGD")],
        as_of_date=date(2026, 4, 10),
        valuation_currency="SGD",
        max_staleness_days=5,
        tenant_id="tenant_sg_pb",
        correlation_id="corr-market-data-001",
    )

    assert seen["url"] == "https://core.example.test/integration/market-data/coverage"
    assert seen["correlation_id"] == "corr-market-data-001"
    assert b'"as_of_date":"2026-04-10"' in seen["payload"]
    assert b'"instrument_ids":["EQ_US_AAPL"]' in seen["payload"]
    assert b'"currency_pairs":[{"from_currency":"USD","to_currency":"SGD"}]' in seen["payload"]
    assert b'"valuation_currency":"SGD"' in seen["payload"]
    assert b'"max_staleness_days":5' in seen["payload"]
    assert b'"tenant_id":"tenant_sg_pb"' in seen["payload"]
    assert response.product_name == "MarketDataCoverageWindow"
    assert response.supportability.state == "READY"
    assert response.fx_coverage[0].rate == Decimal("1.3521000000")


def test_core_resolver_fetches_transaction_cost_curve_from_dedicated_source_product():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["correlation_id"] = request.headers.get("X-Correlation-Id")
        seen["payload"] = request.read()
        return httpx.Response(200, json=_transaction_cost_curve_payload())

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = client.resolve_transaction_cost_curve(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=date(2026, 4, 10),
        window_start_date=date(2026, 1, 10),
        window_end_date=date(2026, 4, 10),
        security_ids=["EQ_US_AAPL"],
        transaction_types=["BUY", "SELL"],
        min_observation_count=1,
        page_size=250,
        page_token=None,
        tenant_id="tenant_sg_pb",
        correlation_id="corr-transaction-cost-001",
    )

    assert seen["url"] == (
        "https://core.example.test/integration/portfolios/"
        "PB_SG_GLOBAL_BAL_001/transaction-cost-curve"
    )
    assert seen["correlation_id"] == "corr-transaction-cost-001"
    assert b'"as_of_date":"2026-04-10"' in seen["payload"]
    assert b'"window":{"start_date":"2026-01-10","end_date":"2026-04-10"}' in seen["payload"]
    assert b'"security_ids":["EQ_US_AAPL"]' in seen["payload"]
    assert b'"transaction_types":["BUY","SELL"]' in seen["payload"]
    assert response.product_name == "TransactionCostCurve"
    assert response.supportability.state == "READY"
    assert response.curve_points[0].average_cost_bps == Decimal("5.0000")


def test_core_resolver_fetches_client_liquidity_source_products_from_dedicated_routes():
    seen: list[tuple[str, bytes]] = []
    payloads = {
        "/integration/portfolios/PB_SG_GLOBAL_BAL_001/client-income-needs-schedule": (
            _client_income_needs_schedule_payload()
        ),
        "/integration/portfolios/PB_SG_GLOBAL_BAL_001/liquidity-reserve-requirement": (
            _liquidity_reserve_requirement_payload()
        ),
        "/integration/portfolios/PB_SG_GLOBAL_BAL_001/planned-withdrawal-schedule": (
            _planned_withdrawal_schedule_payload()
        ),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.path, request.read()))
        return httpx.Response(200, json=payloads[request.url.path])

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    income_needs = client.resolve_client_income_needs_schedule(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=date(2026, 4, 10),
        tenant_id="tenant_sg_pb",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        correlation_id="corr-liquidity-products",
    )
    reserve = client.resolve_liquidity_reserve_requirement(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=date(2026, 4, 10),
        tenant_id="tenant_sg_pb",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        correlation_id="corr-liquidity-products",
    )
    withdrawals = client.resolve_planned_withdrawal_schedule(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=date(2026, 4, 10),
        tenant_id="tenant_sg_pb",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        horizon_days=365,
        correlation_id="corr-liquidity-products",
    )

    assert [path for path, _ in seen] == list(payloads)
    assert b'"include_inactive_schedules":false' in seen[0][1]
    assert b'"include_inactive_requirements":false' in seen[1][1]
    assert b'"include_inactive_withdrawals":false' in seen[2][1]
    assert income_needs.product_name == "ClientIncomeNeedsSchedule"
    assert income_needs.supportability.state == "READY"
    assert reserve.product_name == "LiquidityReserveRequirement"
    assert reserve.supportability.state == "READY"
    assert withdrawals.product_name == "PlannedWithdrawalSchedule"
    assert withdrawals.supportability.state == "READY"


def test_core_resolver_fetches_external_hedge_execution_readiness_from_dedicated_route():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["correlation_id"] = request.headers.get("X-Correlation-Id")
        seen["payload"] = request.read()
        return httpx.Response(200, json=_external_hedge_execution_readiness_payload())

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = client.resolve_external_hedge_execution_readiness(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=date(2026, 4, 10),
        tenant_id="tenant_sg_pb",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        reporting_currency="SGD",
        exposure_currencies=["USD"],
        correlation_id="corr-hedge-readiness-001",
    )

    assert seen["url"] == (
        "https://core.example.test/integration/portfolios/"
        "PB_SG_GLOBAL_BAL_001/external-hedge-execution-readiness"
    )
    assert seen["correlation_id"] == "corr-hedge-readiness-001"
    assert b'"as_of_date":"2026-04-10"' in seen["payload"]
    assert b'"mandate_id":"MANDATE_PB_SG_GLOBAL_BAL_001"' in seen["payload"]
    assert b'"reporting_currency":"SGD"' in seen["payload"]
    assert b'"exposure_currencies":["USD"]' in seen["payload"]
    assert response.product_name == "ExternalHedgeExecutionReadiness"
    assert response.supportability.reason == "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED"
    assert "hedge_advice" in response.supportability.blocked_capabilities


def test_core_resolver_maps_mandate_binding_4xx_to_incomplete_error():
    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(404, json={"detail": "x"}))
        ),
    )

    with pytest.raises(DpmCoreResolverError, match="DPM_CORE_MANDATE_BINDING_INCOMPLETE"):
        client.resolve_mandate_binding(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=date(2026, 4, 10),
            correlation_id=None,
        )


def test_core_resolver_maps_instrument_eligibility_4xx_to_incomplete_error():
    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(404, json={"detail": "x"}))
        ),
    )

    with pytest.raises(DpmCoreResolverError, match="DPM_CORE_INSTRUMENT_ELIGIBILITY_INCOMPLETE"):
        client.resolve_instrument_eligibility(
            security_ids=["UNKNOWN_SEC"],
            as_of_date=date(2026, 4, 10),
            correlation_id=None,
        )


def test_core_resolver_maps_portfolio_tax_lot_4xx_to_incomplete_error():
    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(404, json={"detail": "x"}))
        ),
    )

    with pytest.raises(DpmCoreResolverError, match="DPM_CORE_PORTFOLIO_TAX_LOTS_INCOMPLETE"):
        client.resolve_portfolio_tax_lots(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=date(2026, 4, 10),
            correlation_id=None,
        )


def test_core_resolver_maps_market_data_coverage_4xx_to_incomplete_error():
    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(404, json={"detail": "x"}))
        ),
    )

    with pytest.raises(DpmCoreResolverError, match="DPM_CORE_MARKET_DATA_COVERAGE_INCOMPLETE"):
        client.resolve_market_data_coverage(
            instrument_ids=["UNKNOWN_SEC"],
            currency_pairs=[],
            as_of_date=date(2026, 4, 10),
            correlation_id=None,
        )


def test_core_resolver_timeout_maps_to_source_safe_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(
            base_url="https://core.example.test",
            path_template="/integration/portfolios/{portfolio_id}/core-snapshot",
            max_attempts=1,
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(
        DpmCoreResolverUnavailableError, match="DPM_CORE_MANDATE_BINDING_UNAVAILABLE"
    ):
        client.resolve_execution_context(stateful_input=_stateful_input(), correlation_id=None)


def test_optional_profile_url_configuration_fails_source_safe() -> None:
    config = DpmCoreResolverConfig(
        base_url="https://core.example.test",
        benchmark_assignment_path_template="",
        client_restriction_profile_path_template="",
        sustainability_preference_profile_path_template="",
        client_income_needs_schedule_path_template="",
        liquidity_reserve_requirement_path_template="",
        planned_withdrawal_schedule_path_template="",
    )

    with pytest.raises(
        DpmCoreResolverUnavailableError,
        match="DPM_CORE_CLIENT_RESTRICTIONS_UNAVAILABLE",
    ):
        config.resolve_client_restriction_profile_url("PB_SG_GLOBAL_BAL_001")
    with pytest.raises(
        DpmCoreResolverUnavailableError,
        match="DPM_CORE_SUSTAINABILITY_PREFERENCES_UNAVAILABLE",
    ):
        config.resolve_sustainability_preference_profile_url("PB_SG_GLOBAL_BAL_001")
    with pytest.raises(
        DpmCoreResolverUnavailableError,
        match="DPM_CORE_BENCHMARK_ASSIGNMENT_UNAVAILABLE",
    ):
        config.resolve_benchmark_assignment_url("PB_SG_GLOBAL_BAL_001")
    with pytest.raises(
        DpmCoreResolverUnavailableError,
        match="DPM_CORE_INCOME_NEEDS_UNAVAILABLE",
    ):
        config.resolve_client_income_needs_schedule_url("PB_SG_GLOBAL_BAL_001")
    with pytest.raises(
        DpmCoreResolverUnavailableError,
        match="DPM_CORE_LIQUIDITY_RESERVE_UNAVAILABLE",
    ):
        config.resolve_liquidity_reserve_requirement_url("PB_SG_GLOBAL_BAL_001")
    with pytest.raises(
        DpmCoreResolverUnavailableError,
        match="DPM_CORE_PLANNED_WITHDRAWAL_UNAVAILABLE",
    ):
        config.resolve_planned_withdrawal_schedule_url("PB_SG_GLOBAL_BAL_001")


def test_get_source_product_retries_transient_status_and_rejects_non_object_payload() -> None:
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(503, json={"detail": "retry"})
        return httpx.Response(200, json=["not", "an", "object"])

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test", max_attempts=2),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(DpmCoreResolverError, match="DPM_CORE_SOURCE_INCOMPLETE"):
        client._get_source_product(
            url="https://core.example.test/source",
            params={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
            correlation_id="corr-get-retry",
            unavailable_code="DPM_CORE_SOURCE_UNAVAILABLE",
            incomplete_code="DPM_CORE_SOURCE_INCOMPLETE",
        )

    assert attempts["count"] == 2


def test_get_source_product_maps_transport_error_to_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test", max_attempts=1),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(DpmCoreResolverUnavailableError, match="DPM_CORE_SOURCE_UNAVAILABLE"):
        client._get_source_product(
            url="https://core.example.test/source",
            params={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
            correlation_id=None,
            unavailable_code="DPM_CORE_SOURCE_UNAVAILABLE",
            incomplete_code="DPM_CORE_SOURCE_INCOMPLETE",
        )


def test_source_product_helpers_retry_until_source_safe_unavailable() -> None:
    post_attempts = {"count": 0}

    def post_handler(request: httpx.Request) -> httpx.Response:
        post_attempts["count"] += 1
        raise httpx.ConnectError("connection refused", request=request)

    post_client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test", max_attempts=2),
        client=httpx.Client(transport=httpx.MockTransport(post_handler)),
    )

    with pytest.raises(DpmCoreResolverUnavailableError, match="DPM_CORE_SOURCE_UNAVAILABLE"):
        post_client._post_source_product(
            url="https://core.example.test/source",
            payload={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
            correlation_id=None,
            unavailable_code="DPM_CORE_SOURCE_UNAVAILABLE",
            incomplete_code="DPM_CORE_SOURCE_INCOMPLETE",
        )

    get_attempts = {"count": 0}

    def get_handler(request: httpx.Request) -> httpx.Response:
        get_attempts["count"] += 1
        raise httpx.ConnectError("connection refused", request=request)

    get_client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test", max_attempts=2),
        client=httpx.Client(transport=httpx.MockTransport(get_handler)),
    )

    with pytest.raises(DpmCoreResolverUnavailableError, match="DPM_CORE_SOURCE_UNAVAILABLE"):
        get_client._get_source_product(
            url="https://core.example.test/source",
            params={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
            correlation_id=None,
            unavailable_code="DPM_CORE_SOURCE_UNAVAILABLE",
            incomplete_code="DPM_CORE_SOURCE_INCOMPLETE",
        )

    assert post_attempts["count"] == 2
    assert get_attempts["count"] == 2


def test_owned_core_resolver_client_closes_managed_http_client() -> None:
    http_client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200)))
    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test")
    )
    client._client = http_client
    client._owns_client = True

    client.close()

    assert http_client.is_closed


def test_get_source_product_closes_transient_owned_http_client(monkeypatch: pytest.MonkeyPatch):
    closed = {"value": False}

    class _ManagedClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, url, params, headers):
            return httpx.Response(200, json={"source": "ready"})

        def close(self):
            closed["value"] = True

    monkeypatch.setattr(httpx, "Client", _ManagedClient)
    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test")
    )

    payload = client._get_source_product(
        url="https://core.example.test/source",
        params={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
        correlation_id=None,
        unavailable_code="DPM_CORE_SOURCE_UNAVAILABLE",
        incomplete_code="DPM_CORE_SOURCE_INCOMPLETE",
    )

    assert payload == {"source": "ready"}
    assert closed["value"] is True


def test_optional_resolvers_suppress_unavailable_source_products() -> None:
    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(
            base_url="https://core.example.test",
            transaction_cost_curve_path_template="",
            portfolio_cashflow_projection_path_template="",
            client_restriction_profile_path_template="",
            sustainability_preference_profile_path_template="",
            client_income_needs_schedule_path_template="",
            liquidity_reserve_requirement_path_template="",
            planned_withdrawal_schedule_path_template="",
        ),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(500, json={}))
        ),
    )

    assert (
        client._try_resolve_transaction_cost_curve(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=date(2026, 5, 3),
            security_ids=[],
            tenant_id="tenant_sg_pb",
            correlation_id=None,
        )
        is None
    )
    assert (
        client._try_resolve_transaction_cost_curve(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=date(2026, 5, 3),
            security_ids=["EQ_US_AAPL"],
            tenant_id="tenant_sg_pb",
            correlation_id=None,
        )
        is None
    )
    assert (
        client._try_resolve_portfolio_cashflow_projection(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=date(2026, 5, 3),
            horizon_days=30,
            include_projected=True,
            correlation_id=None,
        )
        is None
    )
    assert (
        client._try_resolve_client_restriction_profile(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=date(2026, 5, 3),
            tenant_id="tenant_sg_pb",
            mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
            correlation_id=None,
        )
        is None
    )
    assert (
        client._try_resolve_sustainability_preference_profile(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=date(2026, 5, 3),
            tenant_id="tenant_sg_pb",
            mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
            correlation_id=None,
        )
        is None
    )
    assert (
        client._try_resolve_client_income_needs_schedule(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=date(2026, 5, 3),
            tenant_id="tenant_sg_pb",
            mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
            correlation_id=None,
        )
        is None
    )
    assert (
        client._try_resolve_liquidity_reserve_requirement(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=date(2026, 5, 3),
            tenant_id="tenant_sg_pb",
            mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
            correlation_id=None,
        )
        is None
    )
    assert (
        client._try_resolve_planned_withdrawal_schedule(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=date(2026, 5, 3),
            tenant_id="tenant_sg_pb",
            mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
            horizon_days=365,
            correlation_id=None,
        )
        is None
    )
