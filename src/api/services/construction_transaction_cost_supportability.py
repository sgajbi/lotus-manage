from decimal import Decimal

from src.core.construction.models import (
    AuthoritativeTransactionCostContext,
    AuthoritativeTransactionCostPoint,
    ConstructionAlternative,
    ConstructionConstraintTrace,
    ConstructionObjectiveTerm,
)
from src.core.construction.status import lowest_construction_status
from src.core.construction.vocabulary import (
    ConstructionMethodStatus,
    ConstructionSourceFamily,
    ConstructionTraceTerm,
)
from src.core.models import Money, RebalanceResult, SecurityTradeIntent

_MONEY_QUANT = Decimal("0.0001")


def with_observed_transaction_cost_estimate(
    *,
    alternative: ConstructionAlternative,
    result: RebalanceResult,
    context: AuthoritativeTransactionCostContext | None,
) -> ConstructionAlternative:
    estimate = observed_transaction_cost_estimate(result=result, context=context)
    if estimate is None:
        return alternative
    metrics = alternative.comparison_metrics.model_copy(
        update={"estimated_transaction_cost": estimate}
    )
    objective_trace = [
        *alternative.objective_trace,
        ConstructionObjectiveTerm(
            term=ConstructionTraceTerm.ESTIMATED_COST,
            value=estimate.amount,
            unit=estimate.currency,
            direction="lower_is_better",
            description=(
                "Source-observed transaction-cost bps applied to candidate trade notionals; "
                "not a predictive execution quote."
            ),
        ),
    ]
    constraint_trace = [
        *alternative.constraint_trace,
        ConstructionConstraintTrace(
            constraint=ConstructionTraceTerm.ESTIMATED_COST,
            status=transaction_cost_status(result=result, context=context),
            source_family=ConstructionSourceFamily.TRANSACTION_COST,
            reason_codes=transaction_cost_reason_codes(result=result, context=context),
            description=(
                "Observed TransactionCostCurve:v1 evidence supports cost-aware comparison only."
            ),
        ),
    ]
    return alternative.model_copy(
        update={
            "comparison_metrics": metrics,
            "objective_trace": objective_trace,
            "constraint_trace": constraint_trace,
        }
    )


def observed_transaction_cost_estimate(
    *,
    result: RebalanceResult,
    context: AuthoritativeTransactionCostContext | None,
) -> Money | None:
    if context is None or context.supportability_status != ConstructionMethodStatus.READY:
        return None
    point_by_key = transaction_cost_curve_points_by_key(context=context)
    cost_terms = _observed_transaction_cost_terms(result=result, point_by_key=point_by_key)
    return _observed_transaction_cost_money(
        cost_terms=cost_terms,
        currency=result.before.total_value.currency,
    )


def _observed_transaction_cost_terms(
    *,
    result: RebalanceResult,
    point_by_key: dict[tuple[str, str], AuthoritativeTransactionCostPoint],
) -> list[Decimal]:
    cost_terms: list[Decimal] = []
    for intent in result.intents:
        term = _observed_transaction_cost_term(intent=intent, point_by_key=point_by_key)
        if term is not None:
            cost_terms.append(term)
    return cost_terms


def _observed_transaction_cost_term(
    *,
    intent: object,
    point_by_key: dict[tuple[str, str], AuthoritativeTransactionCostPoint],
) -> Decimal | None:
    if not isinstance(intent, SecurityTradeIntent) or intent.notional_base is None:
        return None
    point = point_by_key.get((intent.instrument_id, intent.side))
    if point is None:
        return None
    return abs(intent.notional_base.amount) * point.average_cost_bps / Decimal("10000")


def _observed_transaction_cost_money(
    *,
    cost_terms: list[Decimal],
    currency: str,
) -> Money | None:
    if not cost_terms:
        return None
    total = sum(cost_terms, Decimal("0"))
    return Money(amount=total.quantize(_MONEY_QUANT), currency=currency)


def transaction_cost_status(
    *,
    result: RebalanceResult,
    context: AuthoritativeTransactionCostContext | None,
) -> ConstructionMethodStatus:
    if context is None:
        return ConstructionMethodStatus.DEGRADED
    status = context.supportability_status
    traded_security_ids = traded_transaction_cost_security_ids(result=result)
    covered_security_ids = covered_transaction_cost_security_ids(context=context)
    if traded_security_ids and not traded_security_ids <= covered_security_ids:
        status = lowest_construction_status([status, ConstructionMethodStatus.DEGRADED])
    if observed_transaction_cost_estimate(result=result, context=context) is None:
        status = lowest_construction_status([status, ConstructionMethodStatus.DEGRADED])
    return status


def transaction_cost_reason_codes(
    *,
    result: RebalanceResult,
    context: AuthoritativeTransactionCostContext | None,
) -> list[str]:
    if context is None:
        return ["TRANSACTION_COST_CURVE_UNAVAILABLE"]
    reason_codes = list(context.reason_codes)
    traded_security_ids = traded_transaction_cost_security_ids(result=result)
    covered_security_ids = covered_transaction_cost_security_ids(context=context)
    missing_security_ids = sorted(traded_security_ids - covered_security_ids)
    if missing_security_ids:
        reason_codes.append("TRANSACTION_COST_CURVE_MISSING_TRADED_SECURITIES")
    if observed_transaction_cost_estimate(result=result, context=context) is None:
        reason_codes.append("TRANSACTION_COST_ESTIMATE_UNAVAILABLE")
    else:
        reason_codes.append("TRANSACTION_COST_CURVE_APPLIED_TO_CANDIDATE_NOTIONALS")
    return sorted(set(reason_codes))


def traded_transaction_cost_security_ids(*, result: RebalanceResult) -> set[str]:
    return {
        intent.instrument_id for intent in result.intents if isinstance(intent, SecurityTradeIntent)
    }


def covered_transaction_cost_security_ids(
    *,
    context: AuthoritativeTransactionCostContext,
) -> set[str]:
    return {point.security_id for point in context.curve_points}


def transaction_cost_curve_points_by_key(
    *,
    context: AuthoritativeTransactionCostContext,
) -> dict[tuple[str, str], AuthoritativeTransactionCostPoint]:
    return {(point.security_id, point.transaction_type): point for point in context.curve_points}


__all__ = [
    "covered_transaction_cost_security_ids",
    "observed_transaction_cost_estimate",
    "transaction_cost_curve_points_by_key",
    "transaction_cost_reason_codes",
    "transaction_cost_status",
    "traded_transaction_cost_security_ids",
    "with_observed_transaction_cost_estimate",
]
