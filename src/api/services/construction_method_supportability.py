from src.api.services.construction_currency_overlay_supportability import (
    currency_overlay_status,
    derive_currency_overlay_context,
    missing_currency_overlay_pairs,
)
from src.api.services.construction_liquidity_supportability import (
    cashflow_projection_reason_codes,
    derive_liquidity_context,
    liquidity_reason_codes,
    liquidity_status,
    post_trade_cash_weight,
)
from src.core.construction.models import AuthoritativeRegimeStressContext
from src.core.construction.vocabulary import ConstructionMethodStatus


def regime_stress_status(
    context: AuthoritativeRegimeStressContext | None,
) -> ConstructionMethodStatus:
    if context is None:
        return ConstructionMethodStatus.DEGRADED
    if context.worst_case_loss_pct > context.maximum_allowed_loss_pct:
        return ConstructionMethodStatus.PENDING_REVIEW
    return context.supportability_status


__all__ = [
    "cashflow_projection_reason_codes",
    "currency_overlay_status",
    "derive_currency_overlay_context",
    "derive_liquidity_context",
    "liquidity_reason_codes",
    "liquidity_status",
    "missing_currency_overlay_pairs",
    "post_trade_cash_weight",
    "regime_stress_status",
]
