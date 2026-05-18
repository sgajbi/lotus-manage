"""Source-owned risk/performance analytics extraction for proof packs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

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
    if family == "risk":
        return _risk_source_analytics(source_context)
    if family == "performance":
        return _performance_source_analytics(source_context)
    if family == "transaction_cost":
        return _transaction_cost_source_analytics(source_context)
    if family == "client_restriction":
        return _client_restriction_source_analytics(source_context)
    if family == "sustainability_preference":
        return _sustainability_preference_source_analytics(source_context)
    return _regime_stress_source_analytics(source_context)


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


def _transaction_cost_source_analytics(
    source_context: dict[str, Any],
) -> ProofPackSourceAnalytics | None:
    try:
        context = AuthoritativeTransactionCostContext.model_validate(source_context)
    except ValidationError:
        return None
    payload = context.model_dump(mode="json", exclude_none=True)
    content_hash = hash_canonical_payload(payload)
    reason_codes = list(context.reason_codes)
    if context.supportability_status != ConstructionMethodStatus.READY and not reason_codes:
        reason_codes.append("DPM_TRANSACTION_COST_CONTEXT_DEGRADED")
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
        facts={
            "source_system": context.source_system,
            "source_product_name": context.source_product_name,
            "source_product_version": context.source_product_version,
            "source_id": context.source_id,
            "as_of_date": context.as_of_date.isoformat(),
            "window_start_date": context.window_start_date.isoformat(),
            "window_end_date": context.window_end_date.isoformat(),
            "missing_security_ids": context.missing_security_ids,
            "curve_points": [point.model_dump(mode="json") for point in context.curve_points[:10]],
        },
        metrics={
            "returned_curve_point_count": context.returned_curve_point_count,
            "represented_observation_count": sum(
                point.observation_count for point in context.curve_points
            ),
        },
        reason_codes=reason_codes,
        source_ref=source_ref,
        source_hash_key="transaction_cost_context",
        content_hash=context.content_hash or content_hash,
    )


def _client_restriction_source_analytics(
    source_context: dict[str, Any],
) -> ProofPackSourceAnalytics | None:
    try:
        context = AuthoritativeClientRestrictionContext.model_validate(source_context)
    except ValidationError:
        return None
    payload = context.model_dump(mode="json", exclude_none=True)
    content_hash = hash_canonical_payload(payload)
    reason_codes = list(context.reason_codes)
    if context.supportability_status != ConstructionMethodStatus.READY and not reason_codes:
        reason_codes.append("DPM_CLIENT_RESTRICTION_CONTEXT_DEGRADED")
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
        reason_codes=reason_codes,
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
    reason_codes = list(context.reason_codes)
    if context.supportability_status != ConstructionMethodStatus.READY and not reason_codes:
        reason_codes.append("DPM_SUSTAINABILITY_PREFERENCE_CONTEXT_DEGRADED")
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
        reason_codes=reason_codes,
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
        facts={
            "source_system": context.source_system,
            "source_product_name": "RegimeScenarioPackEvaluation",
            "source_product_version": context.source_product_version,
            "scenario_pack_id": context.scenario_pack_id,
            "cio_approval_ref": context.cio_approval_ref,
            "approved_by": context.approved_by,
            "approved_at": context.approved_at,
            "effective_from": context.effective_from.isoformat()
            if context.effective_from is not None
            else None,
            "effective_to": context.effective_to.isoformat()
            if context.effective_to is not None
            else None,
            "applicable_portfolio_ids": context.applicable_portfolio_ids,
            "applicable_mandate_ids": context.applicable_mandate_ids,
            "approval_evidence_projected": context.cio_approval_ref is not None,
            "effective_period_projected": context.effective_from is not None
            or context.effective_to is not None,
            "applicability_evidence_projected": bool(
                context.applicable_portfolio_ids or context.applicable_mandate_ids
            ),
            "scenario_evidence_posture": evidence_posture["facts"],
        },
        metrics={
            "worst_case_loss_pct": context.worst_case_loss_pct,
            "maximum_allowed_loss_pct": context.maximum_allowed_loss_pct,
        },
        reason_codes=sorted(reason_codes),
        source_ref=source_ref,
        source_hash_key="regime_stress_context",
        content_hash=content_hash,
    )


def _regime_stress_evidence_posture(
    context: AuthoritativeRegimeStressContext,
) -> dict[str, Any]:
    reason_codes: set[str] = set()
    posture_facts: dict[str, str] = {
        "cio_approval": "PROJECTED" if context.cio_approval_ref else "MISSING",
        "effective_period": (
            "PROJECTED"
            if context.effective_from is not None or context.effective_to is not None
            else "MISSING"
        ),
        "applicability": (
            "PROJECTED"
            if context.applicable_portfolio_ids or context.applicable_mandate_ids
            else "MISSING"
        ),
        "source_reason_posture": "READY",
    }
    posture_states: list[ProofPackSectionState] = ["READY"]
    if not context.cio_approval_ref:
        reason_codes.add("REGIME_SCENARIO_CIO_APPROVAL_EVIDENCE_MISSING")
        posture_states.append("PENDING_REVIEW")
    if context.effective_from is None and context.effective_to is None:
        reason_codes.add("REGIME_SCENARIO_EFFECTIVE_PERIOD_EVIDENCE_MISSING")
        posture_states.append("PENDING_REVIEW")
    if not context.applicable_portfolio_ids and not context.applicable_mandate_ids:
        reason_codes.add("REGIME_SCENARIO_APPLICABILITY_EVIDENCE_MISSING")
        posture_states.append("PENDING_REVIEW")

    source_reason_codes = {reason.upper() for reason in context.reason_codes}
    if any(
        "INAPPLICABLE" in reason or "NOT_APPLICABLE" in reason for reason in source_reason_codes
    ):
        reason_codes.add("REGIME_SCENARIO_APPLICABILITY_NOT_CONFIRMED")
        posture_facts["source_reason_posture"] = "INAPPLICABLE"
        posture_states.append("BLOCKED")
    elif any(
        marker in reason
        for reason in source_reason_codes
        for marker in ["STALE", "EXPIRED", "OUTSIDE_EFFECTIVE", "EFFECTIVE_PERIOD_EXCEPTION"]
    ):
        reason_codes.add("REGIME_SCENARIO_EFFECTIVE_PERIOD_EXCEPTION")
        posture_facts["source_reason_posture"] = "EFFECTIVE_PERIOD_EXCEPTION"
        posture_states.append("DEGRADED")
    elif any("CONTRIBUTION" in reason and "PARTIAL" in reason for reason in source_reason_codes):
        reason_codes.add("REGIME_SCENARIO_CONTRIBUTION_EVIDENCE_PARTIAL")
        posture_facts["source_reason_posture"] = "CONTRIBUTION_PARTIAL"
        posture_states.append("PENDING_REVIEW")

    return {
        "state": _lowest_section_state(posture_states),
        "reason_codes": sorted(reason_codes),
        "facts": posture_facts,
    }


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
