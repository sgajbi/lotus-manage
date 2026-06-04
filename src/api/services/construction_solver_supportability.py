from src.core.construction.method_registry import classify_solver_failure
from src.core.construction.models import ConstructionEnrichmentSummary
from src.core.construction.status import lowest_construction_status
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
    solver_warnings = solver_warning_codes(result=result)
    if not solver_warnings:
        return ConstructionMethodStatus.READY
    return lowest_construction_status(
        classify_solver_failure(warning) for warning in solver_warnings
    )


def solver_warning_codes(*, result: RebalanceResult) -> list[str]:
    return [
        warning
        for warning in result.diagnostics.warnings
        if warning.startswith(("SOLVER_", "INFEASIBLE_", "UNBOUNDED_"))
    ]


__all__ = [
    "solver_method_status",
    "solver_warning_codes",
    "with_method_reason_codes",
]
