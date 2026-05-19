"""Source-owned analytics aggregation for rebalance waves."""

from __future__ import annotations

from collections import Counter
from typing import Literal, cast

from src.core.construction.models import ConstructionAlternativeSet
from src.core.waves.models import (
    DpmRebalanceWaveItem,
    DpmWaveSourceAnalyticsSummary,
    DpmWaveSourceRef,
)


def build_source_analytics_from_alternative_set(
    alternative_set: ConstructionAlternativeSet,
) -> dict[str, dict[str, object]]:
    summaries: dict[str, dict[str, object]] = {}
    for family in ("risk", "performance"):
        candidates: list[dict[str, object]] = []
        for alternative in alternative_set.alternatives:
            candidate = _source_analytics_from_alternative(
                alternative_set=alternative_set,
                alternative_diagnostics=alternative.diagnostics,
                family=family,
            )
            if candidate is not None:
                candidates.append(candidate)
        if candidates:
            summaries[family] = _merge_item_source_analytics(candidates)
    return summaries


def aggregate_wave_source_analytics(
    items: list[DpmRebalanceWaveItem],
) -> list[DpmWaveSourceAnalyticsSummary]:
    summaries: list[DpmWaveSourceAnalyticsSummary] = []
    for family in ("risk", "performance"):
        item_summaries = [
            _mapping(_mapping(item.diagnostics.get("source_analytics")).get(family))
            for item in items
        ]
        item_summaries = [summary for summary in item_summaries if summary]
        if not item_summaries:
            continue
        state_counts = Counter(
            str(summary.get("supportability_state", "DEGRADED")).upper()
            for summary in item_summaries
        )
        refs = [
            ref
            for summary in item_summaries
            for ref in cast(list[dict[str, object]], summary.get("source_refs", []))
        ]
        measures: dict[str, list[str]] = {}
        for summary in item_summaries:
            for measure, values in _mapping(summary.get("source_measures")).items():
                measure_values = measures.setdefault(str(measure), [])
                measure_values.extend(str(value) for value in cast(list[object], values))
        summaries.append(
            DpmWaveSourceAnalyticsSummary(
                source_family=cast(Literal["RISK", "PERFORMANCE"], family.upper()),
                supportability_state=_worst_source_state(list(state_counts)),
                item_count=len(item_summaries),
                ready_item_count=state_counts.get("READY", 0),
                degraded_item_count=state_counts.get("DEGRADED", 0),
                blocked_item_count=state_counts.get("BLOCKED", 0),
                pending_review_item_count=state_counts.get("PENDING_REVIEW", 0),
                source_systems=sorted(
                    {
                        str(source_system)
                        for summary in item_summaries
                        for source_system in cast(list[object], summary.get("source_systems", []))
                    }
                ),
                source_refs=[
                    DpmWaveSourceRef.model_validate(ref) for ref in _dedupe_source_ref_dicts(refs)
                ],
                reason_codes=sorted(
                    {
                        str(reason_code)
                        for summary in item_summaries
                        for reason_code in cast(list[object], summary.get("reason_codes", []))
                    }
                ),
                source_measures={
                    measure: sorted(set(values)) for measure, values in sorted(measures.items())
                },
            )
        )
    return summaries


def _source_analytics_from_alternative(
    *,
    alternative_set: ConstructionAlternativeSet,
    alternative_diagnostics: dict[str, object],
    family: str,
) -> dict[str, object] | None:
    authority_context = _mapping(alternative_diagnostics.get("authority_context"))
    source_context = _mapping(authority_context.get(f"{family}_context"))
    if not source_context:
        return None
    enrichment_summary = _mapping(alternative_diagnostics.get("enrichment_summary"))
    status_key = f"{family}_status"
    supportability_state = str(
        source_context.get("supportability_status")
        or enrichment_summary.get(status_key)
        or "DEGRADED"
    ).upper()
    source_system = str(source_context.get("source_system") or f"lotus-{family}")
    source_ref = _analytics_source_ref(
        source_context=source_context,
        source_system=source_system,
        family=family,
        fallback_id=alternative_set.alternative_set_id,
    )
    return {
        "supportability_state": supportability_state,
        "source_systems": [source_system],
        "source_refs": [source_ref.model_dump(mode="json")],
        "reason_codes": _string_list(source_context.get("reason_codes"))
        or _string_list(enrichment_summary.get("reason_codes")),
        "source_measures": _source_measures(source_context=source_context, family=family),
    }


