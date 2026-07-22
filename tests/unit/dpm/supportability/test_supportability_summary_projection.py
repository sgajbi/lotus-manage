from datetime import datetime, timedelta, timezone

from src.core.rebalance_runs.models import DpmSupportabilitySummaryData
from src.core.rebalance_runs.supportability_summary import (
    build_supportability_summary_response,
    resolve_freshness_bucket,
)


def _summary(
    *,
    run_count: int = 0,
    operation_count: int = 0,
    operation_status_counts: dict[str, int] | None = None,
    newest_run_created_at: datetime | None = None,
    newest_operation_created_at: datetime | None = None,
) -> DpmSupportabilitySummaryData:
    return DpmSupportabilitySummaryData(
        run_count=run_count,
        operation_count=operation_count,
        operation_status_counts=operation_status_counts or {},
        run_status_counts={"READY": run_count} if run_count else {},
        workflow_decision_count=2,
        workflow_action_counts={"APPROVE": 2},
        workflow_reason_code_counts={"REVIEW_APPROVED": 2},
        lineage_edge_count=4,
        oldest_run_created_at=newest_run_created_at,
        newest_run_created_at=newest_run_created_at,
        oldest_operation_created_at=newest_operation_created_at,
        newest_operation_created_at=newest_operation_created_at,
    )


def test_supportability_summary_response_projects_counts_timestamps_and_ready_posture():
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    summary = _summary(
        run_count=1,
        operation_count=1,
        operation_status_counts={"PENDING": 1},
        newest_run_created_at=now,
        newest_operation_created_at=now,
    )

    response = build_supportability_summary_response(
        summary=summary,
        store_backend="INMEMORY",
        retention_days=7,
        now=now,
    )

    assert response.store_backend == "INMEMORY"
    assert response.retention_days == 7
    assert response.run_count == 1
    assert response.operation_count == 1
    assert response.run_status_counts == {"READY": 1}
    assert response.operation_status_counts == {"PENDING": 1}
    assert response.workflow_decision_count == 2
    assert response.workflow_action_counts == {"APPROVE": 2}
    assert response.workflow_reason_code_counts == {"REVIEW_APPROVED": 2}
    assert response.lineage_edge_count == 4
    assert response.newest_run_created_at == "2026-02-20T12:00:00+00:00"
    assert response.newest_operation_created_at == "2026-02-20T12:00:00+00:00"
    assert response.producer_generated_at == "2026-02-20T12:00:00+00:00"
    assert response.temporal_identity_status == "store_wide"
    assert response.evidence_as_of_date is None
    assert response.supportability.state == "ready"
    assert response.supportability.reason == "supportability_summary_ready"
    assert response.supportability.freshness_bucket == "current"


def test_supportability_summary_fingerprint_includes_returned_source_refs():
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    summary = _summary(
        run_count=1,
        operation_count=1,
        newest_run_created_at=now,
        newest_operation_created_at=now,
    )

    first = build_supportability_summary_response(
        summary=summary,
        store_backend="INMEMORY",
        retention_days=7,
        now=now,
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        source_refs=[
            {
                "productId": "lotus-risk:MandateRiskHealthContext:v1",
                "as_of_date": "2026-02-20",
            }
        ],
    )
    second = build_supportability_summary_response(
        summary=summary,
        store_backend="INMEMORY",
        retention_days=7,
        now=now,
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        source_refs=[
            {
                "productId": "lotus-performance:MandatePerformanceHealthContext:v1",
                "as_of_date": "2026-02-20",
            }
        ],
    )

    assert first.source_batch_fingerprint.startswith("sha256:")
    assert second.source_batch_fingerprint.startswith("sha256:")
    assert first.source_batch_fingerprint != second.source_batch_fingerprint


def test_supportability_summary_confirms_portfolio_scope_for_operation_only_batch():
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    response = build_supportability_summary_response(
        summary=_summary(
            operation_count=1,
            operation_status_counts={"ACCEPTED": 1},
            newest_operation_created_at=now,
        ),
        store_backend="INMEMORY",
        retention_days=7,
        now=now,
        portfolio_id="PB_SG_GLOBAL_BAL_001",
    )

    assert response.portfolio_scope_confirmed is True
    assert response.supportability.portfolio_scope_confirmed is True
    assert response.temporal_identity_status == "missing_source_evidence"
    assert response.supportability.state == "degraded"


