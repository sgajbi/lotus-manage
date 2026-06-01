from __future__ import annotations

import hashlib
import json
from datetime import datetime

from src.core.outcomes import (
    DpmExpectedOutcomeSnapshot,
    DpmOutcomeEvent,
    DpmOutcomeReviewComparison,
    DpmRealizedOutcomeSnapshot,
    OutcomeEventType,
)


def build_review_content_hash(
    *,
    expected_snapshot: DpmExpectedOutcomeSnapshot,
    realized_snapshot: DpmRealizedOutcomeSnapshot,
    comparison: DpmOutcomeReviewComparison,
) -> str:
    return _content_hash(
        {
            "expected_snapshot": expected_snapshot.model_dump(mode="json"),
            "realized_snapshot": realized_snapshot.model_dump(mode="json"),
            "dimension_results": [
                result.model_dump(mode="json") for result in comparison.dimension_results
            ],
        }
    )


def build_created_outcome_event(
    *,
    outcome_review_id: str,
    comparison: DpmOutcomeReviewComparison,
    expected_snapshot: DpmExpectedOutcomeSnapshot,
    realized_snapshot: DpmRealizedOutcomeSnapshot,
    actor_id: str,
    created_at: datetime,
) -> DpmOutcomeEvent:
    return DpmOutcomeEvent(
        event_id=f"{outcome_review_id}_created",
        event_type=created_event_type(comparison.state),
        event_time=created_at.isoformat(),
        actor=actor_id,
        outcome_review_id=outcome_review_id,
        state=comparison.state,
        reason_codes=comparison.supportability.reason_codes,
        source_refs=[*expected_snapshot.source_lineage, *realized_snapshot.source_lineage],
    )


def created_event_type(state: str) -> OutcomeEventType:
    if state == "BLOCKED":
        return "OUTCOME_REVIEW_BLOCKED"
    if state == "DEGRADED":
        return "OUTCOME_REVIEW_DEGRADED"
    if state == "READY":
        return "OUTCOME_REVIEW_READY"
    return "OUTCOME_REVIEW_CREATED"


def _content_hash(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
