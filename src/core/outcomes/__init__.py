"""RFC-0042 post-trade outcome domain primitives."""

from src.core.outcomes.comparison import (
    compare_outcome_dimension,
    compare_outcome_dimensions,
)
from src.core.outcomes.models import (
    DpmOutcomeDimensionInput,
    DpmOutcomeDimensionResult,
    DpmOutcomeEvent,
    DpmOutcomeMetricValue,
    DpmOutcomeReviewComparison,
    DpmOutcomeSourceFreshness,
    DpmOutcomeSourceRef,
    DpmOutcomeSupportability,
    DpmOutcomeTolerance,
    OutcomeComparisonDirection,
    OutcomeDimension,
    OutcomeDimensionState,
    OutcomeEventType,
    OutcomeReviewState,
)

__all__ = [
    "DpmOutcomeDimensionInput",
    "DpmOutcomeDimensionResult",
    "DpmOutcomeEvent",
    "DpmOutcomeMetricValue",
    "DpmOutcomeReviewComparison",
    "DpmOutcomeSourceFreshness",
    "DpmOutcomeSourceRef",
    "DpmOutcomeSupportability",
    "DpmOutcomeTolerance",
    "OutcomeComparisonDirection",
    "OutcomeDimension",
    "OutcomeDimensionState",
    "OutcomeEventType",
    "OutcomeReviewState",
    "compare_outcome_dimension",
    "compare_outcome_dimensions",
]
