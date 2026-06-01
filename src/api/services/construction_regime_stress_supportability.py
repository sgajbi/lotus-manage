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


__all__ = ["regime_stress_status"]
