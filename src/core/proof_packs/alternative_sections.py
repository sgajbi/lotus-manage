"""Selected-alternative, turnover, and eligibility proof-pack section builders."""

from typing import Any, cast

from src.core.construction.models import (
    ConstructionAlternative,
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
    ConstructionComparisonMetrics,
)
from src.core.models import ExcludedInstrument, RebalanceResult
from src.core.proof_packs.models import ProofPackSectionState
from src.core.proof_packs.section_state import lowest_section_state
from src.core.proof_packs.source_analytics import ProofPackSourceAnalytics

SectionPayload = tuple[ProofPackSectionState, str, dict[str, Any], dict[str, Any], list[str]]


def selected_alternative_section_payload(
    *,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
    selection: ConstructionAlternativeSelection | None,
) -> SectionPayload:
    if selected_alternative is None:
        return (
            "DEGRADED",
            "Direct-run proof pack has no selected construction alternative.",
            {},
            {},
            ["DPM_DIRECT_RUN_NO_SELECTED_ALTERNATIVE"],
        )
    return (
        selected_alternative_method_state(selected_alternative),
        "Selected construction alternative captured with method and trace evidence.",
        selected_alternative_facts(
            alternative_set=alternative_set,
            selected_alternative=selected_alternative,
            selection=selection,
        ),
        selected_alternative.comparison_metrics.model_dump(mode="json"),
        selected_alternative_reason_codes(selected_alternative),
    )


def selected_alternative_method_state(
    selected_alternative: ConstructionAlternative,
) -> ProofPackSectionState:
    if selected_alternative.method_status == "READY":
        return "READY"
    return cast(ProofPackSectionState, str(selected_alternative.method_status))


def selected_alternative_reason_codes(
    selected_alternative: ConstructionAlternative,
) -> list[str]:
    if selected_alternative.method_status == "READY":
        return []
    return ["DPM_SELECTED_METHOD_NOT_READY"]


def selected_alternative_facts(
    *,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative,
    selection: ConstructionAlternativeSelection | None,
) -> dict[str, Any]:
    return {
        "alternative_set_id": alternative_set.alternative_set_id if alternative_set else None,
        "selected_alternative_id": selected_alternative.alternative_id,
        "selection_id": selection.selection_id if selection else None,
        "method": selected_alternative.method,
        "method_status": selected_alternative.method_status,
        "summary": selected_alternative.summary,
        "objective_trace": [
            item.model_dump(mode="json") for item in selected_alternative.objective_trace
        ],
        "constraint_trace": [
            item.model_dump(mode="json") for item in selected_alternative.constraint_trace
        ],
    }


def turnover_and_cost_section_payload(
    *,
    selected_alternative: ConstructionAlternative | None,
    source_analytics: dict[str, ProofPackSourceAnalytics],
) -> SectionPayload:
    transaction_cost_context = source_analytics.get("transaction_cost")
    metrics = turnover_comparison_metrics(selected_alternative)
    if transaction_cost_context is None:
        return turnover_payload_without_transaction_cost_context(metrics)
    return turnover_payload_with_transaction_cost_context(
        metrics=metrics,
        transaction_cost_context=transaction_cost_context,
    )


def turnover_comparison_metrics(
    selected_alternative: ConstructionAlternative | None,
) -> dict[str, Any]:
    if selected_alternative is None:
        return {}
    return turnover_comparison_metrics_payload(selected_alternative.comparison_metrics)


def turnover_comparison_metrics_payload(
    comparison_metrics: ConstructionComparisonMetrics,
) -> dict[str, Any]:
    return comparison_metrics.model_dump(mode="json")


def turnover_base_posture(
    metrics: dict[str, Any],
) -> tuple[ProofPackSectionState, list[str]]:
    if metrics:
        return "READY", []
    return "DEGRADED", ["DPM_TURNOVER_COST_METRICS_MISSING"]


def turnover_payload_without_transaction_cost_context(
    metrics: dict[str, Any],
) -> SectionPayload:
    state, reason_codes = turnover_base_posture(metrics)
    if metrics:
        state = "DEGRADED"
        reason_codes.append("DPM_TRANSACTION_COST_AUTHORITY_CONTEXT_MISSING")
    return (
        state,
        "Turnover and cost evidence captured when construction metrics are available.",
        {},
        metrics,
        sorted(set(reason_codes)),
    )


def turnover_payload_with_transaction_cost_context(
    *,
    metrics: dict[str, Any],
    transaction_cost_context: ProofPackSourceAnalytics,
) -> SectionPayload:
    state, reason_codes = turnover_base_posture(metrics)
    return (
        lowest_section_state([state, transaction_cost_context.state]),
        "Turnover metrics and source-owned observed transaction-cost evidence are attached.",
        transaction_cost_context.facts,
        {**metrics, **transaction_cost_context.metrics},
        sorted(set([*reason_codes, *transaction_cost_context.reason_codes])),
    )


def eligibility_and_restrictions_section_payload(
    *,
    result: RebalanceResult,
    source_analytics: dict[str, ProofPackSourceAnalytics],
) -> SectionPayload:
    restriction_context = source_analytics.get("client_restriction")
    excluded = result.universe.excluded
    if restriction_context is not None:
        return eligibility_payload_with_restriction_context(
            restriction_context=restriction_context,
            excluded=excluded,
        )

    return eligibility_payload_from_universe_exclusions(excluded)


def eligibility_payload_with_restriction_context(
    *,
    restriction_context: ProofPackSourceAnalytics,
    excluded: list[ExcludedInstrument],
) -> SectionPayload:
    return (
        lowest_section_state(
            [
                restriction_context.state,
                eligibility_state_from_universe_exclusions(excluded),
            ]
        ),
        "Eligibility evidence and source-owned client restriction profile are attached.",
        {**restriction_context.facts, "excluded": excluded_instrument_facts(excluded)},
        {**restriction_context.metrics, "excluded_count": len(excluded)},
        eligibility_reason_codes(
            base_reason_codes=restriction_context.reason_codes,
            excluded=excluded,
        ),
    )


def eligibility_payload_from_universe_exclusions(
    excluded: list[ExcludedInstrument],
) -> SectionPayload:
    return (
        eligibility_state_from_universe_exclusions(excluded),
        "Eligibility and restriction evidence captured from source run universe.",
        {"excluded": excluded_instrument_facts(excluded)},
        {"excluded_count": len(excluded)},
        eligibility_reason_codes(base_reason_codes=[], excluded=excluded),
    )


def eligibility_state_from_universe_exclusions(
    excluded: list[ExcludedInstrument],
) -> ProofPackSectionState:
    return "PENDING_REVIEW" if excluded else "READY"


def excluded_instrument_facts(
    excluded: list[ExcludedInstrument],
) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in excluded]


def eligibility_reason_codes(
    *,
    base_reason_codes: list[str],
    excluded: list[ExcludedInstrument],
) -> list[str]:
    reason_codes = list(base_reason_codes)
    if excluded:
        reason_codes.append("DPM_UNIVERSE_EXCLUSIONS_PRESENT")
    return sorted(set(reason_codes))
