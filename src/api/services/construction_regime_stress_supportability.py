from src.core.construction.models import AuthoritativeRegimeStressContext
from src.core.construction.vocabulary import ConstructionMethodStatus


def regime_stress_status(
    context: AuthoritativeRegimeStressContext | None,
) -> ConstructionMethodStatus:
    if context is None:
        return ConstructionMethodStatus.DEGRADED
    if regime_stress_threshold_breached(context):
        return ConstructionMethodStatus.PENDING_REVIEW
    return context.supportability_status


def regime_stress_threshold_breached(context: AuthoritativeRegimeStressContext) -> bool:
    return context.worst_case_loss_pct > context.maximum_allowed_loss_pct


__all__ = [
    "regime_stress_status",
    "regime_stress_threshold_breached",
]
