from decimal import Decimal

from src.api.request_models import RebalanceRequest
from src.api.services.construction_supportability_application import (
    apply_construction_supportability,
)
from src.core.construction import build_rebalance_result_alternative
from src.core.construction.method_registry import resolve_method_plan
from src.core.construction.models import (
    AuthoritativeTransactionCostContext,
    AuthoritativeTransactionCostPoint,
    ConstructionAuthorityContext,
)
from src.core.construction.vocabulary import ConstructionMethod, ConstructionMethodStatus
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
    valid_api_payload,
)


def _request() -> RebalanceRequest:
    return RebalanceRequest.model_validate(valid_api_payload())


def _trade_result() -> RebalanceResult:
    return run_simulation(
        portfolio=portfolio_snapshot(
            portfolio_id="pf_supportability_application_1",
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
        request_hash="hash-supportability-application",
        correlation_id="corr-supportability-application",
    )


def _transaction_cost_context() -> AuthoritativeTransactionCostContext:
    return AuthoritativeTransactionCostContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-core",
        as_of_date="2026-06-01",
        window_start_date="2026-05-01",
        window_end_date="2026-06-01",
        returned_curve_point_count=2,
        curve_points=[
            AuthoritativeTransactionCostPoint(
                security_id="EQ_A",
                transaction_type="SELL",
                currency="USD",
                observation_count=3,
                total_notional=Decimal("1000"),
                total_cost=Decimal("1"),
                average_cost_bps=Decimal("10"),
                min_cost_bps=Decimal("8"),
                max_cost_bps=Decimal("12"),
                first_observed_date="2026-05-01",
                last_observed_date="2026-06-01",
            ),
            AuthoritativeTransactionCostPoint(
                security_id="EQ_B",
                transaction_type="BUY",
                currency="USD",
                observation_count=3,
                total_notional=Decimal("1000"),
                total_cost=Decimal("1"),
                average_cost_bps=Decimal("10"),
                min_cost_bps=Decimal("8"),
                max_cost_bps=Decimal("12"),
                first_observed_date="2026-05-01",
                last_observed_date="2026-06-01",
            ),
        ],
        reason_codes=["TRANSACTION_COST_CURVE_READY"],
    )


def test_supportability_application_attaches_cost_evidence_and_diagnostics() -> None:
    result = _trade_result()
    enriched = apply_construction_supportability(
        request=_request(),
        method=ConstructionMethod.COST_AWARE,
        alternative=build_rebalance_result_alternative(
            result=result,
            method=ConstructionMethod.COST_AWARE,
            alternative_id="alt_cost_aware",
        ),
        result=result,
        plan=resolve_method_plan(ConstructionMethod.COST_AWARE, solver_available=True),
        authority_context=ConstructionAuthorityContext(
            transaction_cost_context=_transaction_cost_context()
        ),
    )

    assert enriched.method_status == ConstructionMethodStatus.READY
    assert enriched.comparison_metrics.estimated_transaction_cost is not None
    assert enriched.diagnostics["method_plan"]["requested_method"] == "COST_AWARE"
    enrichment_reason_codes = enriched.diagnostics["enrichment_summary"]["reason_codes"]
    assert "TRANSACTION_COST_CURVE_APPLIED_TO_CANDIDATE_NOTIONALS" in enrichment_reason_codes
    assert (
        enriched.diagnostics["authority_context"]["transaction_cost_context"]["source_system"]
        == "lotus-core"
    )
