from decimal import Decimal

import pytest

from src.api.request_models import RebalanceRequest
import src.api.services.construction_service as construction_service
from src.core.construction import (
    AuthoritativeCurrencyOverlayContext,
    AuthoritativeLiquidityCashflowProjection,
    AuthoritativeLiquidityContext,
    AuthoritativePerformanceContext,
    AuthoritativeRiskContext,
    ConstructionAuthorityContext,
    ConstructionMethodStatus,
    estimate_transaction_cost,
    summarize_enrichment_posture,
)
from src.core.construction.repository import (
    ConstructionAlternativeSetNotFoundError,
    ConstructionIdempotencyConflictError,
)
from src.core.construction.vocabulary import ConstructionMethod
from src.core.models import EngineOptions, RebalanceResult
from src.core.rebalance.engine import run_simulation
from src.infrastructure.construction import InMemoryConstructionRepository
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


def test_construction_service_error_mapping_and_missing_set() -> None:
    with pytest.raises(ConstructionAlternativeSetNotFoundError):
        construction_service.get_construction_alternative_set(
            repository=InMemoryConstructionRepository(),
            alternative_set_id="missing",
        )

    conflict = construction_service.to_api_http_exception(
        ConstructionIdempotencyConflictError("CONSTRUCTION_IDEMPOTENCY_KEY_CONFLICT")
    )
    missing = construction_service.to_api_http_exception(
        ConstructionAlternativeSetNotFoundError("CONSTRUCTION_ALTERNATIVE_SET_NOT_FOUND")
    )
    unknown = construction_service.to_api_http_exception(RuntimeError("boom"))

    assert conflict.status_code == 409
    assert missing.status_code == 404
    assert unknown.status_code == 500
    assert unknown.detail == "RuntimeError"


def test_construction_service_supportability_helper_edges() -> None:
    result = _trade_result(max_turnover_pct=Decimal("0.01"))
    no_context = construction_service._authority_context_for_method(
        method=ConstructionMethod.LIQUIDITY_AWARE,
        result=result,
        authority_context=ConstructionAuthorityContext(),
        risk_authority_client=None,
        correlation_id="corr-helper",
    )
    risk_unavailable = construction_service._authority_context_for_method(
        method=ConstructionMethod.RISK_AWARE,
        result=result,
        authority_context=ConstructionAuthorityContext(),
        risk_authority_client=_UnavailableRiskClient(),
        correlation_id="corr-helper",
    )
    liquidity_context = AuthoritativeLiquidityContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-manage-settlement-engine",
        policy_id="liquidity-policy.v1",
        minimum_cash_weight=Decimal("0.99"),
        allowed_liquidity_tiers=["L1"],
        reason_codes=["LIQUIDITY_READY"],
    )

    assert no_context.liquidity_context is not None
    assert risk_unavailable.risk_context is None
    assert (
        construction_service._solver_method_status(result=result) == ConstructionMethodStatus.READY
    )
    assert (
        construction_service._liquidity_status(result=result, context=None)
        == ConstructionMethodStatus.DEGRADED
    )
    assert (
        construction_service._liquidity_status(result=result, context=liquidity_context)
        == ConstructionMethodStatus.PENDING_REVIEW
    )
    assert "LIQUIDITY_POLICY_CONTEXT_DERIVED" in construction_service._liquidity_reason_codes(
        result=result,
        context=None,
    )


def test_cashflow_projection_context_marks_future_cash_pressure_pending() -> None:
    result = _trade_result()
    context = AuthoritativeLiquidityContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-manage-settlement-engine",
        policy_id="liquidity-policy.v1",
        minimum_cash_weight=Decimal("0.03"),
        allowed_liquidity_tiers=["L1"],
        cashflow_projection=AuthoritativeLiquidityCashflowProjection(
            source_product_name="PortfolioCashflowProjection",
            source_product_version="v1",
            source_system="lotus-core",
            total_net_cashflow={"amount": "-50.00", "currency": "USD"},
            projection_start="2026-05-03",
            projection_end="2026-06-03",
            include_projected=True,
            source_batch_fingerprint="cashflow-projection:pf_enrich_1:2026-05-03",
            reason_codes=["CORE_CASHFLOW_PROJECTION_READY"],
        ),
        reason_codes=["LIQUIDITY_POLICY_READY"],
    )

    status = construction_service._liquidity_status(result=result, context=context)
    reason_codes = construction_service._liquidity_reason_codes(
        result=result,
        context=context,
    )

    assert status == ConstructionMethodStatus.PENDING_REVIEW
    assert "CORE_CASHFLOW_PROJECTION_READY" in reason_codes
    assert "CASHFLOW_PROJECTION_ADJUSTED_CASH_BELOW_POLICY" in reason_codes