def _merge_item_source_analytics(
    candidates: list[dict[str, object]],
) -> dict[str, object]:
    states = [str(candidate.get("supportability_state", "DEGRADED")) for candidate in candidates]
    refs = [
        ref
        for candidate in candidates
        for ref in cast(list[dict[str, object]], candidate.get("source_refs", []))
    ]
    measures: dict[str, list[str]] = {}
    for candidate in candidates:
        for measure, values in _mapping(candidate.get("source_measures")).items():
            measure_values = measures.setdefault(str(measure), [])
            measure_values.extend(str(value) for value in cast(list[object], values))
    return {
        "supportability_state": _worst_source_state(states),
        "source_systems": sorted(
            {
                str(source_system)
                for candidate in candidates
                for source_system in cast(list[object], candidate.get("source_systems", []))
            }
        ),
        "source_refs": _dedupe_source_ref_dicts(refs),
        "reason_codes": sorted(
            {
                str(reason_code)
                for candidate in candidates
                for reason_code in cast(list[object], candidate.get("reason_codes", []))
            }
        ),
        "source_measures": {
            measure: sorted(set(values)) for measure, values in sorted(measures.items())
        },
    }


def _analytics_source_ref(
    *,
    source_context: dict[str, object],
    source_system: str,
    family: str,
    fallback_id: str,
) -> DpmWaveSourceRef:
    source_type = str(
        source_context.get("source_product_name")
        or ("RISK_AUTHORITY_CONTEXT" if family == "risk" else "PERFORMANCE_AUTHORITY_CONTEXT")
    )
    source_version = source_context.get("source_product_version")
    return DpmWaveSourceRef(
        source_system=source_system,
        source_type=source_type,
        source_id=str(source_context.get("source_id") or fallback_id),
        source_version=str(source_version) if source_version is not None else None,
        supportability_state=str(source_context.get("supportability_status") or "DEGRADED"),
        content_hash=(
            str(source_context.get("content_hash")) if source_context.get("content_hash") else None
        ),
    )


def _source_measures(
    *,
    source_context: dict[str, object],
    family: str,
) -> dict[str, list[str]]:
    measure_names = (
        (
            "tracking_error",
            "concentration_breaches",
            "concentration_hhi_delta",
            "top_position_weight_proposed",
            "issuer_coverage_status",
        )
        if family == "risk"
        else ("benchmark_id", "active_return", "underperformance_flag")
    )
    return {
        measure: [str(source_context[measure])]
        for measure in measure_names
        if source_context.get(measure) is not None
    }


def _mapping(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _dedupe_source_ref_dicts(refs: list[dict[str, object]]) -> list[dict[str, object]]:
    deduped: dict[tuple[str, str, str, str | None], dict[str, object]] = {}
    for ref in refs:
        validated = DpmWaveSourceRef.model_validate(ref)
        deduped[
            (
                validated.source_system,
                validated.source_type,
                validated.source_id,
                validated.source_version,
            )
        ] = validated.model_dump(mode="json")
    return list(deduped.values())


def _worst_source_state(states: list[str]) -> str:
    order = {"BLOCKED": 0, "DEGRADED": 1, "PENDING_REVIEW": 2, "READY": 3}
    normalized = [state.upper() for state in states if state]
    if not normalized:
        return "DEGRADED"
    return min(normalized, key=lambda state: order.get(state, 1))
