"""Portfolio construction alternative domain primitives."""

from src.core.construction.alternative_engine import (
    build_alternative_set,
    build_do_nothing_baseline,
    build_rebalance_result_alternative,
)
from src.core.construction.enrichment import (
    estimate_transaction_cost,
    summarize_enrichment_posture,
)
from src.core.construction.models import (
    ConstructionAlternative,
    ConstructionAlternativeSet,
    ConstructionComparisonMetrics,
    ConstructionEnrichmentSummary,
    ConstructionConstraintTrace,
    ConstructionMethodDefinition,
    ConstructionMethodPlan,
    ConstructionObjectiveTerm,
    ConstructionSolverPosture,
)
from src.core.construction.method_registry import (
    METHOD_REGISTRY,
    classify_solver_failure,
    first_wave_method_definitions,
    get_method_definition,
    resolve_method_plan,
)
from src.core.construction.vocabulary import (
    ConstructionMethod,
    ConstructionMethodStatus,
    ConstructionSourceFamily,
    ConstructionTraceTerm,
    FIRST_WAVE_CONSTRUCTION_METHODS,
    SOURCE_AWARE_CONSTRUCTION_METHODS,
)

__all__ = [
    "ConstructionAlternative",
    "ConstructionAlternativeSet",
    "ConstructionComparisonMetrics",
    "ConstructionConstraintTrace",
    "ConstructionEnrichmentSummary",
    "ConstructionMethod",
    "ConstructionMethodDefinition",
    "ConstructionMethodPlan",
    "ConstructionMethodStatus",
    "ConstructionObjectiveTerm",
    "ConstructionSourceFamily",
    "ConstructionSolverPosture",
    "ConstructionTraceTerm",
    "FIRST_WAVE_CONSTRUCTION_METHODS",
    "METHOD_REGISTRY",
    "SOURCE_AWARE_CONSTRUCTION_METHODS",
    "build_alternative_set",
    "build_do_nothing_baseline",
    "build_rebalance_result_alternative",
    "classify_solver_failure",
    "estimate_transaction_cost",
    "first_wave_method_definitions",
    "get_method_definition",
    "resolve_method_plan",
    "summarize_enrichment_posture",
]
