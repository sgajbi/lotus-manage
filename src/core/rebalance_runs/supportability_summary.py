import hashlib
from datetime import datetime, timezone

from src.core.rebalance_runs.models import (
    DpmActionRegisterSupportability,
    DpmFreshnessBucket,
    DpmSupportabilityReason,
    DpmSupportabilityState,
    DpmSupportabilitySummaryData,
    DpmSupportabilitySummaryResponse,
)


def build_supportability_summary_response(
    *,
    summary: DpmSupportabilitySummaryData,
    store_backend: str,
    retention_days: int,
    now: datetime,
    portfolio_id: str | None = None,
    source_refs: list[dict[str, object]] | None = None,
) -> DpmSupportabilitySummaryResponse:
    portfolio_scope_confirmed = portfolio_id is not None and summary.run_count > 0
    return DpmSupportabilitySummaryResponse(
        store_backend=store_backend,
        retention_days=retention_days,
        run_count=summary.run_count,
        operation_count=summary.operation_count,
        operation_status_counts=summary.operation_status_counts,
        run_status_counts=summary.run_status_counts,
        workflow_decision_count=summary.workflow_decision_count,
        workflow_action_counts=summary.workflow_action_counts,
        workflow_reason_code_counts=summary.workflow_reason_code_counts,
        lineage_edge_count=summary.lineage_edge_count,
        portfolio_id=portfolio_id,
        portfolio_scope_confirmed=portfolio_scope_confirmed,
        source_batch_fingerprint=_source_batch_fingerprint(
            summary=summary,
            store_backend=store_backend,
            portfolio_id=portfolio_id,
        ),
        source_refs=source_refs or [],
        oldest_run_created_at=(
            summary.oldest_run_created_at.isoformat()
            if summary.oldest_run_created_at is not None
            else None
        ),
        newest_run_created_at=(
            summary.newest_run_created_at.isoformat()
            if summary.newest_run_created_at is not None
            else None
        ),
        oldest_operation_created_at=(
            summary.oldest_operation_created_at.isoformat()
            if summary.oldest_operation_created_at is not None
            else None
        ),
        newest_operation_created_at=(
            summary.newest_operation_created_at.isoformat()
            if summary.newest_operation_created_at is not None
            else None
        ),
        supportability=resolve_action_register_supportability(
            summary=summary,
            now=now,
            portfolio_id=portfolio_id,
            portfolio_scope_confirmed=portfolio_scope_confirmed,
        ),
    )


def resolve_action_register_supportability(
    *,
    summary: DpmSupportabilitySummaryData,
    now: datetime,
    portfolio_id: str | None = None,
    portfolio_scope_confirmed: bool = False,
) -> DpmActionRegisterSupportability:
    freshness_bucket = resolve_freshness_bucket(summary=summary, now=now)
    has_records = summary.run_count > 0 or summary.operation_count > 0
    state: DpmSupportabilityState
    reason: DpmSupportabilityReason
    if not has_records:
        state = "empty"
        reason = "supportability_summary_empty"
    elif freshness_bucket == "stale":
        state = "stale"
        reason = "supportability_summary_stale"
    elif summary.operation_status_counts.get("FAILED", 0) > 0:
        state = "degraded"
        reason = "supportability_summary_degraded"
    else:
        state = "ready"
        reason = "supportability_summary_ready"
    return DpmActionRegisterSupportability(
        state=state,
        reason=reason,
        freshness_bucket=freshness_bucket,
        run_count=summary.run_count,
        operation_count=summary.operation_count,
        workflow_decision_count=summary.workflow_decision_count,
        portfolio_id=portfolio_id,
        portfolio_scope_confirmed=portfolio_scope_confirmed,
    )


def resolve_freshness_bucket(
    *,
    summary: DpmSupportabilitySummaryData,
    now: datetime,
) -> DpmFreshnessBucket:
    candidates = [
        value
        for value in (
            summary.newest_run_created_at,
            summary.newest_operation_created_at,
        )
        if value is not None
    ]
    if not candidates:
        return "unknown"
    newest = max(candidates)
    if newest.tzinfo is None:
        newest = newest.replace(tzinfo=timezone.utc)
    resolved_now = now
    if resolved_now.tzinfo is None:
        resolved_now = resolved_now.replace(tzinfo=timezone.utc)
    age_days = (resolved_now.date() - newest.astimezone(timezone.utc).date()).days
    if age_days <= 0:
        return "current"
    if age_days <= 1:
        return "same_day"
    return "stale"


def _source_batch_fingerprint(
    *,
    summary: DpmSupportabilitySummaryData,
    store_backend: str,
    portfolio_id: str | None,
) -> str:
    parts = [
        "lotus-manage",
        "PortfolioActionRegister:v1",
        store_backend,
        portfolio_id or "store-wide",
        str(summary.run_count),
        str(summary.operation_count),
        str(summary.workflow_decision_count),
        str(summary.lineage_edge_count),
        summary.newest_run_created_at.isoformat() if summary.newest_run_created_at else "",
        summary.newest_operation_created_at.isoformat()
        if summary.newest_operation_created_at
        else "",
    ]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
