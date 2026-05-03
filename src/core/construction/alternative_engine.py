"""Pure helpers for constructing RFC-0039 alternatives from rebalance outputs."""

from decimal import Decimal

from src.core.construction.models import (
    ConstructionAlternative,
    ConstructionAlternativeSet,
    ConstructionComparisonMetrics,
    ConstructionConstraintTrace,
    ConstructionObjectiveTerm,
)
from src.core.construction.vocabulary import (
    ConstructionMethod,
    ConstructionMethodStatus,
    ConstructionSourceFamily,
    ConstructionTraceTerm,
)
from src.core.models import RebalanceResult, SecurityTradeIntent

_RATIO_QUANT = Decimal("0.0001")


def build_do_nothing_baseline(
    *,
    result: RebalanceResult,
    alternative_id: str = "alt_do_nothing_baseline",
) -> ConstructionAlternative:
    """Build the governed no-action comparator from a rebalance result context."""

    metrics = _comparison_metrics(result=result, use_after_state=False)
    return ConstructionAlternative(
        alternative_id=alternative_id,
        method=ConstructionMethod.DO_NOTHING_BASELINE,
        method_status=_method_status_from_run_status(result.status),
        summary="No-action baseline keeps current holdings unchanged for comparison.",
        rebalance_run_id=result.rebalance_run_id,
        objective_trace=_objective_trace(metrics),
        constraint_trace=_constraint_trace(result),
        comparison_metrics=metrics,
        intent_ids=[],
        diagnostics=_diagnostic_summary(result),
    )


def build_rebalance_result_alternative(
    *,
    result: RebalanceResult,
    method: ConstructionMethod = ConstructionMethod.HEURISTIC_EXPLAINABLE,
    alternative_id: str = "alt_heuristic_explainable",
) -> ConstructionAlternative:
    """Wrap an existing rebalance result as a construction alternative."""

    metrics = _comparison_metrics(result=result, use_after_state=True)
    return ConstructionAlternative(
        alternative_id=alternative_id,
        method=method,
        method_status=_method_status_from_run_status(result.status),
        summary=f"{method.value} alternative generated from rebalance simulation output.",
        rebalance_run_id=result.rebalance_run_id,
        objective_trace=_objective_trace(metrics),
        constraint_trace=_constraint_trace(result),
        comparison_metrics=metrics,
        intent_ids=[intent.intent_id for intent in result.intents],
        diagnostics=_diagnostic_summary(result),
    )


def build_alternative_set(
    *,
    alternative_set_id: str,
    portfolio_id: str,
    as_of: str,
    alternatives: list[ConstructionAlternative],
) -> ConstructionAlternativeSet:
    """Create an aggregate alternative set with conservative status roll-up."""

    status_order = {
        ConstructionMethodStatus.BLOCKED: 0,
        ConstructionMethodStatus.DEGRADED: 1,
        ConstructionMethodStatus.PENDING_REVIEW: 2,
        ConstructionMethodStatus.READY: 3,
    }
    aggregate_status = min(
        (alternative.method_status for alternative in alternatives),
        key=lambda status: status_order[status],
        default=ConstructionMethodStatus.BLOCKED,
    )
    return ConstructionAlternativeSet(
        alternative_set_id=alternative_set_id,
        portfolio_id=portfolio_id,
        as_of=as_of,
        status=aggregate_status,
        alternatives=alternatives,
    )


def _comparison_metrics(
    *,
    result: RebalanceResult,
    use_after_state: bool,
) -> ConstructionComparisonMetrics:
    drift_before = _active_weight_drift(
        actual_weights=_state_weight_map(result.before),
        model_weights=_model_weight_map(result),
    )
    after_state = result.after_simulated if use_after_state else result.before
    drift_after = _active_weight_drift(
        actual_weights=_state_weight_map(after_state),
        model_weights=_model_weight_map(result),
    )
    turnover_weight = _turnover_weight(result)
    return ConstructionComparisonMetrics(
        drift_before=drift_before,
        drift_after=drift_after,
        drift_reduction=(drift_before - drift_after).quantize(_RATIO_QUANT),
        turnover_weight=turnover_weight if use_after_state else Decimal("0.0000"),
        trade_count=_security_trade_count(result) if use_after_state else 0,
        estimated_transaction_cost=None,
    )


