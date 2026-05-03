"""Pure construction enrichment helpers for RFC-0039 alternatives."""

from decimal import Decimal
from typing import cast

from src.core.construction.models import (
    AuthoritativePerformanceContext,
    AuthoritativeRiskContext,
    ConstructionEnrichmentSummary,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.models import Money, RebalanceResult, SecurityTradeIntent

_RATIO_QUANT = Decimal("0.0001")


def estimate_transaction_cost(
    *,
    result: RebalanceResult,
    basis_points: Decimal,
) -> Money:
    """Estimate local construction cost from security-trade notional.

    This is deliberately labelled an estimate. It is not an authoritative execution cost curve.
    """

    notional = sum(
        (
            abs(intent.notional_base.amount)
            for intent in result.intents
            if isinstance(intent, SecurityTradeIntent) and intent.notional_base is not None
        ),
        Decimal("0"),
    )
    cost = (notional * basis_points / Decimal("10000")).quantize(Decimal("0.01"))
    return Money(amount=cost, currency=result.before.total_value.currency)


def summarize_enrichment_posture(
    *,
    result: RebalanceResult,
    tax_required: bool,
    authoritative_cost_available: bool = False,
    risk_context: AuthoritativeRiskContext | None = None,
    performance_context: AuthoritativePerformanceContext | None = None,
) -> ConstructionEnrichmentSummary:
    """Summarize source-aware enrichment readiness without hiding degraded inputs."""

    reason_codes: list[str] = []
    tax_status = ConstructionMethodStatus.READY
    if tax_required and result.tax_impact is None:
        tax_status = ConstructionMethodStatus.BLOCKED
        reason_codes.append("TAX_LOTS_REQUIRED_BUT_NO_TAX_IMPACT")
    elif result.tax_impact is None:
        tax_status = ConstructionMethodStatus.DEGRADED
        reason_codes.append("TAX_ENRICHMENT_NOT_REQUESTED_OR_UNAVAILABLE")

    fx_status = ConstructionMethodStatus.READY
    if result.diagnostics.missing_fx_pairs:
        fx_status = ConstructionMethodStatus.BLOCKED
        reason_codes.append("FX_SOURCE_MISSING")

    liquidity_status = ConstructionMethodStatus.READY
    if _cash_weight(result.after_simulated) is None:
        liquidity_status = ConstructionMethodStatus.DEGRADED
        reason_codes.append("CASH_WEIGHT_UNAVAILABLE")

    cost_status = ConstructionMethodStatus.READY
    if not authoritative_cost_available:
        cost_status = ConstructionMethodStatus.DEGRADED
        reason_codes.append("AUTHORITATIVE_TRANSACTION_COST_UNAVAILABLE")

    turnover_status = ConstructionMethodStatus.READY
    if result.diagnostics.dropped_intents:
        turnover_status = ConstructionMethodStatus.PENDING_REVIEW
        reason_codes.append("TURNOVER_BUDGET_DROPPED_INTENTS")

    risk_status = _authoritative_context_status(
        context_status=risk_context.supportability_status if risk_context else None,
        missing_reason="RISK_ENRICHMENT_UNAVAILABLE",
        context_reason_codes=risk_context.reason_codes if risk_context else [],
        reason_codes=reason_codes,
    )
    performance_status = _authoritative_context_status(
        context_status=(
            performance_context.supportability_status if performance_context else None
        ),
        missing_reason="PERFORMANCE_CONTEXT_UNAVAILABLE",
        context_reason_codes=performance_context.reason_codes if performance_context else [],
        reason_codes=reason_codes,
    )

    return ConstructionEnrichmentSummary(
        tax_status=tax_status,
        turnover_status=turnover_status,
        liquidity_status=liquidity_status,
        cost_status=cost_status,
        fx_status=fx_status,
        risk_status=risk_status,
        performance_status=performance_status,
        reason_codes=sorted(set(reason_codes)),
    )


def _authoritative_context_status(
    *,
    context_status: ConstructionMethodStatus | None,
    missing_reason: str,
    context_reason_codes: list[str],
    reason_codes: list[str],
) -> ConstructionMethodStatus:
    if context_status is None:
        reason_codes.append(missing_reason)
        return ConstructionMethodStatus.DEGRADED
    reason_codes.extend(context_reason_codes)
    return context_status


def _cash_weight(state: object) -> Decimal | None:
    allocation_by_asset_class = getattr(state, "allocation_by_asset_class", [])
    for allocation in allocation_by_asset_class:
        if allocation.key == "CASH":
            return cast(Decimal, allocation.weight.quantize(_RATIO_QUANT))
    return None
