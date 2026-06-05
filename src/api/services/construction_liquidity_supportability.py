from decimal import Decimal

from src.core.construction.models import (
    AuthoritativeLiquidityCashflowProjection,
    AuthoritativeLiquidityContext,
)
from src.core.construction.status import lowest_construction_status
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.models import RebalanceResult


def liquidity_status(
    *,
    result: RebalanceResult,
    context: AuthoritativeLiquidityContext | None,
) -> ConstructionMethodStatus:
    if context is None:
        return ConstructionMethodStatus.DEGRADED
    status = context.supportability_status
    if result.diagnostics.cash_ladder_breaches or result.diagnostics.insufficient_cash:
        return ConstructionMethodStatus.BLOCKED
    cash_weight = post_trade_cash_weight(result=result)
    if cash_weight is not None and cash_weight < context.minimum_cash_weight:
        status = lowest_construction_status([status, ConstructionMethodStatus.PENDING_REVIEW])
    cashflow_status = cashflow_projection_status(
        result=result,
        context=context,
        cash_weight=cash_weight,
    )
    if cashflow_status is None:
        return status
    return lowest_construction_status([status, cashflow_status])


def cashflow_projection_status(
    *,
    result: RebalanceResult,
    context: AuthoritativeLiquidityContext,
    cash_weight: Decimal | None,
) -> ConstructionMethodStatus | None:
    if context.cashflow_projection is None:
        return None
    cashflow_status = context.cashflow_projection.data_quality_status
    if not context.cashflow_projection.include_projected:
        cashflow_status = lowest_construction_status(
            [cashflow_status, ConstructionMethodStatus.DEGRADED]
        )
    if (
        context.cashflow_projection.total_net_cashflow.currency
        != result.after_simulated.total_value.currency
    ):
        cashflow_status = lowest_construction_status(
            [cashflow_status, ConstructionMethodStatus.DEGRADED]
        )
    elif result.after_simulated.total_value.amount <= Decimal("0"):
        cashflow_status = lowest_construction_status(
            [cashflow_status, ConstructionMethodStatus.DEGRADED]
        )
    elif cash_weight is not None:
        projected_cash_weight = projected_cashflow_weight(result=result, context=context)
        if projected_cash_weight is None:
            return cashflow_status
        if cash_weight + projected_cash_weight < context.minimum_cash_weight:
            cashflow_status = lowest_construction_status(
                [cashflow_status, ConstructionMethodStatus.PENDING_REVIEW]
            )
    return cashflow_status


def liquidity_reason_codes(
    *,
    result: RebalanceResult,
    context: AuthoritativeLiquidityContext | None,
) -> list[str]:
    reason_codes: list[str] = []
    if context is None:
        reason_codes.append("LIQUIDITY_POLICY_CONTEXT_DERIVED")
    else:
        reason_codes.extend(context.reason_codes)
        reason_codes.extend(cashflow_projection_reason_codes(result=result, context=context))
    if result.diagnostics.cash_ladder:
        reason_codes.append("SETTLEMENT_CASH_LADDER_PRESENT")
    if result.diagnostics.cash_ladder_breaches:
        reason_codes.append("SETTLEMENT_CASH_LADDER_BREACH")
    if result.diagnostics.insufficient_cash:
        reason_codes.append("LIQUIDITY_FUNDING_DEFICIT")
    return reason_codes


def cashflow_projection_reason_codes(
    *,
    result: RebalanceResult,
    context: AuthoritativeLiquidityContext,
) -> list[str]:
    projection = context.cashflow_projection
    if projection is None:
        return []
    reason_codes = ["CASHFLOW_PROJECTION_CONTEXT_PRESENT", *projection.reason_codes]
    reason_codes.extend(_cashflow_projection_usability_reason_codes(projection))
    if _cashflow_projection_currency_mismatch(result=result, projection=projection):
        reason_codes.append("CASHFLOW_PROJECTION_CURRENCY_MISMATCH")
        return reason_codes
    if _post_trade_total_value_unavailable(result=result):
        reason_codes.append("CASHFLOW_PROJECTION_TOTAL_VALUE_UNAVAILABLE")
        return reason_codes
    cash_weight = post_trade_cash_weight(result=result)
    if cash_weight is None:
        return reason_codes
    projected_cash_weight = projected_cashflow_weight(result=result, context=context)
    if projected_cash_weight is None:
        return reason_codes
    if cash_weight + projected_cash_weight < context.minimum_cash_weight:
        reason_codes.append("CASHFLOW_PROJECTION_ADJUSTED_CASH_BELOW_POLICY")
    elif _cashflow_projection_is_usable(projection):
        reason_codes.append("CASHFLOW_PROJECTION_READY")
    return reason_codes


def _cashflow_projection_usability_reason_codes(
    projection: AuthoritativeLiquidityCashflowProjection,
) -> list[str]:
    reason_codes: list[str] = []
    if projection.data_quality_status != ConstructionMethodStatus.READY:
        reason_codes.append(f"CASHFLOW_PROJECTION_{projection.data_quality_status}_BY_SOURCE")
    if not projection.include_projected:
        reason_codes.append("CASHFLOW_PROJECTION_PROJECTED_ROWS_NOT_INCLUDED")
    return reason_codes


def _cashflow_projection_is_usable(
    projection: AuthoritativeLiquidityCashflowProjection,
) -> bool:
    return (
        projection.data_quality_status == ConstructionMethodStatus.READY
        and projection.include_projected
    )


def _cashflow_projection_currency_mismatch(
    *,
    result: RebalanceResult,
    projection: AuthoritativeLiquidityCashflowProjection,
) -> bool:
    return projection.total_net_cashflow.currency != result.after_simulated.total_value.currency


def _post_trade_total_value_unavailable(*, result: RebalanceResult) -> bool:
    return result.after_simulated.total_value.amount <= Decimal("0")


def projected_cashflow_weight(
    *,
    result: RebalanceResult,
    context: AuthoritativeLiquidityContext,
) -> Decimal | None:
    projection = context.cashflow_projection
    if projection is None:
        return None
    total_value = result.after_simulated.total_value
    if projection.total_net_cashflow.currency != total_value.currency:
        return None
    if total_value.amount <= Decimal("0"):
        return None
    return projection.total_net_cashflow.amount / total_value.amount


def post_trade_cash_weight(*, result: RebalanceResult) -> Decimal | None:
    return next(
        (
            allocation.weight
            for allocation in result.after_simulated.allocation_by_asset_class
            if allocation.key == "CASH"
        ),
        None,
    )


def derive_liquidity_context(*, result: RebalanceResult) -> AuthoritativeLiquidityContext:
    return AuthoritativeLiquidityContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-manage-settlement-engine",
        policy_id="manage-liquidity-policy.v1",
        minimum_cash_weight=Decimal("0.03"),
        allowed_liquidity_tiers=["L1", "L2", "L3"],
        reason_codes=["LIQUIDITY_POLICY_DERIVED_FROM_MANAGE_SETTLEMENT_RULES"],
    )


__all__ = [
    "cashflow_projection_reason_codes",
    "cashflow_projection_status",
    "derive_liquidity_context",
    "liquidity_reason_codes",
    "liquidity_status",
    "post_trade_cash_weight",
    "projected_cashflow_weight",
]
