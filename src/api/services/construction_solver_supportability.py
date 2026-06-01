from src.core.construction.method_registry import classify_solver_failure
from src.core.construction.models import ConstructionEnrichmentSummary
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.models import RebalanceResult


def with_method_reason_codes(
    *,
    enrichment: ConstructionEnrichmentSummary,
    reason_codes: list[str],
) -> ConstructionEnrichmentSummary:
    return enrichment.model_copy(
        update={"reason_codes": sorted(set(enrichment.reason_codes) | set(reason_codes))}
    )


def solver_method_status(*, result: RebalanceResult) -> ConstructionMethodStatus:
    solver_warnings = [
        warning
        for warning in result.diagnostics.warnings
        if warning.startswith(("SOLVER_", "INFEASIBLE_", "UNBOUNDED_"))
    ]
    if not solver_warnings:
        return ConstructionMethodStatus.READY
    return _lowest_status([classify_solver_failure(warning) for warning in solver_warnings])


def _lowest_status(statuses: list[ConstructionMethodStatus]) -> ConstructionMethodStatus:
    status_order = {
        ConstructionMethodStatus.BLOCKED: 0,
        ConstructionMethodStatus.DEGRADED: 1,
        ConstructionMethodStatus.PENDING_REVIEW: 2,
        ConstructionMethodStatus.READY: 3,
    }
    return min(statuses, key=lambda item: status_order[item])


__all__ = [
    "solver_method_status",
    "with_method_reason_codes",
]
