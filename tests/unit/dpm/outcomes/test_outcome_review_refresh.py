from datetime import datetime, timezone
from decimal import Decimal

from src.api.services.outcome_review_dimensions import DpmOutcomeDimensionConfig
from src.api.services.outcome_review_refresh import (
    build_source_refresh_result,
    build_source_refreshed_event,
)
from src.core.outcomes import DpmOutcomeReviewComparison, DpmOutcomeTolerance
from tests.unit.infrastructure.test_outcome_review_repository import _review


REFRESHED_AT = datetime(2026, 5, 6, 2, 15, tzinfo=timezone.utc)


def _comparison(state: str = "READY") -> DpmOutcomeReviewComparison:
    review = _review(state=state)
    return DpmOutcomeReviewComparison(
        state=state,
        dimension_results=review.dimension_results,
        overall_outcome=review.overall_outcome,
        variance_summary=review.variance_summary,
        supportability=review.supportability,
    )


def _dimension_config() -> DpmOutcomeDimensionConfig:
    return DpmOutcomeDimensionConfig(
        dimension="DRIFT_REDUCTION",
        tolerance=DpmOutcomeTolerance(soft=Decimal("0.0025"), hard=Decimal("0.0100")),
        materiality=Decimal("0.0050"),
        direction="LOWER_IS_BETTER",
    )


def test_build_source_refreshed_event_projects_state_reason_codes_and_lineage() -> None:
    review = _review()

    event = build_source_refreshed_event(
        outcome_review_id=review.outcome_review_id,
        expected_snapshot=review.expected_snapshot,
        realized_snapshot=review.realized_snapshot,
        comparison=_comparison(),
        actor_id="system",
        refreshed_at=REFRESHED_AT,
        event_id_suffix="abc123ef",
    )

    assert event.event_id == "dor_001_source_refreshed_abc123ef"
    assert event.event_type == "OUTCOME_REVIEW_SOURCE_REFRESHED"
    assert event.event_time == REFRESHED_AT.isoformat()
    assert event.actor == "system"
    assert event.outcome_review_id == "dor_001"
    assert event.state == "READY"
    assert event.reason_codes == ["SOURCE_READY"]
    assert [ref.source_id for ref in event.source_refs] == ["expected", "realized"]


def test_build_source_refresh_result_compares_snapshot_and_builds_event() -> None:
    review = _review()

    event, comparison = build_source_refresh_result(
        review=review,
        realized_snapshot=review.realized_snapshot,
        dimension_configs=[_dimension_config()],
        actor_id="system",
        refreshed_at=REFRESHED_AT,
        event_id_suffix="def456ab",
    )

    assert comparison.state == "READY"
    assert [result.dimension for result in comparison.dimension_results] == ["DRIFT_REDUCTION"]
    assert event.event_id == "dor_001_source_refreshed_def456ab"
    assert event.state == comparison.state
    assert event.reason_codes == comparison.supportability.reason_codes
    assert [ref.source_id for ref in event.source_refs] == ["expected", "realized"]
