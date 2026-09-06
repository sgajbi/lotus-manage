from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from src.core.mandate_models import (
    DIMENSION_WEIGHTS,
    DpmMandateDimensionScore,
    DpmMandateHealthInput,
    DpmMandateHealthReason,
    DpmMandateHealthSnapshot,
    DpmMandateHealthSourceContextMetadata,
    DpmMandateHealthSourceAnalyticsPosture,
    DpmMandateSourceHealthContext,
    MandateHealthDimension,
    MandateHealthState,
    MandateRecommendedAction,
    MonitoringSeverity,
    default_source_analytics_posture as _default_source_analytics_posture,
)


def calculate_mandate_health(input_: DpmMandateHealthInput) -> DpmMandateHealthSnapshot:
    dimension_scores = _mandate_health_dimension_scores(input_)
    health_state = _mandate_health_state(dimension_scores)
    top_reasons = _top_mandate_health_reasons(dimension_scores)
    recommended_action = _overall_recommended_action(health_state, top_reasons)
    return DpmMandateHealthSnapshot(
        health_snapshot_id=_mandate_health_snapshot_id(input_),
        mandate_id=input_.twin.mandate_id,
        portfolio_id=input_.twin.portfolio_id,
        as_of_date=input_.twin.as_of_date,
        calculated_at=datetime.now(timezone.utc),
        health_score=_weighted_mandate_health_score(dimension_scores),
        health_state=health_state,
        dimension_scores=dimension_scores,
        top_reasons=top_reasons,
        recommended_action=recommended_action,
        source_readiness_state=input_.source_readiness_state,
        evidence_refs=_mandate_health_evidence_refs(input_),
        source_analytics_posture=_source_analytics_posture(input_),
    )


def _mandate_health_dimension_scores(
    input_: DpmMandateHealthInput,
) -> list[DpmMandateDimensionScore]:
    return [
        _score_source_readiness(input_),
        _score_allocation_drift(input_),
        _score_risk_drift(input_),
        _score_cash_liquidity(input_),
        _score_tax_turnover(input_),
        _score_eligibility_restrictions(input_),
        _score_performance_attention(input_),
        _score_workflow_readiness(input_),
        _score_review_cadence(input_),
        _score_model_freshness(input_),
    ]


def _weighted_mandate_health_score(
    dimension_scores: list[DpmMandateDimensionScore],
) -> int:
    weighted = sum(
        Decimal(score.score) * Decimal(score.weight) for score in dimension_scores
    ) / Decimal("100")
    return int(weighted.quantize(Decimal("1"), ROUND_HALF_UP))


def _mandate_health_state(
    dimension_scores: list[DpmMandateDimensionScore],
) -> MandateHealthState:
    if any(score.state == MandateHealthState.BLOCKED for score in dimension_scores):
        return MandateHealthState.BLOCKED
    if any(score.state == MandateHealthState.PENDING_REVIEW for score in dimension_scores):
        return MandateHealthState.PENDING_REVIEW
    return MandateHealthState.READY


def _top_mandate_health_reasons(
    dimension_scores: list[DpmMandateDimensionScore],
) -> list[DpmMandateHealthReason]:
    reasons = [_reason_from_score(score) for score in dimension_scores if score.score < 100]
    reasons.sort(key=lambda reason: _severity_rank(reason.severity), reverse=True)
    return reasons[:5]


def _mandate_health_snapshot_id(input_: DpmMandateHealthInput) -> str:
    as_of = input_.twin.as_of_date.strftime("%Y%m%d")
    return f"mh_{as_of}_{input_.twin.portfolio_id.lower()}"


def _mandate_health_evidence_refs(input_: DpmMandateHealthInput) -> list[str]:
    return [
        lineage.source_record_id
        for lineage in input_.twin.source_lineage
        if lineage.source_record_id
    ]


