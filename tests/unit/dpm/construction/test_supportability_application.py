from datetime import date
from decimal import Decimal
from typing import Any, cast

from src.api.request_models import RebalanceRequest
from src.api.services.construction_supportability_application import (
    apply_construction_supportability,
    supportability_diagnostics,
)
from src.core.construction.enrichment import summarize_enrichment_posture
from src.core.construction import build_rebalance_result_alternative
from src.core.construction.method_registry import resolve_method_plan
from src.core.construction.models import (
    AuthoritativeClientRestrictionContext,
    AuthoritativeClientRestrictionRule,
    AuthoritativeCurrencyOverlayContext,
    AuthoritativeLiquidityContext,
    AuthoritativeRegimeStressContext,
    AuthoritativeTransactionCostContext,
    AuthoritativeTransactionCostPoint,
    ConstructionAuthorityContext,
)
from src.core.construction.vocabulary import (
    ConstructionMethod,
    ConstructionMethodStatus,
    ConstructionTraceTerm,
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
    valid_api_payload,
)


def _request() -> RebalanceRequest:
    request = RebalanceRequest.model_validate(valid_api_payload())
    return request.model_copy(
        update={
            "shelf_entries": [
                *request.shelf_entries,
                shelf_entry("EQ_B", status="APPROVED", asset_class="EQUITY"),
            ]
        }
    )


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
        as_of_date=date(2026, 6, 1),
        window_start_date=date(2026, 5, 1),
        window_end_date=date(2026, 6, 1),
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
                first_observed_date=date(2026, 5, 1),
                last_observed_date=date(2026, 6, 1),
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
                first_observed_date=date(2026, 5, 1),
                last_observed_date=date(2026, 6, 1),
            ),
        ],
        reason_codes=["TRANSACTION_COST_CURVE_READY"],
    )


def _client_restriction_context() -> AuthoritativeClientRestrictionContext:
    return AuthoritativeClientRestrictionContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-core",
        portfolio_id="pf_supportability_application_1",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date=date(2026, 6, 1),
        restriction_count=1,
        restrictions=[
            AuthoritativeClientRestrictionRule(
                restriction_scope="instrument",
                restriction_code="NO_BUY_EQ_B",
                restriction_status="ACTIVE",
                restriction_source="CLIENT_PROFILE",
                applies_to_buy=True,
                applies_to_sell=False,
                instrument_ids=["EQ_B"],
                effective_from=date(2026, 1, 1),
                restriction_version=1,
            )
        ],
        reason_codes=["CLIENT_RESTRICTION_PROFILE_READY"],
    )


def _liquidity_context() -> AuthoritativeLiquidityContext:
    return AuthoritativeLiquidityContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-manage-settlement-engine",
        policy_id="liquidity-policy.v1",
        minimum_cash_weight=Decimal("0.99"),
        allowed_liquidity_tiers=["L1"],
        reason_codes=["LIQUIDITY_READY"],
    )


def _blocked_currency_context() -> AuthoritativeCurrencyOverlayContext:
    return AuthoritativeCurrencyOverlayContext(
        supportability_status=ConstructionMethodStatus.BLOCKED,
        source_system="lotus-core",
        policy_id="currency-overlay-policy.v1",
        hedge_ratio_min=Decimal("0.00"),
        hedge_ratio_max=Decimal("0.00"),
        eligible_currencies=["EUR"],
        reason_codes=["EXTERNAL_TREASURY_SOURCE_NOT_INGESTED"],
    )


