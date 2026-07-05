from __future__ import annotations

from datetime import datetime, timezone

from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import DpmMandateHealthSnapshot


_PRODUCT_ROUTES = {
    "lotus-performance:MandatePerformanceHealthContext:v1": ("/performance/mandate-health-context"),
    "lotus-risk:MandateRiskHealthContext:v1": "/analytics/risk/mandate-health-context",
}


def source_refs_for_portfolio_mandate_health(
    *,
    repository: DpmMandateRepository,
    portfolio_id: str | None,
    now: datetime,
) -> list[dict[str, object]]:
    if portfolio_id is None:
        return []
    mandate = repository.get_latest_mandate_by_portfolio(portfolio_id=portfolio_id)
    if mandate is None:
        return []
    snapshot = repository.get_latest_health_snapshot(mandate_id=mandate.mandate_id)
    if snapshot is None:
        return []
    return [
        payload
        for source_ref in snapshot.source_analytics_posture.source_context_refs
        if (payload := _source_context_ref_payload(source_ref, snapshot=snapshot, now=now))
        is not None
    ]


def _source_context_ref_payload(
    source_ref: str,
    *,
    snapshot: DpmMandateHealthSnapshot,
    now: datetime,
) -> dict[str, object] | None:
    parts = source_ref.split(":")
    if len(parts) < 4:
        return None
    product_id = ":".join(parts[:3])
    content_hash = ":".join(parts[3:])
    if product_id not in _PRODUCT_ROUTES or not content_hash.startswith("sha256:"):
        return None
    return {
        "productId": product_id,
        "product_version": parts[2],
        "route": _PRODUCT_ROUTES[product_id],
        "content_hash": content_hash,
        "generated_at": snapshot.calculated_at.isoformat(),
        "freshness": _freshness_bucket(snapshot.calculated_at, now),
        "data_quality_status": snapshot.health_state.value.lower(),
    }


def _freshness_bucket(calculated_at: datetime, now: datetime) -> str:
    resolved_calculated_at = _aware_utc(calculated_at)
    resolved_now = _aware_utc(now)
    age_days = (resolved_now.date() - resolved_calculated_at.date()).days
    if age_days <= 1:
        return "current"
    return "stale"


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
