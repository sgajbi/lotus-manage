import pytest
from decimal import Decimal

from src.core.dpm_source_context import (
    DpmCoreContextIncompleteError,
    DpmCoreExecutionContext,
    DpmCoreInstrumentEligibilityBulkResponse,
    DpmCoreMandateBindingResponse,
    DpmCoreModelPortfolioTargetResponse,
    build_batch_rebalance_request_from_core_context,
    build_model_portfolio_from_core_targets,
    build_policy_context_from_core_mandate,
    build_rebalance_request_from_core_context,
    build_shelf_entries_from_core_eligibility,
)
from src.core.models import SimulationScenario


def _core_context(*, supportability_state: str = "READY") -> DpmCoreExecutionContext:
    return DpmCoreExecutionContext.model_validate(
        {
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
            "shelf_entries": [
                {
                    "instrument_id": "EQ_1",
                    "status": "APPROVED",
                    "asset_class": "EQUITY",
                    "issuer_id": "ISSUER_1",
                    "settlement_days": 2,
                }
            ],
            "policy_context": {
                "recommended_policy_pack_id": "dpm_standard_v1",
                "tenant_id": "tenant_001",
                "booking_center_code": "SG",
                "mandate_id": "mandate_balanced_discretionary",
            },
            "source_lineage": {
                "portfolio_snapshot_id": "core-pf-snap-001",
                "market_data_snapshot_id": "core-md-snap-001",
                "model_portfolio_id": "model_balanced_sgd",
                "model_portfolio_version": "2026-03-25",
                "shelf_version": "shelf_sg_v1",
                "integration_policy_version": "dpm-core-context.v1",
                "source_lineage_bundle_id": "lineage-bundle-001",
            },
            "supportability": {
                "state": supportability_state,
                "reason": "DPM_CORE_CONTEXT_READY",
                "freshness_bucket": "same_day",
            },
        }
    )


def test_core_context_transforms_all_engine_inputs_and_options():
    request = build_rebalance_request_from_core_context(
        context=_core_context(),
        options_override={"enable_tax_awareness": True, "enable_settlement_awareness": True},
    )

    assert request.portfolio_snapshot.portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert request.portfolio_snapshot.cash_balances[0].amount == 10000
    assert request.market_data_snapshot.prices[0].instrument_id == "EQ_1"
    assert request.model_portfolio.targets[0].weight == 1
    assert request.shelf_entries[0].settlement_days == 2
    assert request.options.enable_tax_awareness is True
    assert request.options.enable_settlement_awareness is True


def test_core_context_transforms_stateful_batch_scenarios():
    request = build_batch_rebalance_request_from_core_context(
        context=_core_context(),
        scenarios={
            "baseline": SimulationScenario(options={}),
            "tax_budget": SimulationScenario(options={"max_realized_capital_gains": "2500"}),
        },
    )

    assert sorted(request.scenarios) == ["baseline", "tax_budget"]
    assert request.portfolio_snapshot.snapshot_id == "core-pf-snap-001"
    assert request.market_data_snapshot.snapshot_id == "core-md-snap-001"


