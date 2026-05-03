from decimal import Decimal

from src.core.construction import (
    AuthoritativePerformanceContext,
    AuthoritativeRiskContext,
    ConstructionMethodStatus,
    estimate_transaction_cost,
    summarize_enrichment_posture,
)
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


def _trade_result(*, max_turnover_pct: Decimal | None = None) -> RebalanceResult:
    portfolio = portfolio_snapshot(
        portfolio_id="pf_enrich_1",
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
        options=EngineOptions(max_turnover_pct=max_turnover_pct),
        request_hash="hash_enrich_1",
        correlation_id="corr_enrich_1",
    )


def test_transaction_cost_estimate_is_labelled_local_and_reconciles_to_turnover_notional() -> None:
    result = _trade_result()

    cost = estimate_transaction_cost(result=result, basis_points=Decimal("10"))

    assert cost.currency == "USD"
    assert cost.amount == Decimal("1.00")


def test_enrichment_summary_blocks_required_tax_without_tax_impact() -> None:
    result = _trade_result()

    summary = summarize_enrichment_posture(result=result, tax_required=True)

    assert summary.tax_status == ConstructionMethodStatus.BLOCKED
    assert summary.cost_status == ConstructionMethodStatus.DEGRADED
    assert summary.risk_status == ConstructionMethodStatus.DEGRADED
    assert summary.performance_status == ConstructionMethodStatus.DEGRADED
    assert "TAX_LOTS_REQUIRED_BUT_NO_TAX_IMPACT" in summary.reason_codes
    assert "AUTHORITATIVE_TRANSACTION_COST_UNAVAILABLE" in summary.reason_codes
    assert "RISK_ENRICHMENT_UNAVAILABLE" in summary.reason_codes
    assert "PERFORMANCE_CONTEXT_UNAVAILABLE" in summary.reason_codes


def test_enrichment_summary_marks_turnover_pending_review_when_budget_drops_intents() -> None:
    result = _trade_result(max_turnover_pct=Decimal("0.25"))

    summary = summarize_enrichment_posture(result=result, tax_required=False)

    assert summary.turnover_status == ConstructionMethodStatus.PENDING_REVIEW
    assert "TURNOVER_BUDGET_DROPPED_INTENTS" in summary.reason_codes


def test_enrichment_summary_does_not_bleed_optional_authority_reason_codes() -> None:
    result = _trade_result()

    summary = summarize_enrichment_posture(
        result=result,
        tax_required=False,
        risk_required=False,
        performance_required=False,
    )

    assert summary.risk_status == ConstructionMethodStatus.READY
    assert summary.performance_status == ConstructionMethodStatus.READY
    assert "RISK_ENRICHMENT_UNAVAILABLE" not in summary.reason_codes
    assert "PERFORMANCE_CONTEXT_UNAVAILABLE" not in summary.reason_codes


def test_enrichment_summary_preserves_authoritative_risk_and_performance_status() -> None:
    result = _trade_result()

    summary = summarize_enrichment_posture(
        result=result,
        tax_required=False,
        risk_context=AuthoritativeRiskContext(
            supportability_status=ConstructionMethodStatus.PENDING_REVIEW,
            source_system="lotus-risk",
            tracking_error=Decimal("0.042"),
            concentration_breaches=1,
            reason_codes=["RISK_TRACKING_ERROR_ATTENTION"],
        ),
        performance_context=AuthoritativePerformanceContext(
            supportability_status=ConstructionMethodStatus.READY,
            source_system="lotus-performance",
            benchmark_id="BM_GLOBAL_BAL",
            active_return=Decimal("-0.012"),
            underperformance_flag=True,
            reason_codes=["PERFORMANCE_UNDER_REVIEW"],
        ),
    )

    assert summary.risk_status == ConstructionMethodStatus.PENDING_REVIEW
    assert summary.performance_status == ConstructionMethodStatus.READY
    assert "RISK_TRACKING_ERROR_ATTENTION" in summary.reason_codes
    assert "PERFORMANCE_UNDER_REVIEW" in summary.reason_codes
    assert "RISK_ENRICHMENT_UNAVAILABLE" not in summary.reason_codes
    assert "PERFORMANCE_CONTEXT_UNAVAILABLE" not in summary.reason_codes
