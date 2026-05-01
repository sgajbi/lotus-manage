import pytest

from src.core.dpm_source_context import (
    DpmCoreContextIncompleteError,
    DpmCoreExecutionContext,
    build_batch_rebalance_request_from_core_context,
    build_rebalance_request_from_core_context,
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


def test_incomplete_core_context_is_not_transformed():
    context = _core_context(supportability_state="INCOMPLETE")

    with pytest.raises(DpmCoreContextIncompleteError, match="DPM_CORE_CONTEXT_READY"):
        build_rebalance_request_from_core_context(context=context, options_override={})