def test_core_model_targets_transform_to_manage_model_portfolio():
    response = DpmCoreModelPortfolioTargetResponse.model_validate(
        {
            "product_name": "DpmModelPortfolioTarget",
            "product_version": "v1",
            "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
            "model_portfolio_version": "2026.04",
            "as_of_date": "2026-04-10",
            "display_name": "Singapore Global Balanced DPM Model",
            "base_currency": "SGD",
            "risk_profile": "balanced",
            "mandate_type": "discretionary",
            "approval_status": "approved",
            "effective_from": "2026-04-10",
            "targets": [
                {
                    "instrument_id": "EQ_US_AAPL",
                    "target_weight": "0.6000000000",
                    "target_status": "active",
                    "quality_status": "accepted",
                },
                {
                    "instrument_id": "FI_US_TREASURY_10Y",
                    "target_weight": "0.4000000000",
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
        }
    )

    model = build_model_portfolio_from_core_targets(response)

    assert [(target.instrument_id, target.weight) for target in model.targets] == [
        ("EQ_US_AAPL", Decimal("0.6000000000")),
        ("FI_US_TREASURY_10Y", Decimal("0.4000000000")),
    ]


def test_core_model_targets_reject_incomplete_supportability():
    response = DpmCoreModelPortfolioTargetResponse.model_validate(
        {
            "product_name": "DpmModelPortfolioTarget",
            "product_version": "v1",
            "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
            "model_portfolio_version": "2026.04",
            "as_of_date": "2026-04-10",
            "display_name": "Singapore Global Balanced DPM Model",
            "base_currency": "SGD",
            "risk_profile": "balanced",
            "mandate_type": "discretionary",
            "approval_status": "approved",
            "effective_from": "2026-04-10",
            "targets": [],
            "supportability": {
                "state": "INCOMPLETE",
                "reason": "MODEL_TARGETS_EMPTY",
                "target_count": 0,
                "total_target_weight": "0",
            },
        }
    )

    with pytest.raises(DpmCoreContextIncompleteError, match="MODEL_TARGETS_EMPTY"):
        build_model_portfolio_from_core_targets(response)


def _core_mandate_binding_payload(**overrides: object) -> dict:
    payload = {
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
        "rebalance_frequency": "monthly",
        "rebalance_bands": {
            "default_band": "0.0250000000",
            "cash_reserve_weight": "0.0200000000",
        },
        "effective_from": "2026-04-01",
        "binding_version": 1,
        "supportability": {
            "state": "READY",
            "reason": "MANDATE_BINDING_READY",
            "missing_data_families": [],
        },
    }
    payload.update(overrides)
    return payload


def test_core_mandate_binding_transforms_to_policy_context():
    response = DpmCoreMandateBindingResponse.model_validate(_core_mandate_binding_payload())

    policy_context = build_policy_context_from_core_mandate(
        response,
        tenant_id="tenant_sg_pb",
    )

    assert policy_context.recommended_policy_pack_id == "POLICY_DPM_SG_BALANCED_V1"
    assert policy_context.tenant_id == "tenant_sg_pb"
    assert policy_context.booking_center_code == "Singapore"
    assert policy_context.mandate_id == "MANDATE_PB_SG_GLOBAL_BAL_001"


def test_core_mandate_binding_rejects_incomplete_supportability():
    response = DpmCoreMandateBindingResponse.model_validate(
        _core_mandate_binding_payload(
            supportability={
                "state": "INCOMPLETE",
                "reason": "MANDATE_POLICY_PACK_MISSING",
                "missing_data_families": ["policy_pack"],
            }
        )
    )

    with pytest.raises(DpmCoreContextIncompleteError, match="MANDATE_POLICY_PACK_MISSING"):
        build_policy_context_from_core_mandate(response)


def test_core_mandate_binding_rejects_non_discretionary_or_inactive_authority():
    non_discretionary = DpmCoreMandateBindingResponse.model_validate(
        _core_mandate_binding_payload(mandate_type="advisory")
    )
    inactive_authority = DpmCoreMandateBindingResponse.model_validate(
        _core_mandate_binding_payload(discretionary_authority_status="suspended")
    )

    with pytest.raises(DpmCoreContextIncompleteError, match="DPM_CORE_MANDATE_NOT_DISCRETIONARY"):
        build_policy_context_from_core_mandate(non_discretionary)

    with pytest.raises(
        DpmCoreContextIncompleteError,
        match="DPM_CORE_DISCRETIONARY_AUTHORITY_NOT_ACTIVE",
    ):
        build_policy_context_from_core_mandate(inactive_authority)


def _core_eligibility_payload(**overrides: object) -> dict:
    payload = {
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
            },
            {
                "security_id": "FO_PRIV_PRIVATE_CREDIT_A",
                "found": True,
                "eligibility_status": "RESTRICTED",
                "product_shelf_status": "RESTRICTED",
                "buy_allowed": False,
                "sell_allowed": True,
                "restriction_reason_codes": ["PRIVATE_ASSET_REVIEW"],
                "settlement_days": 5,
                "settlement_calendar_id": "SGX",
                "liquidity_tier": "L4",
                "issuer_id": "PRIVATE_CREDIT_FUND_A",
                "issuer_name": "Private Credit Fund A",
                "ultimate_parent_issuer_id": "ALT_PARENT",
                "ultimate_parent_issuer_name": "Alternative Investments Parent",
                "asset_class": "Alternatives",
                "country_of_risk": "SG",
                "effective_from": "2026-04-01",
                "effective_to": None,
                "source_record_id": "priv-credit-elig-20260401",
                "quality_status": "accepted",
            },
        ],
        "supportability": {
            "state": "READY",
            "reason": "INSTRUMENT_ELIGIBILITY_READY",
            "requested_count": 2,
            "found_count": 2,
            "missing_security_ids": [],
        },
        "lineage": {
            "source_system": "instrument_eligibility",
            "contract_version": "rfc_087_v1",
        },
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-04-10T09:00:00Z",
    }
    payload.update(overrides)
    return payload