def _source_analytics_posture(
    input_: DpmMandateHealthInput,
) -> DpmMandateHealthSourceAnalyticsPosture:
    source_context_refs: list[str] = []
    source_context_metadata: list[DpmMandateHealthSourceContextMetadata] = []
    reason_codes = list(_default_source_analytics_posture().reason_codes)
    if input_.risk_health_context is not None:
        risk_ref = _source_health_context_ref(input_.risk_health_context)
        source_context_refs.append(risk_ref)
        source_context_metadata.append(
            _source_health_context_metadata(input_.risk_health_context, source_ref=risk_ref)
        )
        reason_codes.append("MANDATE_RISK_HEALTH_CONTEXT_SOURCE_PRODUCT_PRESERVED")
    if input_.performance_health_context is not None:
        performance_ref = _source_health_context_ref(input_.performance_health_context)
        source_context_refs.append(performance_ref)
        source_context_metadata.append(
            _source_health_context_metadata(
                input_.performance_health_context,
                source_ref=performance_ref,
            )
        )
        reason_codes.append("MANDATE_PERFORMANCE_HEALTH_CONTEXT_SOURCE_PRODUCT_PRESERVED")
    return _default_source_analytics_posture().model_copy(
        update={
            "risk_tracking_error_supplied": input_.tracking_error is not None
            or input_.risk_health_context is not None,
            "performance_attention_signal_supplied": input_.performance_under_review
            or input_.performance_health_context is not None,
            "risk_health_context_supplied": input_.risk_health_context is not None,
            "performance_health_context_supplied": input_.performance_health_context is not None,
            "source_context_refs": source_context_refs,
            "source_context_metadata": source_context_metadata,
            "reason_codes": reason_codes,
        }
    )


def _source_health_context_ref(context: DpmMandateSourceHealthContext) -> str:
    return (
        f"{context.source_system}:{context.source_product_name}:"
        f"{context.source_product_version}:{context.request_fingerprint}"
    )


def _source_health_context_metadata(
    context: DpmMandateSourceHealthContext,
    *,
    source_ref: str,
) -> DpmMandateHealthSourceContextMetadata:
    return DpmMandateHealthSourceContextMetadata(
        source_ref=source_ref,
        source_system=context.source_system,
        source_product_name=context.source_product_name,
        source_product_version=context.source_product_version,
        request_fingerprint=context.request_fingerprint,
        as_of_date=context.as_of_date,
    )


def _score_from_penalty(penalty: Decimal) -> int:
    bounded_penalty = min(max(penalty, Decimal("0")), Decimal("100"))
    return int((Decimal("100") - bounded_penalty).quantize(Decimal("1"), ROUND_HALF_UP))


def _ready_score(dimension: MandateHealthDimension) -> DpmMandateDimensionScore:
    return DpmMandateDimensionScore(
        dimension=dimension,
        weight=DIMENSION_WEIGHTS[dimension],
        score=100,
        state=MandateHealthState.READY,
        reason_code=f"{dimension.value}_READY",
    )


def _attention_score(
    *,
    dimension: MandateHealthDimension,
    score: int,
    state: MandateHealthState,
    reason_code: str,
    measured_value: Optional[Decimal | str | int] = None,
    threshold_value: Optional[Decimal | str | int] = None,
    evidence_refs: Optional[list[str]] = None,
) -> DpmMandateDimensionScore:
    return DpmMandateDimensionScore(
        dimension=dimension,
        weight=DIMENSION_WEIGHTS[dimension],
        score=max(0, min(score, 100)),
        state=state,
        reason_code=reason_code,
        measured_value=measured_value,
        threshold_value=threshold_value,
        evidence_refs=evidence_refs or [],
    )