def _objective_trace(
    metrics: ConstructionComparisonMetrics,
) -> list[ConstructionObjectiveTerm]:
    return [
        ConstructionObjectiveTerm(
            term=ConstructionTraceTerm.DRIFT,
            value=metrics.drift_after,
            unit="absolute_active_weight",
            direction="lower_is_better",
            description="Absolute model drift after applying the alternative.",
        ),
        ConstructionObjectiveTerm(
            term=ConstructionTraceTerm.TURNOVER,
            value=metrics.turnover_weight,
            unit="portfolio_weight",
            direction="lower_is_better",
            description="Security-trade turnover needed by the alternative.",
        ),
    ]


def _constraint_trace(result: RebalanceResult) -> list[ConstructionConstraintTrace]:
    traces = [
        ConstructionConstraintTrace(
            constraint=ConstructionTraceTerm.SOURCE_SUPPORTABILITY,
            status=_method_status_from_run_status(result.status),
            source_family=ConstructionSourceFamily.PORTFOLIO_STATE,
            reason_codes=list(result.diagnostics.warnings),
            description="Source and diagnostic posture carried from the rebalance run.",
        ),
        ConstructionConstraintTrace(
            constraint=ConstructionTraceTerm.ELIGIBILITY,
            status=_method_status_from_run_status(result.status),
            source_family=ConstructionSourceFamily.INSTRUMENT_ELIGIBILITY,
            reason_codes=[excluded.reason_code for excluded in result.universe.excluded],
            description="Eligibility exclusions from the execution universe.",
        ),
    ]
    if result.tax_impact is not None or result.diagnostics.tax_budget_constraint_events:
        traces.append(
            ConstructionConstraintTrace(
                constraint=ConstructionTraceTerm.TAX_BUDGET,
                status=_method_status_from_run_status(result.status),
                source_family=ConstructionSourceFamily.TAX_LOTS,
                reason_codes=[
                    event.reason_code
                    for event in result.diagnostics.tax_budget_constraint_events
                ],
                description="Tax budget and lot-selection posture from tax-aware execution.",
            )
        )
    if result.diagnostics.dropped_intents:
        traces.append(
            ConstructionConstraintTrace(
                constraint=ConstructionTraceTerm.TURNOVER_BUDGET,
                status=ConstructionMethodStatus.PENDING_REVIEW,
                source_family=ConstructionSourceFamily.MANDATE_BINDING,
                reason_codes=[entry.reason for entry in result.diagnostics.dropped_intents],
                description="Turnover budget dropped one or more proposed intents.",
            )
        )
    return traces


def _state_weight_map(state: object) -> dict[str, Decimal]:
    allocations = getattr(state, "allocation_by_instrument", [])
    return {allocation.key: allocation.weight for allocation in allocations}


def _model_weight_map(result: RebalanceResult) -> dict[str, Decimal]:
    return {target.instrument_id: target.model_weight for target in result.target.targets}


def _active_weight_drift(
    *,
    actual_weights: dict[str, Decimal],
    model_weights: dict[str, Decimal],
) -> Decimal:
    instrument_ids = set(actual_weights) | set(model_weights)
    drift = sum(
        (
            abs(
                actual_weights.get(instrument_id, Decimal("0"))
                - model_weights.get(instrument_id, Decimal("0"))
            )
            for instrument_id in instrument_ids
        ),
        Decimal("0"),
    )
    return drift.quantize(_RATIO_QUANT)


def _turnover_weight(result: RebalanceResult) -> Decimal:
    portfolio_value = result.before.total_value.amount
    if portfolio_value <= Decimal("0"):
        return Decimal("0.0000")
    turnover = sum(
        abs(intent.notional_base.amount)
        for intent in result.intents
        if isinstance(intent, SecurityTradeIntent) and intent.notional_base is not None
    )
    return (turnover / portfolio_value).quantize(_RATIO_QUANT)


def _security_trade_count(result: RebalanceResult) -> int:
    return sum(1 for intent in result.intents if isinstance(intent, SecurityTradeIntent))


def _method_status_from_run_status(status: str) -> ConstructionMethodStatus:
    if status == "READY":
        return ConstructionMethodStatus.READY
    if status == "PENDING_REVIEW":
        return ConstructionMethodStatus.PENDING_REVIEW
    return ConstructionMethodStatus.BLOCKED


def _diagnostic_summary(result: RebalanceResult) -> dict[str, object]:
    return {
        "warnings": list(result.diagnostics.warnings),
        "data_quality": {
            key: list(values) for key, values in result.diagnostics.data_quality.items()
        },
        "rule_result_count": len(result.rule_results),
    }
