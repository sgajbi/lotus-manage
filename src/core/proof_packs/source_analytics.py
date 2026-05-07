"""Source-owned risk/performance analytics extraction for proof packs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import ValidationError

from src.core.common.canonical import hash_canonical_payload
from src.core.construction.models import (
    AuthoritativePerformanceContext,
    AuthoritativeRiskContext,
    ConstructionAlternative,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.proof_packs.models import DpmProofPackSourceRef, ProofPackSectionState

ProofPackAnalyticsFamily = Literal["risk", "performance"]


@dataclass(frozen=True)
class ProofPackSourceAnalytics:
    family: ProofPackAnalyticsFamily
    state: ProofPackSectionState
    summary: str
    facts: dict[str, Any]
    metrics: dict[str, Any]
    reason_codes: list[str]
    source_ref: DpmProofPackSourceRef
    source_hash_key: str
    content_hash: str


def source_analytics_for_alternative(
    *,
    alternative: ConstructionAlternative | None,
    family: ProofPackAnalyticsFamily,
) -> ProofPackSourceAnalytics | None:
    """Return source-owned analytics attached to a selected construction alternative."""

    if alternative is None:
        return None
    authority_context = _mapping(alternative.diagnostics.get("authority_context"))
    source_context = _mapping(authority_context.get(f"{family}_context"))
    if not source_context:
        return None
    if family == "risk":
        return _risk_source_analytics(source_context)
    return _performance_source_analytics(source_context)


def _risk_source_analytics(source_context: dict[str, Any]) -> ProofPackSourceAnalytics | None:
    try:
        context = AuthoritativeRiskContext.model_validate(source_context)
    except ValidationError:
        return None
    payload = context.model_dump(mode="json", exclude_none=True)
    content_hash = hash_canonical_payload(payload)
    reason_codes = list(context.reason_codes)
    if context.supportability_status != ConstructionMethodStatus.READY and not reason_codes:
        reason_codes.append("DPM_RISK_AUTHORITY_CONTEXT_DEGRADED")
    source_ref = _source_ref(
        family="risk",
        source_system=context.source_system,
        source_type=context.source_product_name or "RiskMetricsReport",
        source_id=context.source_id or content_hash,
        supportability_state=str(context.supportability_status),
        content_hash=context.content_hash or content_hash,
    )
    return ProofPackSourceAnalytics(
        family="risk",
        state=_section_state(context.supportability_status),
        summary="Risk impact is attached from source-owned risk authority context.",
        facts={
            "source_system": context.source_system,
            "source_product_name": context.source_product_name or "RiskMetricsReport",
            "source_product_version": context.source_product_version,
            "source_id": context.source_id,
            "issuer_coverage_status": context.issuer_coverage_status,
        },
        metrics={
            key: value
            for key, value in {
                "tracking_error": context.tracking_error,
                "concentration_breaches": context.concentration_breaches,
                "concentration_hhi_delta": context.concentration_hhi_delta,
                "top_position_weight_proposed": context.top_position_weight_proposed,
            }.items()
            if value is not None
        },
        reason_codes=reason_codes,
        source_ref=source_ref,
        source_hash_key="risk_context",
        content_hash=context.content_hash or content_hash,
    )


def _performance_source_analytics(
    source_context: dict[str, Any],
) -> ProofPackSourceAnalytics | None:
    try:
        context = AuthoritativePerformanceContext.model_validate(source_context)
    except ValidationError:
        return None
    payload = context.model_dump(mode="json", exclude_none=True)
    content_hash = hash_canonical_payload(payload)
    reason_codes = list(context.reason_codes)
    if context.supportability_status != ConstructionMethodStatus.READY and not reason_codes:
        reason_codes.append("DPM_PERFORMANCE_CONTEXT_DEGRADED")
    source_ref = _source_ref(
        family="performance",
        source_system=context.source_system,
        source_type=context.source_product_name or "PerformanceBenchmarkContext",
        source_id=context.source_id or content_hash,
        supportability_state=str(context.supportability_status),
        content_hash=context.content_hash or content_hash,
    )
    return ProofPackSourceAnalytics(
        family="performance",
        state=_section_state(context.supportability_status),
        summary="Performance context is attached from source-owned performance authority context.",
        facts={
            "source_system": context.source_system,
            "source_product_name": context.source_product_name or "PerformanceBenchmarkContext",
            "source_product_version": context.source_product_version,
            "source_id": context.source_id,
            "benchmark_id": context.benchmark_id,
        },
        metrics={
            key: value
            for key, value in {
                "active_return": context.active_return,
                "underperformance_flag": context.underperformance_flag,
            }.items()
            if value is not None
        },
        reason_codes=reason_codes,
        source_ref=source_ref,
        source_hash_key="performance_context",
        content_hash=context.content_hash or content_hash,
    )


def _source_ref(
    *,
    family: ProofPackAnalyticsFamily,
    source_system: str,
    source_type: str,
    source_id: str,
    supportability_state: str,
    content_hash: str,
) -> DpmProofPackSourceRef:
    return DpmProofPackSourceRef(
        source_system=source_system or f"lotus-{family}",
        source_type=source_type,
        source_id=source_id,
        supportability_state=supportability_state,
        content_hash=content_hash,
    )


def _section_state(status: ConstructionMethodStatus) -> ProofPackSectionState:
    if status == ConstructionMethodStatus.READY:
        return "READY"
    if status == ConstructionMethodStatus.BLOCKED:
        return "BLOCKED"
    if status == ConstructionMethodStatus.PENDING_REVIEW:
        return "PENDING_REVIEW"
    return "DEGRADED"


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
