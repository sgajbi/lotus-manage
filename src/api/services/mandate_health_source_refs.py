from __future__ import annotations

from datetime import datetime, timezone
import hashlib

from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import (
    DpmMandateHealthSnapshot,
    DpmMandateHealthSourceContextMetadata,
)


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
    metadata_by_ref = {
        metadata.source_ref: metadata
        for metadata in snapshot.source_analytics_posture.source_context_metadata
    }
    payloads: list[dict[str, object]] = []
    for source_ref in snapshot.source_analytics_posture.source_context_refs:
        payload = _source_context_ref_payload(
            source_ref,
            snapshot=snapshot,
            now=now,
            metadata=metadata_by_ref.get(source_ref),
        )
        if payload is None:
            payload = _unavailable_source_context_ref_payload(
                source_ref,
                snapshot=snapshot,
                now=now,
            )
        payloads.append(payload)
    return payloads


def _source_context_ref_payload(
    source_ref: str,
    *,
    snapshot: DpmMandateHealthSnapshot,
    now: datetime,
    metadata: DpmMandateHealthSourceContextMetadata | None = None,
) -> dict[str, object] | None:
    parts = source_ref.split(":")
    if len(parts) < 4:
        return None
    product_id = ":".join(parts[:3])
    content_hash = ":".join(parts[3:])
    if product_id not in _PRODUCT_ROUTES or not _is_non_empty_sha256_ref(content_hash):
        return None
    payload: dict[str, object] = {
        "productId": product_id,
        "product_version": parts[2],
        "route": _PRODUCT_ROUTES[product_id],
        "content_hash": content_hash,
        "generated_at": _aware_utc(snapshot.calculated_at).isoformat(),
        "freshness": _freshness_bucket(snapshot.calculated_at, now),
        "source_ref_status": "available",
    }
    if metadata is not None and metadata.as_of_date is not None:
        payload["as_of_date"] = metadata.as_of_date.isoformat()
    return payload


def _unavailable_source_context_ref_payload(
    source_ref: str,
    *,
    snapshot: DpmMandateHealthSnapshot,
    now: datetime,
) -> dict[str, object]:
    product_id = "unavailable"
    product_version = "unavailable"
    parts = source_ref.split(":")
    if len(parts) >= 3:
        candidate_product_id = ":".join(parts[:3])
        if candidate_product_id in _PRODUCT_ROUTES:
            product_id = candidate_product_id
            product_version = parts[2]
    return {
        "productId": product_id,
        "product_version": product_version,
        "route": _PRODUCT_ROUTES.get(product_id, "unavailable"),
        "content_hash": "unavailable",
        "generated_at": _aware_utc(snapshot.calculated_at).isoformat(),
        "freshness": _freshness_bucket(snapshot.calculated_at, now),
        "source_ref_status": "unavailable",
        "reason": "malformed_or_unsupported_source_ref",
        "source_ref_fingerprint": _source_ref_fingerprint(source_ref),
    }


def _source_ref_fingerprint(source_ref: str) -> str:
    return f"sha256:{hashlib.sha256(source_ref.encode('utf-8')).hexdigest()}"


def _is_non_empty_sha256_ref(value: str) -> bool:
    return value.startswith("sha256:") and bool(value.removeprefix("sha256:").strip())


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
