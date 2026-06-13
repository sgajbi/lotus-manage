from dataclasses import dataclass
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
    assessment = _cashflow_projection_policy_assessment(
        result=result,
        context=context,
        cash_weight=cash_weight,
        derive_cash_weight=False,
    )
    if assessment is None:
        return None
    return assessment.status


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
    assessment = _cashflow_projection_policy_assessment(
        result=result,
        context=context,
        cash_weight=None,
        derive_cash_weight=True,
    )
    assert assessment is not None
    reason_codes = ["CASHFLOW_PROJECTION_CONTEXT_PRESENT", *projection.reason_codes]
    reason_codes.extend(_cashflow_projection_usability_reason_codes(projection))
    blocking_reason = _cashflow_projection_blocking_reason_code(assessment)
    if blocking_reason is not None:
        reason_codes.append(blocking_reason)
        return reason_codes
    policy_reason = _cashflow_projection_policy_reason_code(
        assessment=assessment,
        projection=projection,
    )
    if policy_reason is not None:
        reason_codes.append(policy_reason)
    return reason_codes


@dataclass(frozen=True)
class _CashflowProjectionPolicyAssessment:
    status: ConstructionMethodStatus
    currency_mismatch: bool
    post_trade_total_value_unavailable: bool
    projected_cash_weight: Decimal | None
    adjusted_cash_below_policy: bool


@dataclass(frozen=True)
class _CashflowProjectionPolicyInputs:
    projection: AuthoritativeLiquidityCashflowProjection
    currency_mismatch: bool
    total_value_unavailable: bool
    effective_cash_weight: Decimal | None


def _cashflow_projection_policy_assessment(
    *,
    result: RebalanceResult,
    context: AuthoritativeLiquidityContext,
    cash_weight: Decimal | None,
    derive_cash_weight: bool,
) -> _CashflowProjectionPolicyAssessment | None:
    projection = context.cashflow_projection
    if projection is None:
        return None
    inputs = _cashflow_projection_policy_inputs(
        result=result,
        projection=projection,
        cash_weight=cash_weight,
        derive_cash_weight=derive_cash_weight,
    )
    projected_weight = _policy_projected_cashflow_weight(
        result=result,
        context=context,
        cash_weight=inputs.effective_cash_weight,
        currency_mismatch=inputs.currency_mismatch,
        total_value_unavailable=inputs.total_value_unavailable,
    )
    below_policy = _adjusted_cash_below_policy(
        cash_weight=inputs.effective_cash_weight,
        projected_cash_weight=projected_weight,
        minimum_cash_weight=context.minimum_cash_weight,
    )
    status = _cashflow_projection_assessed_status(
        projection=inputs.projection,
        currency_mismatch=inputs.currency_mismatch,
        total_value_unavailable=inputs.total_value_unavailable,
        below_policy=below_policy,
    )
    return _CashflowProjectionPolicyAssessment(
        status=status,
        currency_mismatch=inputs.currency_mismatch,
        post_trade_total_value_unavailable=inputs.total_value_unavailable,
        projected_cash_weight=projected_weight,
        adjusted_cash_below_policy=below_policy,
    )


def _cashflow_projection_policy_inputs(
    *,
    result: RebalanceResult,
    projection: AuthoritativeLiquidityCashflowProjection,
    cash_weight: Decimal | None,
    derive_cash_weight: bool,
) -> _CashflowProjectionPolicyInputs:
    currency_mismatch = _cashflow_projection_currency_mismatch(
        result=result,
        projection=projection,
    )
    total_value_unavailable = (
        False if currency_mismatch else _post_trade_total_value_unavailable(result=result)
    )
    effective_cash_weight = (
        post_trade_cash_weight(result=result)
        if derive_cash_weight and cash_weight is None
        else cash_weight
    )
    return _CashflowProjectionPolicyInputs(
        projection=projection,
        currency_mismatch=currency_mismatch,
        total_value_unavailable=total_value_unavailable,
        effective_cash_weight=effective_cash_weight,
    )


def _adjusted_cash_below_policy(
    *,
    cash_weight: Decimal | None,
    projected_cash_weight: Decimal | None,
    minimum_cash_weight: Decimal,
) -> bool:
    return (
        cash_weight is not None
        and projected_cash_weight is not None
        and cash_weight + projected_cash_weight < minimum_cash_weight
    )


def _cashflow_projection_blocking_reason_code(
    assessment: _CashflowProjectionPolicyAssessment,
) -> str | None:
    if assessment.currency_mismatch:
        return "CASHFLOW_PROJECTION_CURRENCY_MISMATCH"
    if assessment.post_trade_total_value_unavailable:
        return "CASHFLOW_PROJECTION_TOTAL_VALUE_UNAVAILABLE"
    return None


def _cashflow_projection_policy_reason_code(
    *,
    assessment: _CashflowProjectionPolicyAssessment,
    projection: AuthoritativeLiquidityCashflowProjection,
) -> str | None:
    if assessment.projected_cash_weight is None:
        return None
    if assessment.adjusted_cash_below_policy:
        return "CASHFLOW_PROJECTION_ADJUSTED_CASH_BELOW_POLICY"
    if _cashflow_projection_is_usable(projection):
        return "CASHFLOW_PROJECTION_READY"
    return None


def _cashflow_projection_assessed_status(
    *,
    projection: AuthoritativeLiquidityCashflowProjection,
    currency_mismatch: bool,
    total_value_unavailable: bool,
    below_policy: bool,
) -> ConstructionMethodStatus:
    status = projection.data_quality_status
    if not projection.include_projected or currency_mismatch or total_value_unavailable:
        status = lowest_construction_status([status, ConstructionMethodStatus.DEGRADED])
    if below_policy:
        status = lowest_construction_status([status, ConstructionMethodStatus.PENDING_REVIEW])
    return status


def _policy_projected_cashflow_weight(
    *,
    result: RebalanceResult,
    context: AuthoritativeLiquidityContext,
    cash_weight: Decimal | None,
    currency_mismatch: bool,
    total_value_unavailable: bool,
) -> Decimal | None:
    if cash_weight is None or currency_mismatch or total_value_unavailable:
        return None
    return projected_cashflow_weight(result=result, context=context)


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
