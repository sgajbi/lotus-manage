"""Pure expected-versus-realized comparison for RFC-0042 outcome reviews."""

from decimal import Decimal

from src.core.outcomes.models import (
    DpmOutcomeDimensionInput,
    DpmOutcomeDimensionResult,
    DpmOutcomeReviewComparison,
    DpmOutcomeSourceRef,
    DpmOutcomeSupportability,
    OutcomeDimension,
    OutcomeDimensionState,
)

_DIMENSION_NOT_SUPPORTED_REASON: dict[OutcomeDimension, str] = {
    "RISK_REDUCTION": "RISK_OUTCOME_NOT_SUPPORTED",
    "PERFORMANCE": "PERFORMANCE_OUTCOME_NOT_SUPPORTED",
    "EXECUTION_QUALITY": "EXECUTION_EVIDENCE_BLOCKED",
}

_READY_REASON: dict[OutcomeDimension, str] = {
    "DRIFT_REDUCTION": "DRIFT_REDUCTION_ACHIEVED",
    "RISK_REDUCTION": "RISK_REDUCTION_ACHIEVED",
}

_PENDING_REASON: dict[OutcomeDimension, str] = {
    "DRIFT_REDUCTION": "DRIFT_REDUCTION_SHORTFALL",
    "RISK_REDUCTION": "RISK_INCREASED",
    "PERFORMANCE": "PERFORMANCE_BELOW_EXPECTATION",
    "COST": "COST_ABOVE_ESTIMATE",
    "TAX": "TAX_ABOVE_BUDGET",
    "EXECUTION_QUALITY": "SLIPPAGE_ABOVE_TOLERANCE",
    "FX_RESIDUAL": "FX_RESIDUAL_VARIANCE",
    "CASH_RESIDUAL": "CASH_RESIDUAL_OUT_OF_BAND",
    "RULE_OUTCOME": "RULE_OUTCOME_BREACHED",
}

_BLOCKING_STATES: set[OutcomeDimensionState] = {"BLOCKED"}
_DEGRADED_STATES: set[OutcomeDimensionState] = {"DEGRADED"}
_NOT_SUPPORTED_STATES: set[OutcomeDimensionState] = {"NOT_SUPPORTED"}


def compare_outcome_dimensions(
    dimensions: list[DpmOutcomeDimensionInput],
) -> DpmOutcomeReviewComparison:
    """Compare supplied dimensions and roll up deterministic supportability."""

    results = [compare_outcome_dimension(dimension) for dimension in dimensions]
    state = _roll_up_state([result.state for result in results])
    supportability = DpmOutcomeSupportability(
        state=state,
        reason_codes=_roll_up_reason_codes(results),
        required_source=True,
        explanation=_overall_explanation(state),
    )
    return DpmOutcomeReviewComparison(
        state=state,
        dimension_results=results,
        overall_outcome=_overall_outcome(state),
        variance_summary={result.dimension: result.variance for result in results},
        supportability=supportability,
    )


def compare_outcome_dimension(
    dimension_input: DpmOutcomeDimensionInput,
) -> DpmOutcomeDimensionResult:
    """Compare one outcome dimension without source clients or persistence."""

    source_refs = [
        *dimension_input.expected.source_refs,
        *dimension_input.realized.source_refs,
    ]
    supportability_state = _source_supportability_state(dimension_input)
    if supportability_state == "NOT_SUPPORTED":
        reason = _not_supported_reason(dimension_input.dimension)
        return _result(
            dimension_input,
            state="NOT_SUPPORTED",
            reason_code=reason,
            source_refs=source_refs,
            explanation="No certified source-owner contract supports this outcome dimension.",
        )
    if supportability_state == "BLOCKED":
        reason = _blocked_reason(dimension_input.dimension)
        return _result(
            dimension_input,
            state="BLOCKED",
            reason_code=reason,
            source_refs=source_refs,
            explanation="Mandatory source evidence is missing, conflicting, or invalid.",
        )

    expected = dimension_input.expected.value
    realized = dimension_input.realized.value
    if expected is None or realized is None:
        return _result(
            dimension_input,
            state="BLOCKED",
            reason_code=_blocked_reason(dimension_input.dimension),
            source_refs=source_refs,
            explanation="Expected and realized values are mandatory for deterministic comparison.",
        )

    variance = realized - expected
    pressure = _variance_pressure(
        expected=expected,
        realized=realized,
        variance=variance,
        dimension_input=dimension_input,
    )
    if pressure > dimension_input.tolerance.hard:
        state: OutcomeDimensionState = "BREACHED"
        reason_code = _pending_reason(dimension_input.dimension)
    elif pressure > dimension_input.tolerance.soft:
        state = "PENDING_REVIEW"
        reason_code = _pending_reason(dimension_input.dimension)
    elif supportability_state == "DEGRADED":
        state = "DEGRADED"
        reason_code = "SOURCE_EVIDENCE_INCOMPLETE"
    else:
        state = "READY"
        reason_code = _ready_reason(dimension_input.dimension)

    return _result(
        dimension_input,
        state=state,
        reason_code=reason_code,
        source_refs=source_refs,
        variance=variance,
        pressure=pressure,
        explanation=_dimension_explanation(state, reason_code, pressure),
    )


