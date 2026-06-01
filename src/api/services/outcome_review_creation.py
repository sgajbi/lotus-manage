from __future__ import annotations

import hashlib
import json
from datetime import datetime

from src.core.outcomes import (
    DpmExpectedOutcomeSnapshot,
    DpmOutcomeEvent,
    DpmOutcomeReviewComparison,
    DpmPostTradeOutcomeReview,
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


def build_created_outcome_review(
    *,
    outcome_review_id: str,
    comparison: DpmOutcomeReviewComparison,
    expected_snapshot: DpmExpectedOutcomeSnapshot,
    realized_snapshot: DpmRealizedOutcomeSnapshot,
    actor_id: str,
    correlation_id: str,
    idempotency_key: str,
    content_hash: str,
    created_at: datetime,
) -> DpmPostTradeOutcomeReview:
    event = build_created_outcome_event(
        outcome_review_id=outcome_review_id,
        comparison=comparison,
        expected_snapshot=expected_snapshot,
        realized_snapshot=realized_snapshot,
        actor_id=actor_id,
        created_at=created_at,
    )
    return DpmPostTradeOutcomeReview(
        outcome_review_id=outcome_review_id,
        state=comparison.state,
        portfolio_id=expected_snapshot.portfolio_id,
        mandate_id=expected_snapshot.mandate_id,
        rebalance_run_id=expected_snapshot.rebalance_run_id,
        alternative_set_id=expected_snapshot.alternative_set_id,
        selected_alternative_id=expected_snapshot.selected_alternative_id,
        proof_pack_id=expected_snapshot.proof_pack_id,
        wave_id=expected_snapshot.wave_id,
        wave_item_id=expected_snapshot.wave_item_id,
        operations_handoff_ref_id=expected_snapshot.operations_handoff_ref_id,
        review_window=realized_snapshot.review_window,
        expected_snapshot=expected_snapshot,
        realized_snapshot=realized_snapshot,
        dimension_results=comparison.dimension_results,
        overall_outcome=comparison.overall_outcome,
        variance_summary=comparison.variance_summary,
        supportability=comparison.supportability,
        source_lineage=[*expected_snapshot.source_lineage, *realized_snapshot.source_lineage],
        source_hashes={**expected_snapshot.source_hashes, **realized_snapshot.source_hashes},
        section_hashes=expected_snapshot.section_hashes,
        events=[event],
        content_hash=content_hash,
        created_at=created_at,
        created_by=actor_id,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
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
