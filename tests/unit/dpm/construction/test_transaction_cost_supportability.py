from decimal import Decimal

from src.api.services.construction_transaction_cost_supportability import (
    _observed_transaction_cost_money,
    _observed_transaction_cost_term,
    _observed_transaction_cost_terms,
    covered_transaction_cost_security_ids,
    observed_transaction_cost_estimate,
    transaction_cost_curve_points_by_key,
    transaction_cost_reason_codes,
    transaction_cost_status,
    traded_transaction_cost_security_ids,
    with_observed_transaction_cost_estimate,
)
from src.core.construction import build_rebalance_result_alternative
from src.core.construction.models import (
    AuthoritativeTransactionCostContext,
    AuthoritativeTransactionCostPoint,
)
from src.core.construction.vocabulary import ConstructionMethodStatus, ConstructionTraceTerm
from src.core.models import EngineOptions, RebalanceResult
from src.core.rebalance.engine import run_simulation
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    position,
    price,
    shelf_entry,
    target,
)


def _trade_result() -> RebalanceResult:
    return run_simulation(
        portfolio=portfolio_snapshot(
            portfolio_id="pf_cost_1",
            base_currency="USD",
            positions=[position("EQ_A", "10")],
            cash_balances=[cash("USD", "0")],
        ),
        market_data=market_data_snapshot(
            prices=[
                price("EQ_A", "100", "USD"),
                price("EQ_B", "100", "USD"),
            ]
        ),
        model=model_portfolio(
            targets=[
                target("EQ_A", "0.50"),
                target("EQ_B", "0.50"),
            ]
        ),
        shelf=[
            shelf_entry("EQ_A", status="APPROVED", asset_class="EQUITY"),
            shelf_entry("EQ_B", status="APPROVED", asset_class="EQUITY"),
        ],
        options=EngineOptions(),
        request_hash="hash-cost",
        correlation_id="corr-cost",
    )


def _transaction_cost_context(*, security_ids: list[str]) -> AuthoritativeTransactionCostContext:
    return AuthoritativeTransactionCostContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-core",
        as_of_date="2026-06-01",
        window_start_date="2026-05-01",
        window_end_date="2026-06-01",
        returned_curve_point_count=len(security_ids),
        curve_points=[
            AuthoritativeTransactionCostPoint(
                security_id=security_id,
                transaction_type=transaction_type,
                currency="USD",
                observation_count=3,
                total_notional=Decimal("1000"),
                total_cost=Decimal("1"),
                average_cost_bps=Decimal("10"),
                min_cost_bps=Decimal("8"),
                max_cost_bps=Decimal("12"),
                first_observed_date="2026-05-01",
                last_observed_date="2026-06-01",
            )
            for security_id, transaction_type in (
                (security_ids[0], "SELL"),
                (security_ids[-1], "BUY"),
            )
        ],
        reason_codes=["TRANSACTION_COST_CURVE_READY"],
    )


def test_transaction_cost_supportability_applies_observed_curve_to_candidate_notionals() -> None:
    result = _trade_result()
    context = _transaction_cost_context(security_ids=["EQ_A", "EQ_B"])
    alternative = build_rebalance_result_alternative(result=result)

    estimate = observed_transaction_cost_estimate(result=result, context=context)
    enriched = with_observed_transaction_cost_estimate(
        alternative=alternative,
        result=result,
        context=context,
    )

    assert estimate is not None
    assert estimate.amount == Decimal("1.0000")
    assert enriched.comparison_metrics.estimated_transaction_cost == estimate
    assert ConstructionTraceTerm.ESTIMATED_COST in {
        trace.term for trace in enriched.objective_trace
    }
    assert transaction_cost_status(result=result, context=context) == ConstructionMethodStatus.READY
    assert "TRANSACTION_COST_CURVE_APPLIED_TO_CANDIDATE_NOTIONALS" in transaction_cost_reason_codes(
        result=result, context=context
    )


def test_transaction_cost_security_id_helpers_preserve_traded_and_covered_sets() -> None:
    result = _trade_result()
    context = _transaction_cost_context(security_ids=["EQ_A", "EQ_B"])

    assert traded_transaction_cost_security_ids(result=result) == {"EQ_A", "EQ_B"}
    assert covered_transaction_cost_security_ids(context=context) == {"EQ_A", "EQ_B"}


def test_transaction_cost_curve_points_by_key_indexes_security_and_transaction_type() -> None:
    context = _transaction_cost_context(security_ids=["EQ_A", "EQ_B"])

    points_by_key = transaction_cost_curve_points_by_key(context=context)

    assert sorted(points_by_key) == [("EQ_A", "SELL"), ("EQ_B", "BUY")]
    assert points_by_key[("EQ_A", "SELL")].average_cost_bps == Decimal("10")


def test_observed_transaction_cost_term_helpers_match_supported_trade_terms() -> None:
    result = _trade_result()
    context = _transaction_cost_context(security_ids=["EQ_A", "EQ_B"])
    points_by_key = transaction_cost_curve_points_by_key(context=context)

    assert _observed_transaction_cost_term(
        intent=result.intents[0],
        point_by_key=points_by_key,
    ) == Decimal("0.5")
    assert _observed_transaction_cost_terms(
        result=result,
        point_by_key=points_by_key,
    ) == [Decimal("0.5"), Decimal("0.5")]


def test_observed_transaction_cost_money_requires_matched_cost_terms() -> None:
    assert _observed_transaction_cost_money(cost_terms=[], currency="USD") is None
    money = _observed_transaction_cost_money(
        cost_terms=[Decimal("0.12345"), Decimal("0.87655")],
        currency="USD",
    )

    assert money is not None
    assert money.amount == Decimal("1.0000")


def test_transaction_cost_supportability_degrades_missing_traded_security_coverage() -> None:
    result = _trade_result()
    context = _transaction_cost_context(security_ids=["EQ_A", "NOT_TRADED"])

    assert (
        transaction_cost_status(result=result, context=context) == ConstructionMethodStatus.DEGRADED
    )
    assert "TRANSACTION_COST_CURVE_MISSING_TRADED_SECURITIES" in transaction_cost_reason_codes(
        result=result,
        context=context,
    )