def _score_source_readiness(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    if (
        input_.source_readiness_state in {"INCOMPLETE", "UNAVAILABLE"}
        or input_.missing_source_families
    ):
        return _attention_score(
            dimension=MandateHealthDimension.SOURCE_READINESS,
            score=0,
            state=MandateHealthState.BLOCKED,
            reason_code="DPM_SOURCE_INCOMPLETE",
            measured_value=input_.source_readiness_state,
            threshold_value="READY",
        )
    if input_.source_readiness_state == "DEGRADED" or input_.stale_source_families:
        return _attention_score(
            dimension=MandateHealthDimension.SOURCE_READINESS,
            score=70,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="DPM_SOURCE_STALE",
            measured_value=input_.source_readiness_state,
            threshold_value="READY",
        )
    return _ready_score(MandateHealthDimension.SOURCE_READINESS)


def _score_allocation_drift(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    if not input_.current_weights or not input_.target_weights:
        return _attention_score(
            dimension=MandateHealthDimension.ALLOCATION_DRIFT,
            score=85,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="ALLOCATION_DRIFT_NOT_ASSESSED",
        )
    default_band = Decimal("0.025")
    max_drift = max(
        (
            abs(input_.current_weights.get(instrument_id, Decimal("0")) - target_weight)
            for instrument_id, target_weight in input_.target_weights.items()
        ),
        default=Decimal("0"),
    )
    if max_drift <= default_band:
        return _ready_score(MandateHealthDimension.ALLOCATION_DRIFT)
    score = _score_from_penalty((max_drift - default_band) * Decimal("1000"))
    return _attention_score(
        dimension=MandateHealthDimension.ALLOCATION_DRIFT,
        score=score,
        state=MandateHealthState.PENDING_REVIEW,
        reason_code="ALLOCATION_DRIFT",
        measured_value=max_drift,
        threshold_value=default_band,
    )


def _score_risk_drift(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    source_score = _score_source_health_context(
        context=input_.risk_health_context,
        dimension=MandateHealthDimension.RISK_DRIFT,
        attention_reason_code="SOURCE_RISK_HEALTH_ATTENTION",
        unavailable_reason_code="SOURCE_RISK_HEALTH_UNAVAILABLE",
    )
    if source_score is not None:
        return source_score
    if input_.tracking_error is None or input_.twin.constraints.max_tracking_error is None:
        return _ready_score(MandateHealthDimension.RISK_DRIFT)
    if input_.tracking_error <= input_.twin.constraints.max_tracking_error:
        return _ready_score(MandateHealthDimension.RISK_DRIFT)
    return _attention_score(
        dimension=MandateHealthDimension.RISK_DRIFT,
        score=65,
        state=MandateHealthState.PENDING_REVIEW,
        reason_code="TRACKING_ERROR_ABOVE_LIMIT",
        measured_value=input_.tracking_error,
        threshold_value=input_.twin.constraints.max_tracking_error,
    )


def _score_cash_liquidity(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    constraints = input_.twin.constraints
    # A limit the mandate never stated cannot be breached (issue #664).
    if (
        constraints.cash_band_min_weight is not None
        and input_.cash_weight < constraints.cash_band_min_weight
    ):
        return _attention_score(
            dimension=MandateHealthDimension.CASH_LIQUIDITY,
            score=60,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="CASH_BELOW_BAND",
            measured_value=input_.cash_weight,
            threshold_value=constraints.cash_band_min_weight,
        )
    if (
        constraints.cash_band_max_weight is not None
        and input_.cash_weight > constraints.cash_band_max_weight
    ):
        return _attention_score(
            dimension=MandateHealthDimension.CASH_LIQUIDITY,
            score=75,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="CASH_ABOVE_BAND",
            measured_value=input_.cash_weight,
            threshold_value=constraints.cash_band_max_weight,
        )
    if input_.projected_net_cashflow is not None and input_.projected_net_cashflow < Decimal("0"):
        return _attention_score(
            dimension=MandateHealthDimension.CASH_LIQUIDITY,
            score=70,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="PROJECTED_CASHFLOW_PRESSURE",
            measured_value=input_.projected_net_cashflow,
            threshold_value=0,
        )
    if constraints.cash_band_min_weight is None or constraints.cash_band_max_weight is None:
        # No breach fired, but the mandate cash band this dimension exists
        # to check was never sourced (issue #664). Unknown is not READY.
        return _attention_score(
            dimension=MandateHealthDimension.CASH_LIQUIDITY,
            score=70,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="CASH_BAND_NOT_SOURCED",
            measured_value=input_.cash_weight,
            threshold_value=None,
        )
    return _ready_score(MandateHealthDimension.CASH_LIQUIDITY)


def _score_tax_turnover(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    if input_.tax_lot_missing_security_ids:
        return _attention_score(
            dimension=MandateHealthDimension.TAX_TURNOVER,
            score=40,
            state=MandateHealthState.BLOCKED,
            reason_code="TAX_LOTS_INCOMPLETE",
            measured_value=len(input_.tax_lot_missing_security_ids),
            threshold_value=0,
        )
    if (
        input_.turnover_budget_used is not None
        and input_.twin.constraints.turnover_budget is not None
        and input_.turnover_budget_used >= input_.twin.constraints.turnover_budget * Decimal("0.8")
    ):
        return _attention_score(
            dimension=MandateHealthDimension.TAX_TURNOVER,
            score=70,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="TURNOVER_BUDGET_NEAR_LIMIT",
            measured_value=input_.turnover_budget_used,
            threshold_value=input_.twin.constraints.turnover_budget,
        )
    if input_.twin.constraints.turnover_budget is None:
        # Same rule for the turnover budget: unassessable is not healthy.
        return _attention_score(
            dimension=MandateHealthDimension.TAX_TURNOVER,
            score=70,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="TURNOVER_BUDGET_NOT_SOURCED",
            measured_value=input_.turnover_budget_used,
            threshold_value=None,
        )
    return _ready_score(MandateHealthDimension.TAX_TURNOVER)


def _score_eligibility_restrictions(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    restricted = set(input_.restricted_held_instruments)
    restricted.update(input_.restricted_target_instruments)
    restricted.update(
        instrument_id
        for instrument_id in input_.current_weights
        if instrument_id in set(input_.twin.constraints.restricted_instruments)
    )
    if restricted:
        return _attention_score(
            dimension=MandateHealthDimension.ELIGIBILITY_RESTRICTIONS,
            score=0,
            state=MandateHealthState.BLOCKED,
            reason_code="RESTRICTED_INSTRUMENT_HELD",
            measured_value=len(restricted),
            threshold_value=0,
        )
    return _ready_score(MandateHealthDimension.ELIGIBILITY_RESTRICTIONS)


def _score_performance_attention(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    source_score = _score_source_health_context(
        context=input_.performance_health_context,
        dimension=MandateHealthDimension.PERFORMANCE_ATTENTION,
        attention_reason_code="SOURCE_PERFORMANCE_HEALTH_ATTENTION",
        unavailable_reason_code="SOURCE_PERFORMANCE_HEALTH_UNAVAILABLE",
    )
    if source_score is not None:
        return source_score
    if input_.performance_under_review:
        return _attention_score(
            dimension=MandateHealthDimension.PERFORMANCE_ATTENTION,
            score=70,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="PERFORMANCE_UNDER_REVIEW",
        )
    return _ready_score(MandateHealthDimension.PERFORMANCE_ATTENTION)


def _score_source_health_context(
    *,
    context: Optional[DpmMandateSourceHealthContext],
    dimension: MandateHealthDimension,
    attention_reason_code: str,
    unavailable_reason_code: str,
) -> Optional[DpmMandateDimensionScore]:
    if context is None:
        return None
    context_ref = _source_health_context_ref(context)
    if context.health_state == "ready" and context.threshold_breached is not True:
        return _ready_score(dimension)
    if context.health_state == "unavailable":
        return _attention_score(
            dimension=dimension,
            score=60,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code=unavailable_reason_code,
            measured_value=f"{context.source_product_name}:unavailable",
            threshold_value="ready",
            evidence_refs=[context_ref],
        )
    return _attention_score(
        dimension=dimension,
        score=65,
        state=MandateHealthState.PENDING_REVIEW,
        reason_code=attention_reason_code,
        measured_value=f"{context.source_product_name}:{context.health_state}",
        threshold_value="ready",
        evidence_refs=[context_ref],
    )


def _score_workflow_readiness(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    if input_.workflow_blocked:
        return _attention_score(
            dimension=MandateHealthDimension.WORKFLOW_READINESS,
            score=0,
            state=MandateHealthState.BLOCKED,
            reason_code="REBALANCE_RUN_BLOCKED",
        )
    if input_.sustainability_review_required:
        return _attention_score(
            dimension=MandateHealthDimension.WORKFLOW_READINESS,
            score=70,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="SUSTAINABILITY_REVIEW_REQUIRED",
        )
    if input_.approval_required:
        return _attention_score(
            dimension=MandateHealthDimension.WORKFLOW_READINESS,
            score=70,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="APPROVAL_REQUIRED",
        )
    return _ready_score(MandateHealthDimension.WORKFLOW_READINESS)


def _score_review_cadence(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    due_date = input_.twin.review_policy.next_review_due_date
    if due_date is not None and due_date < input_.twin.as_of_date:
        days_overdue = (input_.twin.as_of_date - due_date).days
        return _attention_score(
            dimension=MandateHealthDimension.REVIEW_CADENCE,
            score=65,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="MANDATE_REVIEW_OVERDUE",
            measured_value=days_overdue,
            threshold_value=0,
        )
    return _ready_score(MandateHealthDimension.REVIEW_CADENCE)


def _score_model_freshness(input_: DpmMandateHealthInput) -> DpmMandateDimensionScore:
    if input_.model_effective_to is not None and input_.model_effective_to < input_.twin.as_of_date:
        return _attention_score(
            dimension=MandateHealthDimension.MODEL_FRESHNESS,
            score=55,
            state=MandateHealthState.PENDING_REVIEW,
            reason_code="MODEL_VERSION_STALE",
            measured_value=input_.model_effective_to.isoformat(),
            threshold_value=input_.twin.as_of_date.isoformat(),
        )
    return _ready_score(MandateHealthDimension.MODEL_FRESHNESS)


def _reason_from_score(score: DpmMandateDimensionScore) -> DpmMandateHealthReason:
    severity = (
        MonitoringSeverity.CRITICAL
        if score.state == MandateHealthState.BLOCKED
        else MonitoringSeverity.WARNING
    )
    return DpmMandateHealthReason(
        dimension=score.dimension,
        reason_code=score.reason_code,
        severity=severity,
        message=f"{score.dimension.value} requires attention: {score.reason_code}",
        recommended_action=_recommended_action_for_dimension(
            score.dimension, score.state, score.reason_code
        ),
    )


_SOURCE_GAP_REASON_CODES = frozenset(
    {
        "CASH_BAND_NOT_SOURCED",
        "TURNOVER_BUDGET_NOT_SOURCED",
    }
)


def _recommended_action_for_dimension(
    dimension: MandateHealthDimension,
    state: MandateHealthState,
    reason_code: str = "",
) -> MandateRecommendedAction:
    if reason_code in _SOURCE_GAP_REASON_CODES:
        # An absent mandate limit is a source gap, not a portfolio problem
        # (issue #664). Simulating a rebalance cannot produce a limit Core
        # never supplied, so the generic pending-dimension action would send
        # an operator somewhere that cannot resolve the finding.
        return MandateRecommendedAction.FIX_SOURCE_DATA
    if dimension == MandateHealthDimension.SOURCE_READINESS:
        return MandateRecommendedAction.FIX_SOURCE_DATA
    if dimension == MandateHealthDimension.ELIGIBILITY_RESTRICTIONS:
        return MandateRecommendedAction.REVIEW_RESTRICTION
    if dimension in {
        MandateHealthDimension.WORKFLOW_READINESS,
        MandateHealthDimension.REVIEW_CADENCE,
    }:
        return MandateRecommendedAction.REVIEW_WORKFLOW
    if state == MandateHealthState.PENDING_REVIEW:
        return MandateRecommendedAction.SIMULATE_REBALANCE
    return MandateRecommendedAction.REVIEW_MANDATE


def _overall_recommended_action(
    health_state: MandateHealthState,
    reasons: list[DpmMandateHealthReason],
) -> MandateRecommendedAction:
    if health_state == MandateHealthState.READY:
        return MandateRecommendedAction.NONE
    # A source gap outranks other findings rather than taking its turn among
    # them (issue #664). Reasons of equal severity keep dimension order, so a
    # co-occurring ALLOCATION_DRIFT or PROJECTED_CASHFLOW_PRESSURE would
    # otherwise decide the overall action and the snapshot would contradict
    # itself: the individual reason says FIX_SOURCE_DATA while the headline
    # says SIMULATE_REBALANCE. Simulation cannot produce a limit Core never
    # supplied, so the missing limit has to be resolved first regardless of
    # what else is wrong.
    if any(reason.reason_code in _SOURCE_GAP_REASON_CODES for reason in reasons):
        return MandateRecommendedAction.FIX_SOURCE_DATA
    if reasons:
        return reasons[0].recommended_action
    return MandateRecommendedAction.REVIEW_MANDATE


def _severity_rank(severity: MonitoringSeverity) -> int:
    return {
        MonitoringSeverity.INFO: 0,
        MonitoringSeverity.WARNING: 1,
        MonitoringSeverity.CRITICAL: 2,
    }[severity]


if sum(DIMENSION_WEIGHTS.values()) != 100:
    raise RuntimeError("Mandate health dimension weights must total 100")
