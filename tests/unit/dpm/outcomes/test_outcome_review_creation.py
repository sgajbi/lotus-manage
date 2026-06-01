from datetime import datetime, timezone

from src.api.services.outcome_review_creation import (
    build_created_outcome_event,
    build_created_outcome_review,
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


def test_build_created_outcome_review_preserves_source_lineage_and_identity() -> None:
    source_review = _review()
    comparison = _comparison()

    review = build_created_outcome_review(
        outcome_review_id="dor_created_001",
        comparison=comparison,
        expected_snapshot=source_review.expected_snapshot,
        realized_snapshot=source_review.realized_snapshot,
        actor_id="pm_creation",
        correlation_id="corr_created_001",
        idempotency_key="idem_created_001",
        content_hash="sha256:created-review",
        created_at=CREATED_AT,
    )

    assert review.outcome_review_id == "dor_created_001"
    assert review.state == comparison.state
    assert review.portfolio_id == source_review.expected_snapshot.portfolio_id
    assert review.review_window == source_review.realized_snapshot.review_window
    assert review.source_hashes == {"expected": "sha256:expected", "realized": "sha256:realized"}
    assert [ref.source_id for ref in review.source_lineage] == ["expected", "realized"]
    assert review.events == [
        build_created_outcome_event(
            outcome_review_id="dor_created_001",
            comparison=comparison,
            expected_snapshot=source_review.expected_snapshot,
            realized_snapshot=source_review.realized_snapshot,
            actor_id="pm_creation",
            created_at=CREATED_AT,
        )
    ]
    assert review.content_hash == "sha256:created-review"
    assert review.created_by == "pm_creation"
    assert review.correlation_id == "corr_created_001"
    assert review.idempotency_key == "idem_created_001"