def test_supportability_summary_binds_producer_temporal_identity_into_fingerprint():
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    later = datetime(2026, 2, 20, 12, 1, tzinfo=timezone.utc)
    summary = _summary(
        run_count=1,
        newest_run_created_at=now,
    )
    source_refs = [
        {
            "productId": "lotus-risk:MandateRiskHealthContext:v1",
            "as_of_date": "2026-02-19",
            "generated_at": "2026-02-20T09:00:00+00:00",
            "content_hash": "sha256:risk",
        },
        {
            "productId": "lotus-performance:MandatePerformanceHealthContext:v1",
            "as_of_date": "2026-02-19",
            "generated_at": "2026-02-20T09:00:00+00:00",
            "content_hash": "sha256:performance",
        },
    ]

    first = build_supportability_summary_response(
        summary=summary,
        store_backend="INMEMORY",
        retention_days=7,
        now=now,
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        source_refs=source_refs,
    )
    second = build_supportability_summary_response(
        summary=summary,
        store_backend="INMEMORY",
        retention_days=7,
        now=later,
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        source_refs=source_refs,
    )

    assert first.temporal_identity_status == "available"
    assert first.evidence_as_of_date == "2026-02-19"
    assert first.producer_generated_at == "2026-02-20T12:00:00+00:00"
    assert first.supportability.temporal_identity_status == "available"
    assert first.supportability.evidence_as_of_date == "2026-02-19"
    assert first.source_batch_fingerprint != second.source_batch_fingerprint


def test_supportability_summary_degrades_mixed_source_as_of_dates():
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    response = build_supportability_summary_response(
        summary=_summary(run_count=1, newest_run_created_at=now),
        store_backend="INMEMORY",
        retention_days=7,
        now=now,
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        source_refs=[
            {
                "productId": "lotus-risk:MandateRiskHealthContext:v1",
                "as_of_date": "2026-02-19",
            },
            {
                "productId": "lotus-performance:MandatePerformanceHealthContext:v1",
                "as_of_date": "2026-02-18",
            },
        ],
    )

    assert response.temporal_identity_status == "mixed_source_as_of"
    assert response.evidence_as_of_date is None
    assert response.supportability.state == "degraded"
    assert response.supportability.reason == "supportability_summary_degraded"


def test_supportability_summary_response_classifies_empty_stale_and_degraded_posture():
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)

    empty = build_supportability_summary_response(
        summary=_summary(),
        store_backend="INMEMORY",
        retention_days=0,
        now=now,
    )
    assert empty.supportability.state == "empty"
    assert empty.supportability.reason == "supportability_summary_empty"
    assert empty.supportability.freshness_bucket == "unknown"

    stale = build_supportability_summary_response(
        summary=_summary(
            run_count=1,
            newest_run_created_at=now - timedelta(days=2),
        ),
        store_backend="INMEMORY",
        retention_days=0,
        now=now,
    )
    assert stale.supportability.state == "stale"
    assert stale.supportability.reason == "supportability_summary_stale"
    assert stale.supportability.freshness_bucket == "stale"

    degraded = build_supportability_summary_response(
        summary=_summary(
            operation_count=1,
            operation_status_counts={"FAILED": 1},
            newest_operation_created_at=now,
        ),
        store_backend="INMEMORY",
        retention_days=0,
        now=now,
    )
    assert degraded.supportability.state == "degraded"
    assert degraded.supportability.reason == "supportability_summary_degraded"
    assert degraded.supportability.freshness_bucket == "current"


def test_supportability_freshness_bucket_accepts_naive_source_timestamps():
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    summary = _summary(
        run_count=1,
        newest_run_created_at=datetime(2026, 2, 19, 12, 0),
    )

    assert resolve_freshness_bucket(summary=summary, now=now) == "same_day"
