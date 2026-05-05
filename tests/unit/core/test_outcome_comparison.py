from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.core.outcomes import (
    DpmOutcomeDimensionInput,
    DpmOutcomeMetricValue,
    DpmOutcomeSourceFreshness,
    DpmOutcomeSourceRef,
    DpmOutcomeSupportability,
    DpmOutcomeTolerance,
    compare_outcome_dimension,
    compare_outcome_dimensions,
)


def _source_ref(source_system: str = "lotus-performance") -> DpmOutcomeSourceRef:
    return DpmOutcomeSourceRef(
        source_system=source_system,
        source_type="OUTCOME_VALUE",
        source_id=f"{source_system}_outcome_001",
        source_version="1.0.0",
        content_hash=f"sha256:{source_system}-outcome",
    )


def _metric(
    value: str | None,
    *,
    source_system: str = "lotus-performance",
    state: str = "READY",
    freshness_state: str = "CURRENT",
) -> DpmOutcomeMetricValue:
    return DpmOutcomeMetricValue(
        value=Decimal(value) if value is not None else None,
        unit="ratio",
        source_refs=[_source_ref(source_system)],
        source_freshness=DpmOutcomeSourceFreshness(
            observed_at="2026-05-05T01:15:00Z",
            as_of_date="2026-05-05",
            freshness_state=freshness_state,
        ),
        supportability=DpmOutcomeSupportability(
            state=state,
            reason_codes=[f"SOURCE_{state}"],
            required_source=True,
            explanation=f"{source_system} source is {state}.",
        ),
    )


def _dimension(
    *,
    dimension: str = "DRIFT_REDUCTION",
    expected: str | None = "0.1200",
    realized: str | None = "0.1180",
    expected_state: str = "READY",
    realized_state: str = "READY",
    direction: str = "LOWER_IS_BETTER",
) -> DpmOutcomeDimensionInput:
    return DpmOutcomeDimensionInput(
        dimension=dimension,
        expected=_metric(expected, source_system="lotus-manage", state=expected_state),
        realized=_metric(realized, source_system="lotus-performance", state=realized_state),
        tolerance=DpmOutcomeTolerance(soft=Decimal("0.0025"), hard=Decimal("0.0100")),
        materiality=Decimal("0.0050"),
        direction=direction,
    )


def test_lower_is_better_dimension_is_ready_when_realized_is_inside_tolerance() -> None:
    result = compare_outcome_dimension(
        _dimension(dimension="DRIFT_REDUCTION", expected="0.1200", realized="0.1210")
    )

    assert result.state == "READY"
    assert result.reason_code == "DRIFT_REDUCTION_ACHIEVED"
    assert result.variance == Decimal("0.0010")
    assert result.calculation_trace["variance_pressure"] == Decimal("0.0010")
    assert {ref.source_system for ref in result.source_refs} == {
        "lotus-manage",
        "lotus-performance",
    }


def test_soft_tolerance_variance_requires_pm_review_without_hard_breach() -> None:
    result = compare_outcome_dimension(
        _dimension(dimension="DRIFT_REDUCTION", expected="0.1200", realized="0.1260")
    )

    assert result.state == "PENDING_REVIEW"
    assert result.reason_code == "DRIFT_REDUCTION_SHORTFALL"
    assert result.calculation_trace["variance_pressure"] == Decimal("0.0060")


def test_hard_tolerance_variance_is_breached() -> None:
    result = compare_outcome_dimension(
        _dimension(dimension="COST", expected="100.00", realized="111.00")
    )

    assert result.state == "BREACHED"
    assert result.reason_code == "COST_ABOVE_ESTIMATE"
    assert result.variance == Decimal("11.00")


def test_higher_is_better_performance_shortfall_uses_performance_reason() -> None:
    result = compare_outcome_dimension(
        _dimension(
            dimension="PERFORMANCE",
            expected="0.0150",
            realized="0.0080",
            direction="HIGHER_IS_BETTER",
        )
    )

    assert result.state == "PENDING_REVIEW"
    assert result.reason_code == "PERFORMANCE_BELOW_EXPECTATION"
    assert result.calculation_trace["variance_pressure"] == Decimal("0.0070")


def test_missing_mandatory_value_blocks_deterministic_comparison() -> None:
    result = compare_outcome_dimension(_dimension(expected="0.1200", realized=None))

    assert result.state == "BLOCKED"
    assert result.reason_code == "SOURCE_EVIDENCE_INCOMPLETE"
    assert result.variance is None


def test_degraded_source_with_values_remains_degraded_not_ready() -> None:
    result = compare_outcome_dimension(
        _dimension(expected="0.1200", realized="0.1190", realized_state="DEGRADED")
    )

    assert result.state == "DEGRADED"
    assert result.reason_code == "SOURCE_EVIDENCE_INCOMPLETE"


def test_not_supported_dimension_cannot_become_ready_even_when_values_exist() -> None:
    result = compare_outcome_dimension(
        _dimension(
            dimension="RISK_REDUCTION",
            expected="0.3000",
            realized="0.2500",
            realized_state="NOT_SUPPORTED",
        )
    )

    assert result.state == "NOT_SUPPORTED"
    assert result.reason_code == "RISK_OUTCOME_NOT_SUPPORTED"
    assert result.variance is None


def test_review_rollup_prioritizes_blocked_then_breached_then_degraded() -> None:
    comparison = compare_outcome_dimensions(
        [
            _dimension(dimension="DRIFT_REDUCTION", expected="0.1200", realized="0.1180"),
            _dimension(dimension="COST", expected="100.00", realized="111.00"),
            _dimension(
                dimension="EXECUTION_QUALITY",
                expected="0.0005",
                realized=None,
                realized_state="BLOCKED",
            ),
        ]
    )

    assert comparison.state == "BLOCKED"
    assert comparison.overall_outcome == "SOURCE_BLOCKED"
    assert comparison.supportability.reason_codes == [
        "DRIFT_REDUCTION_ACHIEVED",
        "COST_ABOVE_ESTIMATE",
        "EXECUTION_EVIDENCE_BLOCKED",
    ]
    assert comparison.variance_summary["EXECUTION_QUALITY"] is None


def test_review_rollup_treats_mixed_ready_and_not_supported_as_degraded() -> None:
    comparison = compare_outcome_dimensions(
        [
            _dimension(dimension="DRIFT_REDUCTION", expected="0.1200", realized="0.1180"),
            _dimension(
                dimension="PERFORMANCE",
                expected="0.0150",
                realized="0.0160",
                realized_state="NOT_SUPPORTED",
                direction="HIGHER_IS_BETTER",
            ),
        ]
    )

    assert comparison.state == "DEGRADED"
    assert comparison.overall_outcome == "SOURCE_DEGRADED"
    assert "PERFORMANCE_OUTCOME_NOT_SUPPORTED" in comparison.supportability.reason_codes


def test_tolerance_requires_hard_threshold_to_be_at_least_soft_threshold() -> None:
    with pytest.raises(ValidationError, match="hard tolerance"):
        DpmOutcomeTolerance(soft=Decimal("0.0100"), hard=Decimal("0.0025"))
