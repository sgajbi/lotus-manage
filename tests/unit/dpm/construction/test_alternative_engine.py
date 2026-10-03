from decimal import Decimal
from copy import deepcopy

import pytest
from pydantic import ValidationError
from src.core.construction.models import ConstructionAlternative

from src.core.construction import (
    ConstructionMethod,
    ConstructionMethodStatus,
    ConstructionTraceTerm,
    build_alternative_set,
    build_do_nothing_baseline,
    build_rebalance_result_alternative,
)
from src.core.construction.alternative_engine import (
    _security_trade_change_notional,
    _security_trade_change_row,
)
from src.core.models import EngineOptions, RebalanceResult
from src.core.rebalance.engine import run_simulation
from tests.shared.factories import (
    cash,
    fx,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    position,
    price,
    shelf_entry,
    target,
)


def _ready_rebalance_result() -> RebalanceResult:
    portfolio = portfolio_snapshot(
        portfolio_id="pf_construct_1",
        base_currency="USD",
        positions=[position("EQ_A", "10")],
        cash_balances=[cash("USD", "0")],
    )
    market_data = market_data_snapshot(
        prices=[
            price("EQ_A", "100", "USD"),
            price("EQ_B", "100", "USD"),
        ]
    )
    model = model_portfolio(
        targets=[
            target("EQ_A", "0.50"),
            target("EQ_B", "0.50"),
        ]
    )
    shelf = [
        shelf_entry("EQ_A", status="APPROVED", asset_class="EQUITY"),
        shelf_entry("EQ_B", status="APPROVED", asset_class="EQUITY"),
    ]
    return run_simulation(
        portfolio=portfolio,
        market_data=market_data,
        model=model,
        shelf=shelf,
        options=EngineOptions(),
        request_hash="hash_construct_1",
        correlation_id="corr_construct_1",
    )


def test_do_nothing_baseline_has_no_trades_and_no_drift_reduction() -> None:
    result = _ready_rebalance_result()

    baseline = build_do_nothing_baseline(result=result)

    assert baseline.method == ConstructionMethod.DO_NOTHING_BASELINE
    assert baseline.method_status == ConstructionMethodStatus.READY
    assert baseline.intent_ids == []
    assert baseline.rebalance_run_id is None
    assert baseline.evaluation_context is not None
    assert baseline.evaluation_context.rebalance_run_id == result.rebalance_run_id
    assert baseline.evaluation_context.state_basis == "BEFORE"
    assert baseline.diagnostics["proposed_changes"] == []
    assert baseline.comparison_metrics.trade_count == 0
    assert baseline.comparison_metrics.turnover_weight == Decimal("0.0000")
    assert baseline.comparison_metrics.drift_before == Decimal("1.0000")
    assert baseline.comparison_metrics.drift_after == Decimal("1.0000")
    assert baseline.comparison_metrics.drift_reduction == Decimal("0.0000")


def test_rebalance_result_wraps_heuristic_as_comparable_alternative() -> None:
    result = _ready_rebalance_result()

    alternative = build_rebalance_result_alternative(result=result)

    assert alternative.method == ConstructionMethod.HEURISTIC_EXPLAINABLE
    assert alternative.method_status == ConstructionMethodStatus.READY
    assert alternative.rebalance_run_id == result.rebalance_run_id
    assert alternative.comparison_metrics.trade_count == 2
    assert alternative.comparison_metrics.turnover_weight == Decimal("1.0000")
    assert alternative.comparison_metrics.drift_after == Decimal("0.0000")
    assert alternative.comparison_metrics.drift_reduction == Decimal("1.0000")
    assert {term.term for term in alternative.objective_trace} == {
        ConstructionTraceTerm.DRIFT,
        ConstructionTraceTerm.TURNOVER,
    }
    proposed_changes = alternative.diagnostics["proposed_changes"]
    assert proposed_changes == [
        {
            "intent_id": "oi_1",
            "security_id": "EQ_A",
            "action": "SELL",
            "quantity": "5",
            "estimated_value": "500.0",
            "currency": "USD",
            "reason": "Align",
            "reason_code": "DRIFT_REBALANCE",
        },
        {
            "intent_id": "oi_2",
            "security_id": "EQ_B",
            "action": "BUY",
            "quantity": "5",
            "estimated_value": "500.0",
            "currency": "USD",
            "reason": "Align",
            "reason_code": "DRIFT_REBALANCE",
        },
    ]