def _variance_pressure(
    *,
    expected: Decimal,
    realized: Decimal,
    variance: Decimal,
    dimension_input: DpmOutcomeDimensionInput,
) -> Decimal:
    if dimension_input.direction == "LOWER_IS_BETTER":
        return max(variance, Decimal("0"))
    if dimension_input.direction == "HIGHER_IS_BETTER":
        return max(-variance, Decimal("0"))
    return abs(realized - expected)


def _source_supportability_state(
    dimension_input: DpmOutcomeDimensionInput,
) -> OutcomeDimensionState:
    source_states = [
        dimension_input.expected.supportability.state,
        dimension_input.realized.supportability.state,
    ]
    if any(state in _NOT_SUPPORTED_STATES for state in source_states):
        return "NOT_SUPPORTED"
    if any(state in _BLOCKING_STATES for state in source_states):
        return "BLOCKED"
    if any(state in _DEGRADED_STATES for state in source_states):
        return "DEGRADED"
    return "READY"


def _result(
    dimension_input: DpmOutcomeDimensionInput,
    *,
    state: OutcomeDimensionState,
    reason_code: str,
    source_refs: list[DpmOutcomeSourceRef],
    explanation: str,
    variance: Decimal | None = None,
    pressure: Decimal | None = None,
) -> DpmOutcomeDimensionResult:
    supportability = DpmOutcomeSupportability(
        state=state,
        reason_codes=[reason_code],
        required_source=True,
        explanation=explanation,
    )
    return DpmOutcomeDimensionResult(
        dimension=dimension_input.dimension,
        state=state,
        reason_code=reason_code,
        expected=dimension_input.expected.value,
        realized=dimension_input.realized.value,
        variance=variance,
        tolerance=dimension_input.tolerance,
        materiality=dimension_input.materiality,
        explanation=explanation,
        source_refs=source_refs,
        source_freshness=[
            dimension_input.expected.source_freshness,
            dimension_input.realized.source_freshness,
        ],
        supportability=supportability,
        calculation_trace={
            "direction": dimension_input.direction,
            "soft_tolerance": dimension_input.tolerance.soft,
            "hard_tolerance": dimension_input.tolerance.hard,
            "materiality": dimension_input.materiality,
            "variance_pressure": pressure,
        },
    )


def _roll_up_state(states: list[OutcomeDimensionState]) -> OutcomeDimensionState:
    if not states:
        return "BLOCKED"
    if all(state == "NOT_SUPPORTED" for state in states):
        return "NOT_SUPPORTED"
    for candidate in ("BLOCKED", "BREACHED", "PENDING_REVIEW"):
        if candidate in states:
            return candidate
    if "DEGRADED" in states or "NOT_SUPPORTED" in states:
        return "DEGRADED"
    return "READY"


def _roll_up_reason_codes(results: list[DpmOutcomeDimensionResult]) -> list[str]:
    reason_codes: list[str] = []
    for result in results:
        if result.reason_code not in reason_codes:
            reason_codes.append(result.reason_code)
    return reason_codes or ["SOURCE_EVIDENCE_INCOMPLETE"]


def _ready_reason(dimension: OutcomeDimension) -> str:
    return _READY_REASON.get(dimension, "OUTCOME_WITHIN_TOLERANCE")


def _pending_reason(dimension: OutcomeDimension) -> str:
    return _PENDING_REASON.get(dimension, "RULE_OUTCOME_BREACHED")


def _blocked_reason(dimension: OutcomeDimension) -> str:
    if dimension == "EXECUTION_QUALITY":
        return "EXECUTION_EVIDENCE_BLOCKED"
    return "SOURCE_EVIDENCE_INCOMPLETE"


def _not_supported_reason(dimension: OutcomeDimension) -> str:
    return _DIMENSION_NOT_SUPPORTED_REASON.get(dimension, "SOURCE_EVIDENCE_INCOMPLETE")


def _dimension_explanation(
    state: OutcomeDimensionState,
    reason_code: str,
    pressure: Decimal,
) -> str:
    return (
        f"Dimension classified as {state} with reason {reason_code}; "
        f"variance pressure is {pressure}."
    )


def _overall_outcome(state: OutcomeDimensionState) -> str:
    return {
        "READY": "READY_WITHIN_TOLERANCE",
        "PENDING_REVIEW": "PENDING_PM_REVIEW",
        "BREACHED": "OUTCOME_BREACHED",
        "DEGRADED": "SOURCE_DEGRADED",
        "BLOCKED": "SOURCE_BLOCKED",
        "NOT_SUPPORTED": "NOT_SUPPORTED",
    }[state]


def _overall_explanation(state: OutcomeDimensionState) -> str:
    return f"Outcome review rolled up to {state} from deterministic dimension states."