def _blocked_regime_context() -> AuthoritativeRegimeStressContext:
    return AuthoritativeRegimeStressContext(
        supportability_status=ConstructionMethodStatus.BLOCKED,
        source_system="lotus-risk",
        scenario_pack_id="CIO_REGIME_2026_Q2",
        worst_case_loss_pct=Decimal("0.18"),
        maximum_allowed_loss_pct=Decimal("0.10"),
        reason_codes=["REGIME_SCENARIO_PACK_UNAVAILABLE"],
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


def test_supportability_diagnostics_preserves_existing_context_and_source_posture() -> None:
    result = _trade_result()
    alternative = build_rebalance_result_alternative(
        result=result,
        method=ConstructionMethod.COST_AWARE,
        alternative_id="alt_cost_aware",
    ).model_copy(update={"diagnostics": {"existing": "kept"}})
    authority_context = ConstructionAuthorityContext(
        transaction_cost_context=_transaction_cost_context()
    )
    enrichment = summarize_enrichment_posture(
        result=result,
        tax_required=False,
        risk_required=False,
        risk_context=None,
        performance_context=None,
        performance_required=False,
        transaction_cost_context=authority_context.transaction_cost_context,
        liquidity_context=None,
    )

    diagnostics = supportability_diagnostics(
        method=ConstructionMethod.COST_AWARE,
        alternative=alternative,
        plan=resolve_method_plan(ConstructionMethod.COST_AWARE, solver_available=True),
        enrichment=enrichment,
        method_reason_codes=["TRANSACTION_COST_CURVE_APPLIED_TO_CANDIDATE_NOTIONALS"],
        authority_context=authority_context,
    )

    assert diagnostics["existing"] == "kept"
    method_plan = cast(dict[str, Any], diagnostics["method_plan"])
    enrichment_summary = cast(dict[str, Any], diagnostics["enrichment_summary"])
    authority_diagnostics = cast(dict[str, Any], diagnostics["authority_context"])
    transaction_cost_diagnostics = cast(
        dict[str, Any],
        authority_diagnostics["transaction_cost_context"],
    )
    source_posture = cast(dict[str, Any], diagnostics["source_analytics_posture"])

    assert method_plan["requested_method"] == "COST_AWARE"
    assert (
        "TRANSACTION_COST_CURVE_APPLIED_TO_CANDIDATE_NOTIONALS"
        in enrichment_summary["reason_codes"]
    )
    assert transaction_cost_diagnostics["source_system"] == "lotus-core"
    assert source_posture["product_family"] == ("CONSTRUCTION_ALTERNATIVE_RISK_PERFORMANCE_CONTEXT")
    assert source_posture["risk_context_supplied"] is False


def test_supportability_application_applies_esg_restriction_constraints() -> None:
    result = _trade_result()
    enriched = apply_construction_supportability(
        request=_request(),
        method=ConstructionMethod.ESG_AWARE,
        alternative=build_rebalance_result_alternative(
            result=result,
            method=ConstructionMethod.ESG_AWARE,
            alternative_id="alt_esg_aware",
        ),
        result=result,
        plan=resolve_method_plan(ConstructionMethod.ESG_AWARE, solver_available=True),
        authority_context=ConstructionAuthorityContext(
            client_restriction_context=_client_restriction_context()
        ),
    )

    assert enriched.method_status == ConstructionMethodStatus.BLOCKED
    assert any(
        trace.constraint == ConstructionTraceTerm.CLIENT_RESTRICTION
        and trace.status == ConstructionMethodStatus.BLOCKED
        for trace in enriched.constraint_trace
    )
    reason_codes = enriched.diagnostics["enrichment_summary"]["reason_codes"]
    assert "CLIENT_RESTRICTION_VIOLATION_NO_BUY_EQ_B" in reason_codes


def test_supportability_application_applies_liquidity_status_overlay() -> None:
    result = _trade_result()
    enriched = apply_construction_supportability(
        request=_request(),
        method=ConstructionMethod.LIQUIDITY_AWARE,
        alternative=build_rebalance_result_alternative(
            result=result,
            method=ConstructionMethod.LIQUIDITY_AWARE,
            alternative_id="alt_liquidity_aware",
        ),
        result=result,
        plan=resolve_method_plan(ConstructionMethod.LIQUIDITY_AWARE, solver_available=True),
        authority_context=ConstructionAuthorityContext(liquidity_context=_liquidity_context()),
    )

    assert enriched.method_status == ConstructionMethodStatus.PENDING_REVIEW
    reason_codes = enriched.diagnostics["enrichment_summary"]["reason_codes"]
    assert "SETTLEMENT_AWARENESS_ENABLED" in reason_codes
    assert "LIQUIDITY_READY" in reason_codes
    assert (
        enriched.diagnostics["authority_context"]["liquidity_context"]["policy_id"]
        == "liquidity-policy.v1"
    )


def test_supportability_application_applies_currency_context_status_overlay() -> None:
    result = _trade_result()
    enriched = apply_construction_supportability(
        request=_request(),
        method=ConstructionMethod.CURRENCY_OVERLAY,
        alternative=build_rebalance_result_alternative(
            result=result,
            method=ConstructionMethod.CURRENCY_OVERLAY,
            alternative_id="alt_currency_overlay",
        ),
        result=result,
        plan=resolve_method_plan(ConstructionMethod.CURRENCY_OVERLAY, solver_available=True),
        authority_context=ConstructionAuthorityContext(
            currency_overlay_context=_blocked_currency_context()
        ),
    )

    assert enriched.method_status == ConstructionMethodStatus.BLOCKED
    reason_codes = enriched.diagnostics["enrichment_summary"]["reason_codes"]
    assert "CURRENCY_OVERLAY_CONTEXT_BLOCKED" in reason_codes
    assert "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED" in reason_codes
    assert (
        enriched.diagnostics["authority_context"]["currency_overlay_context"]["policy_id"]
        == "currency-overlay-policy.v1"
    )


def test_supportability_application_applies_regime_context_status_overlay() -> None:
    result = _trade_result()
    enriched = apply_construction_supportability(
        request=_request(),
        method=ConstructionMethod.REGIME_STRESS_AWARE,
        alternative=build_rebalance_result_alternative(
            result=result,
            method=ConstructionMethod.REGIME_STRESS_AWARE,
            alternative_id="alt_regime_stress_aware",
        ),
        result=result,
        plan=resolve_method_plan(ConstructionMethod.REGIME_STRESS_AWARE, solver_available=True),
        authority_context=ConstructionAuthorityContext(
            regime_stress_context=_blocked_regime_context()
        ),
    )

    assert enriched.method_status == ConstructionMethodStatus.BLOCKED
    reason_codes = enriched.diagnostics["enrichment_summary"]["reason_codes"]
    assert "REGIME_SCENARIO_PACK_UNAVAILABLE" in reason_codes
    assert (
        enriched.diagnostics["authority_context"]["regime_stress_context"]["scenario_pack_id"]
        == "CIO_REGIME_2026_Q2"
    )
