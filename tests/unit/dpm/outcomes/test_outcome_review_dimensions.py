from decimal import Decimal

import pytest

from src.api.services import outcome_review_dimensions, outcome_review_service
from src.api.services.outcome_review_dimensions import (
    DpmOutcomeDimensionConfig,
    DpmOutcomeReviewValidationError,
    dimension_inputs_for_review,
)
from src.core.outcomes import (
    DpmExpectedOutcomeSnapshot,
    DpmOutcomeMetricValue,
    DpmOutcomeSupportability,
    DpmOutcomeTolerance,
    DpmOutcomeReviewWindow,
    DpmRealizedOutcomeSnapshot,
)


def _metric(value: str) -> DpmOutcomeMetricValue:
    return DpmOutcomeMetricValue(value=Decimal(value), unit="ratio")


def _expected(
    *,
    expected_values: dict[str, DpmOutcomeMetricValue] | None = None,
) -> DpmExpectedOutcomeSnapshot:
    return DpmExpectedOutcomeSnapshot.model_construct(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        alternative_set_id="cas_001",
        selected_alternative_id="alt_selected",
        proof_pack_id="dpp_001",
        expected_values=(
            expected_values
            if expected_values is not None
            else {"DRIFT_REDUCTION": _metric("0.012")}
        ),
        supportability=DpmOutcomeSupportability(state="READY"),
    )


def _realized(
    *,
    realized_values: dict[str, DpmOutcomeMetricValue] | None = None,
) -> DpmRealizedOutcomeSnapshot:
    return DpmRealizedOutcomeSnapshot.model_construct(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=DpmOutcomeReviewWindow(
            start_at="2026-05-06T01:00:00Z",
            end_at="2026-05-07T01:00:00Z",
            as_of_date="2026-05-07",
        ),
        realized_values=(
            realized_values
            if realized_values is not None
            else {"DRIFT_REDUCTION": _metric("0.010")}
        ),
        supportability=DpmOutcomeSupportability(state="READY"),
    )


def _config() -> DpmOutcomeDimensionConfig:
    return DpmOutcomeDimensionConfig(
        dimension="DRIFT_REDUCTION",
        tolerance=DpmOutcomeTolerance(soft=Decimal("0.0025"), hard=Decimal("0.0100")),
        materiality=Decimal("0.0050"),
        direction="LOWER_IS_BETTER",
    )


def test_dimension_inputs_for_review_projects_configured_dimension_evidence() -> None:
    inputs = dimension_inputs_for_review(
        expected_snapshot=_expected(),
        realized_snapshot=_realized(),
        dimension_configs=[_config()],
    )

    assert len(inputs) == 1
    assert inputs[0].dimension == "DRIFT_REDUCTION"
    assert inputs[0].expected.value == Decimal("0.012")
    assert inputs[0].realized.value == Decimal("0.010")
    assert inputs[0].tolerance.soft == Decimal("0.0025")
    assert inputs[0].materiality == Decimal("0.0050")
    assert inputs[0].direction == "LOWER_IS_BETTER"


@pytest.mark.parametrize(
    ("expected_values", "realized_values"),
    [
        ({}, {"DRIFT_REDUCTION": _metric("0.010")}),
        ({"DRIFT_REDUCTION": _metric("0.012")}, {}),
    ],
)
def test_dimension_inputs_for_review_rejects_missing_expected_or_realized_evidence(
    expected_values: dict[str, DpmOutcomeMetricValue],
    realized_values: dict[str, DpmOutcomeMetricValue],
) -> None:
    with pytest.raises(DpmOutcomeReviewValidationError) as exc_info:
        dimension_inputs_for_review(
            expected_snapshot=_expected(expected_values=expected_values),
            realized_snapshot=_realized(realized_values=realized_values),
            dimension_configs=[_config()],
        )

    assert str(exc_info.value) == "DPM_OUTCOME_DIMENSION_EVIDENCE_MISSING:DRIFT_REDUCTION"


def test_outcome_review_dimensions_exports_dimension_helper_surface() -> None:
    assert outcome_review_dimensions.__all__ == [
        "DpmOutcomeDimensionConfig",
        "DpmOutcomeReviewValidationError",
        "dimension_inputs_for_review",
    ]


def test_service_preserves_dimension_import_surface() -> None:
    assert outcome_review_service.DpmOutcomeDimensionConfig is DpmOutcomeDimensionConfig
    assert outcome_review_service.DpmOutcomeReviewValidationError is DpmOutcomeReviewValidationError
    assert outcome_review_service._dimension_inputs is dimension_inputs_for_review