@pytest.mark.parametrize(
    "quote_currency,rate,quantity,cash_weight",
    [("USD", "1", "20", "0.3333"), ("EUR", "1.25", "12", "0.2857")],
)
def test_no_action_retains_current_economics_when_heuristic_needs_security_and_fx(
    quote_currency: str, rate: str, quantity: str, cash_weight: str
) -> None:
    result = run_simulation(
        portfolio=portfolio_snapshot(
            base_currency="USD",
            positions=[position("EQ_A", "100")],
            cash_balances=[cash("USD", "5000")],
        ),
        market_data=market_data_snapshot(
            prices=[price("EQ_A", "100", quote_currency)],
            fx_rates=[fx("EUR/USD", rate)] if quote_currency == "EUR" else [],
        ),
        model=model_portfolio(targets=[target("EQ_A", "0.80")]),
        shelf=[shelf_entry("EQ_A", status="APPROVED", asset_class="EQUITY")],
        options=EngineOptions(
            enable_settlement_awareness=False,
            enable_tax_awareness=False,
            fx_buffer_pct=Decimal("0.01"),
        ),
        request_hash="hash-no-action-economics",
        correlation_id="corr-no-action-economics",
    )
    assert result.status == "READY"
    expected_nav = Decimal("100") * Decimal("100") * Decimal(rate) + Decimal("5000")
    assert result.before.total_value.amount == expected_nav
    assert result.after_simulated.total_value.amount == expected_nav
    assert result.before.positions[0].quantity == Decimal("100")
    assert result.after_simulated.positions[0].quantity == Decimal("100") + Decimal(quantity)
    assert next(
        balance.amount for balance in result.before.cash_balances if balance.currency == "USD"
    ) == Decimal("5000")
    # FX funding buys the security notional plus a 1% buffer, leaving that buffer in EUR.
    quote_cash = (
        Decimal(quantity) * Decimal("100") * Decimal("0.01")
        if quote_currency == "EUR"
        else Decimal("0")
    )
    assert next(
        balance.amount
        for balance in result.after_simulated.cash_balances
        if balance.currency == "USD"
    ) == expected_nav * Decimal("0.20") - quote_cash * Decimal(rate)
    if quote_currency == "EUR":
        assert (
            next(
                balance.amount
                for balance in result.after_simulated.cash_balances
                if balance.currency == "EUR"
            )
            == quote_cash
        )
    baseline = build_do_nothing_baseline(result=result)
    heuristic = build_rebalance_result_alternative(result=result)
    assert baseline.rebalance_run_id is None
    assert baseline.intent_ids == []
    assert baseline.diagnostics["proposed_changes"] == []
    assert baseline.comparison_metrics.cash_weight_after == Decimal(cash_weight)
    assert baseline.comparison_metrics.drift_after == baseline.comparison_metrics.drift_before
    assert baseline.comparison_metrics.trade_count == 0
    assert baseline.comparison_metrics.turnover_weight == 0
    assert heuristic.rebalance_run_id == result.rebalance_run_id
    assert heuristic.diagnostics["proposed_changes"][0]["quantity"] == quantity
    assert heuristic.comparison_metrics.cash_weight_after == Decimal("0.2000")
    if quote_currency == "EUR":
        assert any(intent.intent_type == "FX_SPOT" for intent in result.intents)


