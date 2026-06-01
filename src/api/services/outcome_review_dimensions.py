from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.core.outcomes import (
    DpmExpectedOutcomeSnapshot,
    DpmOutcomeDimensionInput,
    DpmOutcomeTolerance,
    DpmRealizedOutcomeSnapshot,
    OutcomeComparisonDirection,
    OutcomeDimension,
)


class DpmOutcomeReviewValidationError(Exception):
    pass


@dataclass(frozen=True)
class DpmOutcomeDimensionConfig:
    dimension: OutcomeDimension
    tolerance: DpmOutcomeTolerance
    materiality: Decimal
    direction: OutcomeComparisonDirection


def dimension_inputs_for_review(
    *,
    expected_snapshot: DpmExpectedOutcomeSnapshot,
    realized_snapshot: DpmRealizedOutcomeSnapshot,
    dimension_configs: list[DpmOutcomeDimensionConfig],
) -> list[DpmOutcomeDimensionInput]:
    inputs: list[DpmOutcomeDimensionInput] = []
    for config in dimension_configs:
        expected = expected_snapshot.expected_values.get(config.dimension)
        realized = realized_snapshot.realized_values.get(config.dimension)
        if expected is None or realized is None:
            raise DpmOutcomeReviewValidationError(
                f"DPM_OUTCOME_DIMENSION_EVIDENCE_MISSING:{config.dimension}"
            )
        inputs.append(
            DpmOutcomeDimensionInput(
                dimension=config.dimension,
                expected=expected,
                realized=realized,
                tolerance=config.tolerance,
                materiality=config.materiality,
                direction=config.direction,
            )
        )
    return inputs


__all__ = [
    "DpmOutcomeDimensionConfig",
    "DpmOutcomeReviewValidationError",
    "dimension_inputs_for_review",
]
