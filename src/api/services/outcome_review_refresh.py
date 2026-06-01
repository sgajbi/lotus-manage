from __future__ import annotations

from datetime import datetime

from src.core.outcomes import (
    DpmExpectedOutcomeSnapshot,
    DpmOutcomeEvent,
    DpmOutcomeReviewComparison,
    DpmPostTradeOutcomeReview,
    DpmRealizedOutcomeSnapshot,
    compare_outcome_dimensions,
)
from src.api.services.outcome_review_dimensions import (
    DpmOutcomeDimensionConfig,
    dimension_inputs_for_review,
)


def build_source_refresh_result(
    *,
    review: DpmPostTradeOutcomeReview,
    realized_snapshot: DpmRealizedOutcomeSnapshot,
    dimension_configs: list[DpmOutcomeDimensionConfig],
    actor_id: str,
    refreshed_at: datetime,
    event_id_suffix: str,
) -> tuple[DpmOutcomeEvent, DpmOutcomeReviewComparison]:
    comparison = compare_outcome_dimensions(
        dimension_inputs_for_review(
            expected_snapshot=review.expected_snapshot,
            realized_snapshot=realized_snapshot,
            dimension_configs=dimension_configs,
        )
    )
    event = build_source_refreshed_event(
        outcome_review_id=review.outcome_review_id,
        expected_snapshot=review.expected_snapshot,
        realized_snapshot=realized_snapshot,
        comparison=comparison,
        actor_id=actor_id,
        refreshed_at=refreshed_at,
        event_id_suffix=event_id_suffix,
    )
    return event, comparison


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