def test_cashflow_projection_context_rejects_unusable_projection_posture() -> None:
    result = _trade_result()
    context = AuthoritativeLiquidityContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-manage-settlement-engine",
        policy_id="liquidity-policy.v1",
        minimum_cash_weight=Decimal("0.03"),
        allowed_liquidity_tiers=["L1"],
        cashflow_projection=AuthoritativeLiquidityCashflowProjection(
            source_product_name="PortfolioCashflowProjection",
            source_product_version="v1",
            source_system="lotus-core",
            total_net_cashflow={"amount": "100.00", "currency": "SGD"},
            projection_start="2026-05-03",
            projection_end="2026-06-03",
            include_projected=False,
            data_quality_status=ConstructionMethodStatus.DEGRADED,
            reason_codes=["CORE_CASHFLOW_PROJECTION_STALE"],
        ),
        reason_codes=["LIQUIDITY_POLICY_READY"],
    )

    status = construction_service._liquidity_status(result=result, context=context)
    reason_codes = construction_service._liquidity_reason_codes(
        result=result,
        context=context,
    )

    assert status == ConstructionMethodStatus.DEGRADED
    assert "CASHFLOW_PROJECTION_CURRENCY_MISMATCH" in reason_codes
    assert "CASHFLOW_PROJECTION_PROJECTED_ROWS_NOT_INCLUDED" in reason_codes
    assert "CASHFLOW_PROJECTION_DEGRADED_BY_SOURCE" in reason_codes


def test_construction_service_currency_overlay_helper_edges() -> None:
    payload = valid_api_payload()
    payload["portfolio_snapshot"]["base_currency"] = "SGD"
    payload["market_data_snapshot"]["prices"][0]["currency"] = "USD"
    payload["market_data_snapshot"]["fx_rates"] = []
    request = RebalanceRequest.model_validate(payload)
    context = AuthoritativeCurrencyOverlayContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-manage-fx-policy",
        policy_id="currency-policy.v1",
        hedge_ratio_min=Decimal("0.00"),
        hedge_ratio_max=Decimal("1.00"),
        eligible_currencies=[],
        reason_codes=["CURRENCY_POLICY_READY"],
    )

    assert (
        construction_service._currency_overlay_status(request=request, context=context)
        == ConstructionMethodStatus.BLOCKED
    )
    payload["market_data_snapshot"]["fx_rates"] = [
        {"pair": "USD/SGD", "rate": "1.35", "as_of": "2026-05-03"}
    ]
    request = RebalanceRequest.model_validate(payload)

    assert (
        construction_service._currency_overlay_status(request=request, context=None)
        == ConstructionMethodStatus.DEGRADED
    )
    assert (
        construction_service._currency_overlay_status(request=request, context=context)
        == ConstructionMethodStatus.PENDING_REVIEW
    )


def test_construction_service_uses_method_specific_run_correlation_ids() -> None:
    class FakeRunService:
        def __init__(self) -> None:
            self.correlation_ids: list[str] = []

        def record_run(self, *, result, request_hash, portfolio_id, idempotency_key) -> None:
            self.correlation_ids.append(result.correlation_id)

    payload = valid_api_payload()
    request = RebalanceRequest.model_validate(payload)
    run_service = FakeRunService()

    construction_service.generate_construction_alternative_set(
        request=request,
        idempotency_key="construction-correlation-test",
        correlation_id="corr-construct-test",
        repository=InMemoryConstructionRepository(),
        methods=[
            ConstructionMethod.DO_NOTHING_BASELINE,
            ConstructionMethod.HEURISTIC_EXPLAINABLE,
            ConstructionMethod.MIN_TURNOVER,
        ],
        run_service=run_service,
    )

    assert run_service.correlation_ids == [
        "corr-construct-test:heuristic_explainable",
        "corr-construct-test:min_turnover",
    ]
    assert len(set(run_service.correlation_ids)) == len(run_service.correlation_ids)


class _UnavailableRiskClient:
    def concentration_context(self, *, result, correlation_id):
        raise construction_service.LotusRiskAuthorityUnavailableError("risk down")


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