def test_legacy_baseline_reference_is_read_as_audit_context_without_mutating_payload() -> None:
    result = _ready_rebalance_result()
    legacy = build_do_nothing_baseline(result=result).model_dump(mode="json")
    legacy.pop("evaluation_context")
    legacy["rebalance_run_id"] = result.rebalance_run_id
    legacy["intent_ids"] = [intent.intent_id for intent in result.intents]
    legacy["diagnostics"]["proposed_changes"] = build_rebalance_result_alternative(
        result=result
    ).diagnostics["proposed_changes"]
    retained = deepcopy(legacy)
    loaded = ConstructionAlternative.model_validate(legacy)
    assert legacy == retained
    assert loaded.rebalance_run_id is None
    assert loaded.evaluation_context.rebalance_run_id == result.rebalance_run_id
    assert loaded.intent_ids == []
    assert loaded.diagnostics["proposed_changes"] == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("rebalance_run_id", "rr_wrong"),
        ("intent_ids", ["oi_wrong"]),
        ("diagnostics", {"proposed_changes": [{"action": "BUY"}]}),
    ],
)
def test_explicit_no_action_contract_rejects_action_material(field: str, value: object) -> None:
    payload = build_do_nothing_baseline(result=_ready_rebalance_result()).model_dump(mode="json")
    payload[field] = value
    with pytest.raises(ValidationError, match="CONSTRUCTION_NO_ACTION_ECONOMICS_MISMATCH"):
        ConstructionAlternative.model_validate(payload)


@pytest.mark.parametrize("amount", ["10.00", "-10.00", "0.00"])
def test_no_action_comparator_rejects_transaction_cost_estimates(amount: str) -> None:
    payload = build_do_nothing_baseline(result=_ready_rebalance_result()).model_dump(mode="json")
    payload["comparison_metrics"]["estimated_transaction_cost"] = {
        "amount": amount,
        "currency": "USD",
    }
    with pytest.raises(ValidationError, match="CONSTRUCTION_NO_ACTION_ECONOMICS_MISMATCH"):
        ConstructionAlternative.model_validate(payload)


def test_no_action_comparator_has_no_transaction_cost_estimate() -> None:
    baseline = build_do_nothing_baseline(result=_ready_rebalance_result())
    assert baseline.comparison_metrics.estimated_transaction_cost is None


def test_rebalance_result_proposed_changes_preserve_constraint_labels() -> None:
    result = _ready_rebalance_result()
    result = result.model_copy(
        update={
            "intents": [
                result.intents[0].model_copy(update={"constraints_applied": ["MIN_LOT_SIZE"]}),
                *result.intents[1:],
            ]
        }
    )

    alternative = build_rebalance_result_alternative(result=result)

    proposed_changes = alternative.diagnostics["proposed_changes"]
    assert proposed_changes[0]["constraints_applied"] == ["MIN_LOT_SIZE"]


def test_security_trade_change_notional_prefers_base_notional() -> None:
    intent = _ready_rebalance_result().intents[0]
    assert _security_trade_change_notional(intent) == intent.notional_base

    without_base = intent.model_copy(update={"notional_base": None})
    assert _security_trade_change_notional(without_base) == intent.notional


def test_security_trade_change_row_maps_optional_trade_evidence() -> None:
    intent = (
        _ready_rebalance_result()
        .intents[0]
        .model_copy(update={"constraints_applied": ["MIN_LOT_SIZE"]})
    )

    assert _security_trade_change_row(intent) == {
        "intent_id": "oi_1",
        "security_id": "EQ_A",
        "action": "SELL",
        "quantity": "5",
        "estimated_value": "500.0",
        "currency": "USD",
        "reason": "Align",
        "reason_code": "DRIFT_REBALANCE",
        "constraints_applied": ["MIN_LOT_SIZE"],
    }


def test_alternative_set_rolls_up_conservative_status() -> None:
    result = _ready_rebalance_result()
    baseline = build_do_nothing_baseline(result=result)
    heuristic = build_rebalance_result_alternative(result=result)
    blocked = heuristic.model_copy(update={"method_status": ConstructionMethodStatus.BLOCKED})

    alternative_set = build_alternative_set(
        alternative_set_id="alts_pf_construct_1",
        portfolio_id="pf_construct_1",
        as_of="2026-04-10",
        alternatives=[baseline, heuristic, blocked],
    )

    assert alternative_set.status == ConstructionMethodStatus.BLOCKED
    assert [alternative.method for alternative in alternative_set.alternatives] == [
        ConstructionMethod.DO_NOTHING_BASELINE,
        ConstructionMethod.HEURISTIC_EXPLAINABLE,
        ConstructionMethod.HEURISTIC_EXPLAINABLE,
    ]
