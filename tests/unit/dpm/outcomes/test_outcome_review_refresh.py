from datetime import datetime, timezone

from src.api.services.outcome_review_refresh import build_source_refreshed_event
from src.core.outcomes import DpmOutcomeReviewComparison
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
