from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.core.outcomes import (
    DpmExpectedOutcomeSnapshot,
    DpmOutcomeEvent,
    DpmOutcomeMetricValue,
    DpmOutcomeReviewWindow,
    DpmOutcomeSourceFreshness,
    DpmOutcomeSourceRef,
    DpmOutcomeSupportability,
    DpmOutcomeTolerance,
    DpmPostTradeOutcomeReview,
    DpmRealizedOutcomeSnapshot,
    compare_outcome_dimension,
)
from src.core.outcomes.models import DpmOutcomeDimensionInput
from src.core.outcomes.repository import DpmOutcomeReviewConflictError
from src.infrastructure.outcomes import InMemoryDpmOutcomeReviewRepository


def _window() -> DpmOutcomeReviewWindow:
    return DpmOutcomeReviewWindow(
        start_at="2026-05-05T01:00:00Z",
        end_at="2026-05-06T01:00:00Z",
        as_of_date="2026-05-06",
    )


def _source_ref(source_id: str) -> DpmOutcomeSourceRef:
    return DpmOutcomeSourceRef(
        source_system="lotus-manage",
        source_type="TEST_SOURCE",
        source_id=source_id,
        content_hash=f"sha256:{source_id}",
    )


def _metric(value: str) -> DpmOutcomeMetricValue:
    return DpmOutcomeMetricValue(
        value=Decimal(value),
        unit="ratio",
        source_refs=[_source_ref("metric")],
        source_freshness=DpmOutcomeSourceFreshness(
            observed_at="2026-05-06T01:10:00Z",
            as_of_date="2026-05-06",
            freshness_state="CURRENT",
        ),
        supportability=DpmOutcomeSupportability(state="READY", reason_codes=["SOURCE_READY"]),
    )


def _review(
    *,
    outcome_review_id: str = "dor_001",
    content_hash: str = "sha256:review",
    state: str = "READY",
    idempotency_key: str | None = "idem_001",
) -> DpmPostTradeOutcomeReview:
    expected_metric = _metric("0.0350")
    realized_metric = _metric("0.0340")
    dimension_result = compare_outcome_dimension(
        DpmOutcomeDimensionInput(
            dimension="DRIFT_REDUCTION",
            expected=expected_metric,
            realized=realized_metric,
            tolerance=DpmOutcomeTolerance(soft=Decimal("0.0025"), hard=Decimal("0.0100")),
            materiality=Decimal("0.0050"),
            direction="LOWER_IS_BETTER",
        )
    )
    expected_snapshot = DpmExpectedOutcomeSnapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        rebalance_run_id="rr_001",
        alternative_set_id="cas_001",
        selected_alternative_id="alt_min_turnover",
        proof_pack_id="dpp_001",
        wave_id="dwv_001",
        wave_item_id="dwi_001",
        operations_handoff_ref_id="dwh_001",
        expected_values={"DRIFT_REDUCTION": expected_metric},
        supportability=DpmOutcomeSupportability(state="READY", reason_codes=["EXPECTED_READY"]),
        source_lineage=[_source_ref("expected")],
        source_hashes={"expected": "sha256:expected"},
        section_hashes={"selected_alternative": "sha256:selected-section"},
    )
    realized_snapshot = DpmRealizedOutcomeSnapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        realized_values={"DRIFT_REDUCTION": realized_metric},
        supportability=DpmOutcomeSupportability(state="READY", reason_codes=["REALIZED_READY"]),
        source_lineage=[_source_ref("realized")],
        source_hashes={"realized": "sha256:realized"},
        quality_summary={"COMPLETE": 1},
    )
    return DpmPostTradeOutcomeReview(
        outcome_review_id=outcome_review_id,
        state=state,
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        rebalance_run_id="rr_001",
        alternative_set_id="cas_001",
        selected_alternative_id="alt_min_turnover",
        proof_pack_id="dpp_001",
        wave_id="dwv_001",
        wave_item_id="dwi_001",
        operations_handoff_ref_id="dwh_001",
        review_window=_window(),
        expected_snapshot=expected_snapshot,
        realized_snapshot=realized_snapshot,
        dimension_results=[dimension_result],
        overall_outcome="READY_WITHIN_TOLERANCE",
        variance_summary={"DRIFT_REDUCTION": Decimal("-0.0010")},
        supportability=DpmOutcomeSupportability(state=state, reason_codes=["SOURCE_READY"]),
        source_lineage=[_source_ref("expected"), _source_ref("realized")],
        source_hashes={"expected": "sha256:expected", "realized": "sha256:realized"},
        section_hashes={"selected_alternative": "sha256:selected-section"},
        events=[
            DpmOutcomeEvent(
                event_id=f"{outcome_review_id}_created",
                event_type="OUTCOME_REVIEW_CREATED",
                event_time="2026-05-06T01:20:00Z",
                actor="pm_001",
                outcome_review_id=outcome_review_id,
                state=state,
                reason_codes=["SOURCE_READY"],
            )
        ],
        retention_policy="DPM_OUTCOME_REVIEW_7Y",
        legal_hold_state="NONE",
        content_hash=content_hash,
        created_at=datetime(2026, 5, 6, 1, 20, tzinfo=timezone.utc),
        created_by="pm_001",
        correlation_id=f"corr_{outcome_review_id}",
        idempotency_key=idempotency_key,
    )


