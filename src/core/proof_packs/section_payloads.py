"""Generic proof-pack section payload helpers."""

from typing import Any

from src.core.construction.models import ConstructionAlternative
from src.core.models import RebalanceResult
from src.core.proof_packs.models import ProofPackSectionState
from src.core.proof_packs.source_analytics import (
    ProofPackAnalyticsFamily,
    ProofPackSourceAnalytics,
)

SectionPayload = tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]]


def source_analytics_section_payload(
    *,
    source_analytics: dict[str, ProofPackSourceAnalytics],
    family: ProofPackAnalyticsFamily,
    missing_summary: str,
    missing_reason_code: str,
    sort_reason_codes: bool = False,
) -> SectionPayload:
    analytics = source_analytics.get(family)
    if analytics is None:
        return ("DEGRADED", missing_summary, {}, {}, [missing_reason_code])
    reason_codes = list(analytics.reason_codes)
    if sort_reason_codes:
        reason_codes = sorted(set(reason_codes))
    return (
        analytics.state,
        analytics.summary,
        analytics.facts,
        analytics.metrics,
        reason_codes,
    )


def adapter_section_payload(
    *,
    summary: str,
    adapter_contract: str,
) -> SectionPayload:
    return (
        "READY",
        summary,
        {"adapter_contract": adapter_contract},
        {},
        [],
    )


def source_readiness_section_payload(
    *,
    result: RebalanceResult | None,
) -> SectionPayload:
    if result is None:
        return ("BLOCKED", "No source run is available.", {}, {}, ["DPM_SOURCE_RUN_MISSING"])

    source_state = result.lineage.source_supportability_state
    reason_codes = (
        [] if source_state in {None, "READY", "ready"} else ["DPM_SOURCE_READINESS_DEGRADED"]
    )
    return (
        "READY" if not reason_codes else "DEGRADED",
        "Source readiness captured from run lineage.",
        {
            "input_mode": result.lineage.input_mode,
            "source_system": result.lineage.source_system,
            "source_supportability_state": source_state,
        },
        {},
        reason_codes,
    )


def decision_summary_section_payload(
    *,
    result: RebalanceResult | None,
    selected_alternative: ConstructionAlternative | None,
    reason: str | None,
    created_by: str,
) -> SectionPayload:
    reason_codes = [] if reason else ["DPM_PROOF_PACK_REASON_MISSING"]
    return (
        "READY" if reason else "DEGRADED",
        "Decision evidence assembled from manage run and actor rationale.",
        {
            "actor": created_by,
            "reason": reason,
            "source_run_status": result.status if result is not None else None,
            "selected_alternative_id": (
                selected_alternative.alternative_id if selected_alternative else None
            ),
        },
        {},
        reason_codes,
    )
