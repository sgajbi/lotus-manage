"""Source-owned risk/performance analytics extraction for proof packs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

from pydantic import ValidationError

from src.core.common.canonical import hash_canonical_payload
from src.core.construction.models import (
    AuthoritativeClientRestrictionContext,
    AuthoritativePerformanceContext,
    AuthoritativeRegimeStressContext,
    AuthoritativeRiskContext,
    AuthoritativeSustainabilityPreferenceContext,
    AuthoritativeTransactionCostContext,
    ConstructionAlternative,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.proof_packs.models import DpmProofPackSourceRef, ProofPackSectionState

_RegimeStressSourceReasonPosture = Literal[
    "READY",
    "INAPPLICABLE",
    "EFFECTIVE_PERIOD_EXCEPTION",
    "CONTRIBUTION_PARTIAL",
]
_INAPPLICABLE_REASON_MARKERS = ("INAPPLICABLE", "NOT_APPLICABLE")
_EFFECTIVE_PERIOD_REASON_MARKERS = (
    "STALE",
    "EXPIRED",
    "OUTSIDE_EFFECTIVE",
    "EFFECTIVE_PERIOD_EXCEPTION",
)
_MISSING_REGIME_STRESS_GOVERNANCE_REASONS: dict[str, str] = {
    "cio_approval": "REGIME_SCENARIO_CIO_APPROVAL_EVIDENCE_MISSING",
    "effective_period": "REGIME_SCENARIO_EFFECTIVE_PERIOD_EVIDENCE_MISSING",
    "applicability": "REGIME_SCENARIO_APPLICABILITY_EVIDENCE_MISSING",
}
_REGIME_SOURCE_REASON_POSTURE_EFFECTS: dict[
    _RegimeStressSourceReasonPosture,
    tuple[ProofPackSectionState, str],
] = {
    "INAPPLICABLE": ("BLOCKED", "REGIME_SCENARIO_APPLICABILITY_NOT_CONFIRMED"),
    "EFFECTIVE_PERIOD_EXCEPTION": (
        "DEGRADED",
        "REGIME_SCENARIO_EFFECTIVE_PERIOD_EXCEPTION",
    ),
    "CONTRIBUTION_PARTIAL": (
        "PENDING_REVIEW",
        "REGIME_SCENARIO_CONTRIBUTION_EVIDENCE_PARTIAL",
    ),
}
_RegimeStressSourceReasonClassifier = tuple[
    _RegimeStressSourceReasonPosture,
    Callable[[str], bool],
]

ProofPackAnalyticsFamily = Literal[
    "risk",
    "performance",
    "transaction_cost",
    "client_restriction",
    "sustainability_preference",
    "regime_stress",
]


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


_SourceAnalyticsBuilder = Callable[[dict[str, Any]], ProofPackSourceAnalytics | None]


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
    return source_analytics_for_context(source_context=source_context, family=family)


def source_analytics_for_context(
    *,
    source_context: dict[str, Any],
    family: ProofPackAnalyticsFamily,
) -> ProofPackSourceAnalytics | None:
    """Return source-owned analytics from an explicit authority context payload."""

    if not source_context:
        return None
    return _SOURCE_ANALYTICS_BUILDERS[family](source_context)


def _risk_source_analytics(source_context: dict[str, Any]) -> ProofPackSourceAnalytics | None:
    try:
        context = AuthoritativeRiskContext.model_validate(source_context)
    except ValidationError:
        return None
    payload = context.model_dump(mode="json", exclude_none=True)
    content_hash = hash_canonical_payload(payload)
    return ProofPackSourceAnalytics(
        family="risk",
        state=_section_state(context.supportability_status),
        summary="Risk impact is attached from source-owned risk authority context.",
        facts=_risk_source_facts(context),
        metrics=_risk_source_metrics(context),
        reason_codes=_authority_reason_codes(
            context=context,
            degraded_reason="DPM_RISK_AUTHORITY_CONTEXT_DEGRADED",
        ),
        source_ref=_authority_source_ref(
            family="risk",
            source_system=context.source_system,
            source_type=context.source_product_name or "RiskMetricsReport",
            source_id=context.source_id,
            supportability_status=context.supportability_status,
            content_hash=context.content_hash,
            fallback_hash=content_hash,
        ),
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
    return ProofPackSourceAnalytics(
        family="performance",
        state=_section_state(context.supportability_status),
        summary="Performance context is attached from source-owned performance authority context.",
        facts=_performance_source_facts(context),
        metrics=_performance_source_metrics(context),
        reason_codes=_authority_reason_codes(
            context=context,
            degraded_reason="DPM_PERFORMANCE_CONTEXT_DEGRADED",
        ),
        source_ref=_authority_source_ref(
            family="performance",
            source_system=context.source_system,
            source_type=context.source_product_name or "PerformanceBenchmarkContext",
            source_id=context.source_id,
            supportability_status=context.supportability_status,
            content_hash=context.content_hash,
            fallback_hash=content_hash,
        ),
        source_hash_key="performance_context",
        content_hash=context.content_hash or content_hash,
    )


def _authority_reason_codes(
    *,
    context: AuthoritativeRiskContext | AuthoritativePerformanceContext,
    degraded_reason: str,
) -> list[str]:
    reason_codes = list(context.reason_codes)
    if context.supportability_status != ConstructionMethodStatus.READY and not reason_codes:
        reason_codes.append(degraded_reason)
    return reason_codes


def _authority_source_ref(
    *,
    family: ProofPackAnalyticsFamily,
    source_system: str,
    source_type: str,
    source_id: str | None,
    supportability_status: ConstructionMethodStatus,
    content_hash: str | None,
    fallback_hash: str,
) -> DpmProofPackSourceRef:
    return _source_ref(
        family=family,
        source_system=source_system,
        source_type=source_type,
        source_id=source_id or fallback_hash,
        supportability_state=str(supportability_status),
        content_hash=content_hash or fallback_hash,
    )


def _risk_source_facts(context: AuthoritativeRiskContext) -> dict[str, Any]:
    return {
        "source_system": context.source_system,
        "source_product_name": context.source_product_name or "RiskMetricsReport",
        "source_product_version": context.source_product_version,
        "source_id": context.source_id,
        "issuer_coverage_status": context.issuer_coverage_status,
    }


def _risk_source_metrics(context: AuthoritativeRiskContext) -> dict[str, Any]:
    return _present_metrics(
        {
            "tracking_error": context.tracking_error,
            "maximum_drawdown": context.maximum_drawdown,
            "average_drawdown": context.average_drawdown,
            "stress_loss_pct": context.stress_loss_pct,
            "stress_contribution_count": context.stress_contribution_count,
            "attribution_contributor_count": context.attribution_contributor_count,
            "concentration_breaches": context.concentration_breaches,
            "concentration_hhi_delta": context.concentration_hhi_delta,
            "top_position_weight_proposed": context.top_position_weight_proposed,
        }
    )


def _performance_source_facts(context: AuthoritativePerformanceContext) -> dict[str, Any]:
    return {
        "source_system": context.source_system,
        "source_product_name": context.source_product_name or "PerformanceBenchmarkContext",
        "source_product_version": context.source_product_version,
        "source_id": context.source_id,
        "benchmark_id": context.benchmark_id,
    }


def _performance_source_metrics(context: AuthoritativePerformanceContext) -> dict[str, Any]:
    return _present_metrics(
        {
            "active_return": context.active_return,
            "benchmark_relative_return": context.benchmark_relative_return,
            "contribution_total_return": context.contribution_total_return,
            "attribution_allocation": context.attribution_allocation,
            "attribution_selection": context.attribution_selection,
            "attribution_interaction": context.attribution_interaction,
            "currency_attribution_total": context.currency_attribution_total,
            "underperformance_flag": context.underperformance_flag,
        }
    )


def _present_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metrics.items() if value is not None}


def _transaction_cost_source_analytics(
    source_context: dict[str, Any],
) -> ProofPackSourceAnalytics | None:
    try:
        context = AuthoritativeTransactionCostContext.model_validate(source_context)
    except ValidationError:
        return None
    payload = context.model_dump(mode="json", exclude_none=True)
    content_hash = hash_canonical_payload(payload)
    source_ref = _source_ref(
        family="transaction_cost",
        source_system=context.source_system,
        source_type=context.source_product_name,
        source_id=context.source_id or content_hash,
        supportability_state=str(context.supportability_status),
        content_hash=context.content_hash or content_hash,
    )
    return ProofPackSourceAnalytics(
        family="transaction_cost",
        state=_section_state(context.supportability_status),
        summary=(
            "Observed transaction-cost evidence is attached from source-owned "
            "TransactionCostCurve:v1."
        ),
        facts=_transaction_cost_source_facts(context),
        metrics=_transaction_cost_source_metrics(context),
        reason_codes=_degraded_context_reason_codes(
            supportability_status=context.supportability_status,
            reason_codes=context.reason_codes,
            degraded_reason="DPM_TRANSACTION_COST_CONTEXT_DEGRADED",
        ),
        source_ref=source_ref,
        source_hash_key="transaction_cost_context",
        content_hash=context.content_hash or content_hash,
    )


def _transaction_cost_source_facts(
    context: AuthoritativeTransactionCostContext,
) -> dict[str, Any]:
    return {
        "source_system": context.source_system,
        "source_product_name": context.source_product_name,
        "source_product_version": context.source_product_version,
        "source_id": context.source_id,
        "as_of_date": context.as_of_date.isoformat(),
        "window_start_date": context.window_start_date.isoformat(),
        "window_end_date": context.window_end_date.isoformat(),
        "missing_security_ids": context.missing_security_ids,
        "curve_points": [point.model_dump(mode="json") for point in context.curve_points[:10]],
    }


def _transaction_cost_source_metrics(
    context: AuthoritativeTransactionCostContext,
) -> dict[str, int]:
    return {
        "returned_curve_point_count": context.returned_curve_point_count,
        "represented_observation_count": sum(
            point.observation_count for point in context.curve_points
        ),
    }


def _client_restriction_source_analytics(
    source_context: dict[str, Any],
) -> ProofPackSourceAnalytics | None:
    try:
        context = AuthoritativeClientRestrictionContext.model_validate(source_context)
    except ValidationError:
        return None
    payload = context.model_dump(mode="json", exclude_none=True)
    content_hash = hash_canonical_payload(payload)
    source_ref = _source_ref(
        family="client_restriction",
        source_system=context.source_system,
        source_type=context.source_product_name,
        source_id=context.source_id or content_hash,
        supportability_state=str(context.supportability_status),
        content_hash=context.content_hash or content_hash,
    )
    return ProofPackSourceAnalytics(
        family="client_restriction",
        state=_section_state(context.supportability_status),
        summary="Client restriction evidence is attached from source-owned ClientRestrictionProfile:v1.",
        facts={
            "source_system": context.source_system,
            "source_product_name": context.source_product_name,
            "source_product_version": context.source_product_version,
            "source_id": context.source_id,
            "portfolio_id": context.portfolio_id,
            "client_id": context.client_id,
            "mandate_id": context.mandate_id,
            "as_of_date": context.as_of_date.isoformat(),
            "missing_data_families": context.missing_data_families,
            "restrictions": [
                restriction.model_dump(mode="json") for restriction in context.restrictions[:20]
            ],
        },
        metrics={"restriction_count": context.restriction_count},
        reason_codes=_degraded_context_reason_codes(
            supportability_status=context.supportability_status,
            reason_codes=context.reason_codes,
            degraded_reason="DPM_CLIENT_RESTRICTION_CONTEXT_DEGRADED",
        ),
        source_ref=source_ref,
        source_hash_key="client_restriction_context",
        content_hash=context.content_hash or content_hash,
    )


def _sustainability_preference_source_analytics(
    source_context: dict[str, Any],
) -> ProofPackSourceAnalytics | None:
    try:
        context = AuthoritativeSustainabilityPreferenceContext.model_validate(source_context)
    except ValidationError:
        return None
    payload = context.model_dump(mode="json", exclude_none=True)
    content_hash = hash_canonical_payload(payload)
    source_ref = _source_ref(
        family="sustainability_preference",
        source_system=context.source_system,
        source_type=context.source_product_name,
        source_id=context.source_id or content_hash,
        supportability_state=str(context.supportability_status),
        content_hash=context.content_hash or content_hash,
    )
    return ProofPackSourceAnalytics(
        family="sustainability_preference",
        state=_section_state(context.supportability_status),
        summary=(
            "Sustainability preference evidence is attached from source-owned "
            "SustainabilityPreferenceProfile:v1."
        ),
        facts={
            "source_system": context.source_system,
            "source_product_name": context.source_product_name,
            "source_product_version": context.source_product_version,
            "source_id": context.source_id,
            "portfolio_id": context.portfolio_id,
            "client_id": context.client_id,
            "mandate_id": context.mandate_id,
            "as_of_date": context.as_of_date.isoformat(),
            "missing_data_families": context.missing_data_families,
            "preferences": [
                preference.model_dump(mode="json") for preference in context.preferences[:20]
            ],
        },
        metrics={"preference_count": context.preference_count},
        reason_codes=_degraded_context_reason_codes(
            supportability_status=context.supportability_status,
            reason_codes=context.reason_codes,
            degraded_reason="DPM_SUSTAINABILITY_PREFERENCE_CONTEXT_DEGRADED",
        ),
        source_ref=source_ref,
        source_hash_key="sustainability_preference_context",
        content_hash=context.content_hash or content_hash,
    )


def _regime_stress_source_analytics(
    source_context: dict[str, Any],
) -> ProofPackSourceAnalytics | None:
    try:
        context = AuthoritativeRegimeStressContext.model_validate(source_context)
    except ValidationError:
        return None
    payload = context.model_dump(mode="json", exclude_none=True)
    content_hash = hash_canonical_payload(payload)
    evidence_posture = _regime_stress_evidence_posture(context)
    reason_codes = {*context.reason_codes, *evidence_posture["reason_codes"]}
    if context.supportability_status in {
        ConstructionMethodStatus.DEGRADED,
        ConstructionMethodStatus.BLOCKED,
    }:
        reason_codes.add("DPM_REGIME_STRESS_CONTEXT_DEGRADED")
    source_ref = _source_ref(
        family="regime_stress",
        source_system=context.source_system,
        source_type="RegimeScenarioPackEvaluation",
        source_id=context.scenario_pack_id or content_hash,
        supportability_state=str(context.supportability_status),
        content_hash=content_hash,
    )
    return ProofPackSourceAnalytics(
        family="regime_stress",
        state=_lowest_section_state(
            [
                _section_state(context.supportability_status),
                evidence_posture["state"],
            ]
        ),
        summary=(
            "Scenario/regime evidence is attached from source-owned "
            "RegimeScenarioPackEvaluation:v1."
        ),
        facts=_regime_stress_source_facts(context=context, evidence_posture=evidence_posture),
        metrics=_regime_stress_source_metrics(context),
        reason_codes=sorted(reason_codes),
        source_ref=source_ref,
        source_hash_key="regime_stress_context",
        content_hash=content_hash,
    )


_SOURCE_ANALYTICS_BUILDERS: dict[ProofPackAnalyticsFamily, _SourceAnalyticsBuilder] = {
    "risk": _risk_source_analytics,
    "performance": _performance_source_analytics,
    "transaction_cost": _transaction_cost_source_analytics,
    "client_restriction": _client_restriction_source_analytics,
    "sustainability_preference": _sustainability_preference_source_analytics,
    "regime_stress": _regime_stress_source_analytics,
}


def _degraded_context_reason_codes(
    *,
    supportability_status: ConstructionMethodStatus,
    reason_codes: list[str],
    degraded_reason: str,
) -> list[str]:
    resolved_reason_codes = list(reason_codes)
    if supportability_status != ConstructionMethodStatus.READY and not resolved_reason_codes:
        resolved_reason_codes.append(degraded_reason)
    return resolved_reason_codes


def _regime_stress_source_facts(
    *,
    context: AuthoritativeRegimeStressContext,
    evidence_posture: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_system": context.source_system,
        "source_product_name": "RegimeScenarioPackEvaluation",
        "source_product_version": context.source_product_version,
        "scenario_pack_id": context.scenario_pack_id,
        "cio_approval_status": context.cio_approval_status,
        "cio_approval_ref": context.cio_approval_ref,
        "approved_by": context.approved_by,
        "approved_at": context.approved_at,
        "effective_from": context.effective_from.isoformat()
        if context.effective_from is not None
        else None,
        "effective_to": context.effective_to.isoformat()
        if context.effective_to is not None
        else None,
        "effective_period_status": context.effective_period_status,
        "applicability_status": context.applicability_status,
        "applicability_scope": context.applicability_scope,
        "portfolio_applicability_ref": context.portfolio_applicability_ref,
        "methodology_ref": context.methodology_ref,
        "applicable_portfolio_ids": context.applicable_portfolio_ids,
        "applicable_mandate_ids": context.applicable_mandate_ids,
        "approval_evidence_projected": context.cio_approval_ref is not None,
        "effective_period_projected": context.effective_from is not None
        or context.effective_to is not None,
        "applicability_evidence_projected": _regime_applicability_projected(context),
        "scenario_evidence_posture": evidence_posture["facts"],
    }


def _regime_stress_source_metrics(
    context: AuthoritativeRegimeStressContext,
) -> dict[str, Any]:
    return {
        "worst_case_loss_pct": context.worst_case_loss_pct,
        "maximum_allowed_loss_pct": context.maximum_allowed_loss_pct,
    }


def _regime_stress_evidence_posture(
    context: AuthoritativeRegimeStressContext,
) -> dict[str, Any]:
    reason_codes: set[str] = set()
    posture_facts = _regime_stress_governance_posture_facts(context)
    posture_states: list[ProofPackSectionState] = ["READY"]

    missing_governance_evidence = _missing_regime_stress_governance_evidence(context)
    missing_governance_reason_codes = _missing_regime_stress_governance_reason_codes(
        missing_governance_evidence
    )
    reason_codes.update(missing_governance_reason_codes)
    posture_states.extend(["PENDING_REVIEW"] * len(missing_governance_reason_codes))

    source_reason_posture = _regime_source_reason_posture(context.reason_codes)
    posture_facts["source_reason_posture"] = source_reason_posture
    source_reason_effect = _regime_source_reason_posture_effect(source_reason_posture)
    if source_reason_effect is not None:
        source_state, source_reason_code = source_reason_effect
        reason_codes.add(source_reason_code)
        posture_states.append(source_state)

    return {
        "state": _lowest_section_state(posture_states),
        "reason_codes": sorted(reason_codes),
        "facts": posture_facts,
    }


def _missing_regime_stress_governance_reason_codes(
    missing_governance_evidence: set[str],
) -> set[str]:
    return {
        reason_code
        for evidence_key, reason_code in _MISSING_REGIME_STRESS_GOVERNANCE_REASONS.items()
        if evidence_key in missing_governance_evidence
    }


def _regime_source_reason_posture_effect(
    source_reason_posture: _RegimeStressSourceReasonPosture,
) -> tuple[ProofPackSectionState, str] | None:
    return _REGIME_SOURCE_REASON_POSTURE_EFFECTS.get(source_reason_posture)


def _regime_stress_governance_posture_facts(
    context: AuthoritativeRegimeStressContext,
) -> dict[str, str]:
    return {
        "cio_approval": "PROJECTED" if context.cio_approval_ref else "MISSING",
        "effective_period": (
            "PROJECTED"
            if context.effective_from is not None or context.effective_to is not None
            else "MISSING"
        ),
        "applicability": "PROJECTED" if _regime_applicability_projected(context) else "MISSING",
        "source_reason_posture": "READY",
    }


def _missing_regime_stress_governance_evidence(
    context: AuthoritativeRegimeStressContext,
) -> set[str]:
    missing_evidence: set[str] = set()
    if not context.cio_approval_ref:
        missing_evidence.add("cio_approval")
    if context.effective_from is None and context.effective_to is None:
        missing_evidence.add("effective_period")
    if not _regime_applicability_projected(context):
        missing_evidence.add("applicability")
    return missing_evidence


def _regime_source_reason_posture(
    reason_codes: list[str],
) -> _RegimeStressSourceReasonPosture:
    normalized_reason_codes = _normalized_reason_codes(reason_codes)
    for posture, matches in _regime_source_reason_classifiers():
        if any(matches(reason) for reason in normalized_reason_codes):
            return posture
    return "READY"


def _regime_source_reason_classifiers() -> tuple[_RegimeStressSourceReasonClassifier, ...]:
    return (
        ("INAPPLICABLE", _is_inapplicable_regime_reason),
        ("EFFECTIVE_PERIOD_EXCEPTION", _is_effective_period_regime_reason),
        ("CONTRIBUTION_PARTIAL", _is_partial_contribution_regime_reason),
    )


def _normalized_reason_codes(reason_codes: list[str]) -> set[str]:
    return {reason.upper() for reason in reason_codes}


def _is_inapplicable_regime_reason(reason: str) -> bool:
    return _reason_contains_any_marker(reason=reason, markers=_INAPPLICABLE_REASON_MARKERS)


def _is_effective_period_regime_reason(reason: str) -> bool:
    return _reason_contains_any_marker(
        reason=reason,
        markers=_EFFECTIVE_PERIOD_REASON_MARKERS,
    )


def _is_partial_contribution_regime_reason(reason: str) -> bool:
    return "CONTRIBUTION" in reason and "PARTIAL" in reason


def _reason_contains_any_marker(*, reason: str, markers: tuple[str, ...]) -> bool:
    return any(marker in reason for marker in markers)


def _regime_applicability_projected(context: AuthoritativeRegimeStressContext) -> bool:
    return bool(
        context.applicable_portfolio_ids
        or context.applicable_mandate_ids
        or context.applicability_scope
        or context.portfolio_applicability_ref
        or context.applicability_status
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


def _lowest_section_state(states: list[ProofPackSectionState]) -> ProofPackSectionState:
    order: dict[ProofPackSectionState, int] = {
        "READY": 0,
        "PENDING_REVIEW": 1,
        "DEGRADED": 2,
        "BLOCKED": 3,
    }
    return max(states, key=lambda state: order[state])


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