def test_in_memory_outcome_repository_persists_immutable_review_and_retention() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    review = _review()

    repository.save_outcome_review(
        review=review,
        retention_expires_at=datetime(2033, 5, 6, tzinfo=timezone.utc),
    )

    loaded = repository.get_outcome_review(outcome_review_id=review.outcome_review_id)
    assert loaded == review
    assert repository.get_outcome_review_by_idempotency(idempotency_key="idem_001") == review
    retention = repository.get_retention_metadata(outcome_review_id=review.outcome_review_id)
    assert retention is not None
    assert retention.retention_policy == "DPM_OUTCOME_REVIEW_7Y"
    assert retention.retention_expires_at == "2033-05-06T00:00:00+00:00"


def test_in_memory_outcome_repository_rejects_immutable_conflict() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    repository.save_outcome_review(review=_review(), retention_expires_at=None)

    with pytest.raises(DpmOutcomeReviewConflictError, match="IMMUTABLE"):
        repository.save_outcome_review(
            review=_review(content_hash="sha256:different"),
            retention_expires_at=None,
        )


def test_in_memory_outcome_repository_rejects_idempotency_conflict() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    repository.save_outcome_review(review=_review(), retention_expires_at=None)

    with pytest.raises(DpmOutcomeReviewConflictError, match="IDEMPOTENCY"):
        repository.save_outcome_review(
            review=_review(outcome_review_id="dor_002", content_hash="sha256:review-2"),
            retention_expires_at=None,
        )


def test_in_memory_outcome_repository_lists_filters_and_append_only_events() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    ready = _review(outcome_review_id="dor_ready", idempotency_key="idem_ready")
    blocked = _review(
        outcome_review_id="dor_blocked",
        content_hash="sha256:blocked",
        state="BLOCKED",
        idempotency_key="idem_blocked",
    )
    repository.save_outcome_review(review=ready, retention_expires_at=None)
    repository.save_outcome_review(review=blocked, retention_expires_at=None)
    repository.append_event(
        event=DpmOutcomeEvent(
            event_id="dor_ready_refreshed",
            event_type="OUTCOME_REVIEW_SOURCE_REFRESHED",
            event_time="2026-05-06T01:30:00Z",
            actor="system",
            outcome_review_id="dor_ready",
            state="READY",
            reason_codes=["SOURCE_REFRESHED"],
        )
    )

    assert [review.outcome_review_id for review in repository.list_outcome_reviews(state="READY")] == [
        "dor_ready"
    ]
    events = repository.list_events(outcome_review_id="dor_ready")
    assert [event.event_type for event in events] == [
        "OUTCOME_REVIEW_CREATED",
        "OUTCOME_REVIEW_SOURCE_REFRESHED",
    ]


def test_in_memory_outcome_repository_returns_deep_copies() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    repository.save_outcome_review(review=_review(), retention_expires_at=None)

    loaded = repository.get_outcome_review(outcome_review_id="dor_001")
    assert loaded is not None
    loaded.state = "BLOCKED"

    assert repository.get_outcome_review(outcome_review_id="dor_001").state == "READY"  # type: ignore[union-attr]
