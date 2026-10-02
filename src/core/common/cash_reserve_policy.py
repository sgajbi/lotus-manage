from decimal import Decimal

from src.core.models import EngineOptions


def effective_cash_reserve_floor(options: EngineOptions) -> Decimal:
    """Return the construction floor without changing target or band semantics."""

    source_target = options.cash_reserve_target_weight or Decimal("0")
    return max(options.min_cash_buffer_pct, source_target)


__all__ = ["effective_cash_reserve_floor"]
