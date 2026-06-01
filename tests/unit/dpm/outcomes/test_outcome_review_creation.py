from datetime import datetime, timezone

from src.api.services.outcome_review_creation import (
    build_created_outcome_event,
    build_review_content_hash,
    created_event_type,
)
from src.core.outcomes import DpmOutcomeReviewComparison
from tests.unit.infrastructure.test_outcome_review_repository import _review


CREATED_AT = datetime(2026, 5, 6, 1, 20, tzinfo=timezone.utc)


def _comparison(state: str = "READY") -> DpmOutcomeReviewComparison:
    review = _review(state=state)
    return DpmOutcomeReviewComparison(
        state=state,
        dimension_results=review.dimension_results,
        overall_outcome=review.overall_outcome,
        variance_summary=review.variance_summary,
        supportability=review.supportability,
    )


def test_created_event_type_maps_review_state_to_bounded_event_type() -> None:
    assert created_event_type("READY") == "OUTCOME_REVIEW_READY"
    assert created_event_type("DEGRADED") == "OUTCOME_REVIEW_DEGRADED"
    assert created_event_type("BLOCKED") == "OUTCOME_REVIEW_BLOCKED"
    assert created_event_type("PENDING_REVIEW") == "OUTCOME_REVIEW_CREATED"


def test_build_created_outcome_event_combines_expected_and_realized_lineage() -> None:
    review = _review()
    event = build_created_outcome_event(
        outcome_review_id=review.outcome_review_id,
        comparison=_comparison(),
        expected_snapshot=review.expected_snapshot,
        realized_snapshot=review.realized_snapshot,
        actor_id="pm_creation",
        created_at=CREATED_AT,
    )

    assert event.event_id == "dor_001_created"
    assert event.event_type == "OUTCOME_REVIEW_READY"
    assert event.event_time == CREATED_AT.isoformat()
    assert event.actor == "pm_creation"
    assert event.outcome_review_id == "dor_001"
    assert event.state == "READY"
    assert event.reason_codes == ["SOURCE_READY"]
    assert [ref.source_id for ref in event.source_refs] == ["expected", "realized"]


def test_build_review_content_hash_is_stable_and_changes_with_source_snapshot() -> None:
    review = _review()
    ready_hash = build_review_content_hash(
        expected_snapshot=review.expected_snapshot,
        realized_snapshot=review.realized_snapshot,
        comparison=_comparison(),
    )
    changed_realized = review.realized_snapshot.model_copy(
        update={"source_hashes": {"realized": "sha256:changed-realized"}}
    )
    changed_hash = build_review_content_hash(
        expected_snapshot=review.expected_snapshot,
        realized_snapshot=changed_realized,
        comparison=_comparison(),
    )

    assert ready_hash.startswith("sha256:")
    assert ready_hash == build_review_content_hash(
        expected_snapshot=review.expected_snapshot,
        realized_snapshot=review.realized_snapshot,
        comparison=_comparison(),
    )
    assert changed_hash != ready_hash
