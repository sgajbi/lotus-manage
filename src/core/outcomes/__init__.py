"""RFC-0042 post-trade outcome domain primitives."""

from src.core.outcomes.comparison import (
    compare_outcome_dimension,
    compare_outcome_dimensions,
)
from src.core.outcomes.models import (
    DpmExpectedOutcomeSnapshot,
    DpmOutcomeDimensionInput,
    DpmOutcomeDimensionResult,
    DpmOutcomeEvent,
    DpmOutcomeMetricValue,
    DpmOutcomeReviewWindow,
    DpmOutcomeReviewComparison,
    DpmOutcomeSourceFreshness,
    DpmOutcomeSourceRef,
    DpmOutcomeSupportability,
    DpmOutcomeTolerance,
    DpmRealizedOutcomeSnapshot,
    DpmRealizedSourceSnapshot,
    OutcomeComparisonDirection,
    OutcomeDimension,
    OutcomeDimensionState,
    OutcomeEventType,
    OutcomeReviewState,
)
from src.core.outcomes.snapshots import (
    DpmExpectedSnapshotAssemblyError,
    assemble_expected_outcome_snapshot,
)
from src.core.outcomes.realized_sources import assemble_realized_outcome_snapshot

__all__ = [
    "DpmExpectedOutcomeSnapshot",
    "DpmExpectedSnapshotAssemblyError",
    "DpmOutcomeDimensionInput",
    "DpmOutcomeDimensionResult",
    "DpmOutcomeEvent",
    "DpmOutcomeMetricValue",
    "DpmOutcomeReviewWindow",
    "DpmOutcomeReviewComparison",
    "DpmOutcomeSourceFreshness",
    "DpmOutcomeSourceRef",
    "DpmOutcomeSupportability",
    "DpmOutcomeTolerance",
    "DpmRealizedOutcomeSnapshot",
    "DpmRealizedSourceSnapshot",
    "OutcomeComparisonDirection",
    "OutcomeDimension",
    "OutcomeDimensionState",
    "OutcomeEventType",
    "OutcomeReviewState",
    "assemble_expected_outcome_snapshot",
    "assemble_realized_outcome_snapshot",
    "compare_outcome_dimension",
    "compare_outcome_dimensions",
]
