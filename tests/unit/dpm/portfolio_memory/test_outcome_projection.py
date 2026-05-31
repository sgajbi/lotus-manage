from src.core.outcomes import DpmOutcomeEvent, DpmOutcomeSourceRef
from src.core.portfolio_memory.outcome_projection import outcome_review_events
from tests.unit.infrastructure.test_outcome_review_repository import _review


def test_outcome_review_created_event_projects_review_lineage_and_handoff_refs() -> None:
    review = _review()

    event = outcome_review_events(review=review, persisted_events=[])[0]

    assert event.event_type == "OUTCOME_REVIEW_CREATED"
    assert event.source_type == "DPM_POST_TRADE_OUTCOME_REVIEW"
    assert event.source_id == review.outcome_review_id
    assert event.supportability_state == "READY"
    assert event.reason_codes == ["SOURCE_READY"]
    assert [ref.source_id for ref in event.source_refs] == ["expected", "realized"]
    assert event.content_hash == review.content_hash
    assert event.metadata["proof_pack_id"] == "dpp_001"
    assert event.metadata["operations_handoff_ref_id"] == "dwh_001"


def test_outcome_review_events_prefer_persisted_event_for_duplicate_id() -> None:
    review = _review()
    persisted_event = DpmOutcomeEvent(
        event_id=review.events[0].event_id,
        event_type="OUTCOME_REVIEW_DEGRADED",
        event_time="2026-05-06T02:30:00Z",
        actor="ops_001",
        outcome_review_id=review.outcome_review_id,
        state="DEGRADED",
        reason_codes=["REALIZED_SOURCE_DEGRADED"],
        source_refs=[
            DpmOutcomeSourceRef(
                source_system="lotus-performance",
                source_type="PerformanceOutcomeEvidence",
                source_id="performance-outcome-001",
                source_version="v1",
                content_hash="sha256:performance-outcome",
            )
        ],
    )

    events = outcome_review_events(review=review, persisted_events=[persisted_event])
    projected_event = events[1]

    assert len(events) == 2
    assert projected_event.event_type == "OUTCOME_REVIEW_EVENT"
    assert projected_event.source_type == "OUTCOME_REVIEW_DEGRADED"
    assert projected_event.status == "DEGRADED"
    assert projected_event.supportability_state == "DEGRADED"
    assert projected_event.reason_codes == ["REALIZED_SOURCE_DEGRADED"]
    assert projected_event.source_refs[0].source_system == "lotus-performance"
    assert projected_event.metadata == {"outcome_review_id": review.outcome_review_id}