def test_core_instrument_eligibility_transforms_to_shelf_entries():
    response = DpmCoreInstrumentEligibilityBulkResponse.model_validate(_core_eligibility_payload())

    shelf_entries = build_shelf_entries_from_core_eligibility(response)

    assert [(entry.instrument_id, entry.status) for entry in shelf_entries] == [
        ("EQ_US_AAPL", "APPROVED"),
        ("FO_PRIV_PRIVATE_CREDIT_A", "RESTRICTED"),
    ]
    restricted_entry = shelf_entries[1]
    assert restricted_entry.asset_class == "Alternatives"
    assert restricted_entry.issuer_id == "PRIVATE_CREDIT_FUND_A"
    assert restricted_entry.liquidity_tier == "L4"
    assert restricted_entry.settlement_days == 5
    assert restricted_entry.attributes["buy_allowed"] == "false"
    assert restricted_entry.attributes["sell_allowed"] == "true"
    assert restricted_entry.attributes["restriction_reason_codes"] == "PRIVATE_ASSET_REVIEW"
    assert restricted_entry.attributes["settlement_calendar_id"] == "SGX"
    assert restricted_entry.attributes["ultimate_parent_issuer_id"] == "ALT_PARENT"


def test_core_instrument_eligibility_rejects_missing_supportability():
    response = DpmCoreInstrumentEligibilityBulkResponse.model_validate(
        _core_eligibility_payload(
            eligibility=[
                {
                    "security_id": "UNKNOWN_SEC",
                    "found": False,
                    "eligibility_status": "UNKNOWN",
                    "product_shelf_status": "SUSPENDED",
                    "buy_allowed": False,
                    "sell_allowed": False,
                    "restriction_reason_codes": ["ELIGIBILITY_PROFILE_MISSING"],
                    "settlement_days": None,
                    "settlement_calendar_id": None,
                    "quality_status": "MISSING",
                }
            ],
            supportability={
                "state": "INCOMPLETE",
                "reason": "INSTRUMENT_ELIGIBILITY_MISSING",
                "requested_count": 1,
                "found_count": 0,
                "missing_security_ids": ["UNKNOWN_SEC"],
            },
        )
    )

    with pytest.raises(DpmCoreContextIncompleteError, match="INSTRUMENT_ELIGIBILITY_MISSING"):
        build_shelf_entries_from_core_eligibility(response)


def test_incomplete_core_context_is_not_transformed():
    context = _core_context(supportability_state="INCOMPLETE")

    with pytest.raises(DpmCoreContextIncompleteError, match="DPM_CORE_CONTEXT_READY"):
        build_rebalance_request_from_core_context(context=context, options_override={})
