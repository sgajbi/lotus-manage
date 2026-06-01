from __future__ import annotations

from datetime import datetime

from src.core.outcomes import (
    DpmExpectedOutcomeSnapshot,
    DpmOutcomeEvent,
    DpmOutcomeReviewComparison,
    DpmRealizedOutcomeSnapshot,
)


def build_source_refreshed_event(
    *,
    outcome_review_id: str,
    expected_snapshot: DpmExpectedOutcomeSnapshot,
    realized_snapshot: DpmRealizedOutcomeSnapshot,
    comparison: DpmOutcomeReviewComparison,
    actor_id: str,
    refreshed_at: datetime,
    event_id_suffix: str,
) -> DpmOutcomeEvent:
    return DpmOutcomeEvent(
        event_id=f"{outcome_review_id}_source_refreshed_{event_id_suffix}",
        event_type="OUTCOME_REVIEW_SOURCE_REFRESHED",
        event_time=refreshed_at.isoformat(),
        actor=actor_id,
        outcome_review_id=outcome_review_id,
        state=comparison.state,
        reason_codes=comparison.supportability.reason_codes,
        source_refs=[*expected_snapshot.source_lineage, *realized_snapshot.source_lineage],
    )
