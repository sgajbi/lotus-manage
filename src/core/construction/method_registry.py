"""Construction method registry and solver/fallback governance."""

from src.core.common.capabilities import has_solver_dependencies
from src.core.construction.models import (
    ConstructionMethodDefinition,
    ConstructionMethodPlan,
    ConstructionSolverPosture,
)
from src.core.construction.vocabulary import (
    ConstructionMethod,
    ConstructionMethodStatus,
    ConstructionSourceFamily,
)


METHOD_REGISTRY: dict[ConstructionMethod, ConstructionMethodDefinition] = {
    ConstructionMethod.DO_NOTHING_BASELINE: ConstructionMethodDefinition(
        method=ConstructionMethod.DO_NOTHING_BASELINE,
        display_name="Do Nothing Baseline",
        first_wave=True,
        requires_solver=False,
        required_source_families=[
            ConstructionSourceFamily.PORTFOLIO_STATE,
            ConstructionSourceFamily.MODEL_TARGETS,
            ConstructionSourceFamily.MANDATE_BINDING,
            ConstructionSourceFamily.MARKET_DATA,
        ],
        fallback_method=None,
        support_promotion_gate="No-action comparator with current drift and source readiness.",
    ),
    ConstructionMethod.HEURISTIC_EXPLAINABLE: ConstructionMethodDefinition(
        method=ConstructionMethod.HEURISTIC_EXPLAINABLE,
        display_name="Explainable Heuristic",
        first_wave=True,
        requires_solver=False,
        required_source_families=[
            ConstructionSourceFamily.PORTFOLIO_STATE,
            ConstructionSourceFamily.MODEL_TARGETS,
            ConstructionSourceFamily.MANDATE_BINDING,
            ConstructionSourceFamily.INSTRUMENT_ELIGIBILITY,
            ConstructionSourceFamily.MARKET_DATA,
        ],
        fallback_method=None,
        support_promotion_gate="Reason-coded deterministic output with constraints and diagnostics.",
    ),
    ConstructionMethod.MIN_TURNOVER: ConstructionMethodDefinition(
        method=ConstructionMethod.MIN_TURNOVER,
        display_name="Minimum Turnover",
        first_wave=True,
        requires_solver=False,
        required_source_families=[
            ConstructionSourceFamily.PORTFOLIO_STATE,
            ConstructionSourceFamily.MODEL_TARGETS,
            ConstructionSourceFamily.MANDATE_BINDING,
            ConstructionSourceFamily.INSTRUMENT_ELIGIBILITY,
            ConstructionSourceFamily.MARKET_DATA,
        ],
        fallback_method=ConstructionMethod.HEURISTIC_EXPLAINABLE,
        support_promotion_gate="Turnover, trade count, drift reduction, and dropped-intent proof.",
    ),
    ConstructionMethod.TAX_AWARE: ConstructionMethodDefinition(
        method=ConstructionMethod.TAX_AWARE,
        display_name="Tax Aware",
        first_wave=True,
        requires_solver=False,
        required_source_families=[
            ConstructionSourceFamily.PORTFOLIO_STATE,
            ConstructionSourceFamily.MODEL_TARGETS,
            ConstructionSourceFamily.MANDATE_BINDING,
            ConstructionSourceFamily.INSTRUMENT_ELIGIBILITY,
            ConstructionSourceFamily.MARKET_DATA,
            ConstructionSourceFamily.TAX_LOTS,
        ],
        fallback_method=ConstructionMethod.HEURISTIC_EXPLAINABLE,
        support_promotion_gate="Tax-lot supportability and realized-gain/loss proof.",
    ),
    ConstructionMethod.SOLVER_CONSTRAINED: ConstructionMethodDefinition(
        method=ConstructionMethod.SOLVER_CONSTRAINED,
        display_name="Solver Constrained",
        first_wave=False,
        requires_solver=True,
        required_source_families=[
            ConstructionSourceFamily.PORTFOLIO_STATE,
            ConstructionSourceFamily.MODEL_TARGETS,
            ConstructionSourceFamily.MANDATE_BINDING,
            ConstructionSourceFamily.INSTRUMENT_ELIGIBILITY,
            ConstructionSourceFamily.MARKET_DATA,
        ],
        fallback_method=ConstructionMethod.HEURISTIC_EXPLAINABLE,
        support_promotion_gate="Solver trace, timeout, infeasibility, and fallback evidence.",
    ),
    ConstructionMethod.LIQUIDITY_AWARE: ConstructionMethodDefinition(
        method=ConstructionMethod.LIQUIDITY_AWARE,
        display_name="Liquidity Aware",
        first_wave=False,
        requires_solver=False,
        required_source_families=[
            ConstructionSourceFamily.PORTFOLIO_STATE,
            ConstructionSourceFamily.MODEL_TARGETS,
            ConstructionSourceFamily.MANDATE_BINDING,
            ConstructionSourceFamily.INSTRUMENT_ELIGIBILITY,
            ConstructionSourceFamily.MARKET_DATA,
            ConstructionSourceFamily.LIQUIDITY_PROFILE,
        ],
        fallback_method=ConstructionMethod.HEURISTIC_EXPLAINABLE,
        support_promotion_gate="Cash, liquidity, settlement, and missing-cashflow proof.",
    ),
    ConstructionMethod.RISK_AWARE: ConstructionMethodDefinition(
        method=ConstructionMethod.RISK_AWARE,
        display_name="Risk Aware",
        first_wave=False,
        requires_solver=False,
        required_source_families=[
            ConstructionSourceFamily.PORTFOLIO_STATE,
            ConstructionSourceFamily.MODEL_TARGETS,
            ConstructionSourceFamily.RISK_ENRICHMENT,
        ],
        fallback_method=ConstructionMethod.HEURISTIC_EXPLAINABLE,
        support_promotion_gate="Risk-owned enrichment and degraded-risk proof.",
    ),
    ConstructionMethod.ESG_AWARE: ConstructionMethodDefinition(
        method=ConstructionMethod.ESG_AWARE,
        display_name="ESG Aware",
        first_wave=False,
        requires_solver=False,
        required_source_families=[
            ConstructionSourceFamily.PORTFOLIO_STATE,
            ConstructionSourceFamily.MODEL_TARGETS,
            ConstructionSourceFamily.ESG_PROFILE,
        ],
        fallback_method=ConstructionMethod.HEURISTIC_EXPLAINABLE,
        support_promotion_gate="Sustainability preference and restriction source proof.",
    ),
    ConstructionMethod.CURRENCY_OVERLAY: ConstructionMethodDefinition(
        method=ConstructionMethod.CURRENCY_OVERLAY,
        display_name="Currency Overlay",
        first_wave=False,
        requires_solver=False,
        required_source_families=[
            ConstructionSourceFamily.PORTFOLIO_STATE,
            ConstructionSourceFamily.MARKET_DATA,
            ConstructionSourceFamily.CURRENCY_POLICY,
        ],
        fallback_method=ConstructionMethod.HEURISTIC_EXPLAINABLE,
        support_promotion_gate="Currency policy, hedge eligibility, and FX source proof.",
    ),
    ConstructionMethod.REGIME_STRESS_AWARE: ConstructionMethodDefinition(
        method=ConstructionMethod.REGIME_STRESS_AWARE,
        display_name="Regime Stress Aware",
        first_wave=False,
        requires_solver=False,
        required_source_families=[
            ConstructionSourceFamily.PORTFOLIO_STATE,
            ConstructionSourceFamily.MODEL_TARGETS,
            ConstructionSourceFamily.REGIME_SCENARIO,
        ],
        fallback_method=ConstructionMethod.HEURISTIC_EXPLAINABLE,
        support_promotion_gate="Risk/CIO-owned scenario pack and stress proof.",
    ),
}


def get_method_definition(method: ConstructionMethod) -> ConstructionMethodDefinition:
    return METHOD_REGISTRY[method]


def first_wave_method_definitions() -> tuple[ConstructionMethodDefinition, ...]:
    return tuple(definition for definition in METHOD_REGISTRY.values() if definition.first_wave)


def resolve_method_plan(
    method: ConstructionMethod,
    *,
    solver_available: bool | None = None,
) -> ConstructionMethodPlan:
    definition = get_method_definition(method)
    available = has_solver_dependencies() if solver_available is None else solver_available
    solver_posture = _solver_posture(definition=definition, solver_available=available)

    if definition.requires_solver and not available:
        fallback = definition.fallback_method or ConstructionMethod.HEURISTIC_EXPLAINABLE
        fallback_definition = get_method_definition(fallback)
        return ConstructionMethodPlan(
            requested_method=method,
            effective_method=fallback,
            method_status=ConstructionMethodStatus.PENDING_REVIEW,
            fallback_method=fallback,
            reason_codes=["SOLVER_UNAVAILABLE_FALLBACK_HEURISTIC"],
            required_source_families=fallback_definition.required_source_families,
            solver_posture=solver_posture,
        )

    return ConstructionMethodPlan(
        requested_method=method,
        effective_method=method,
        method_status=ConstructionMethodStatus.READY,
        fallback_method=None,
        reason_codes=[],
        required_source_families=definition.required_source_families,
        solver_posture=solver_posture,
    )


def classify_solver_failure(reason_code: str) -> ConstructionMethodStatus:
    if reason_code.startswith("INFEASIBLE_") or reason_code.startswith("UNBOUNDED_"):
        return ConstructionMethodStatus.BLOCKED
    if reason_code == "SOLVER_ERROR" or reason_code.startswith("SOLVER_NON_OPTIMAL_"):
        return ConstructionMethodStatus.PENDING_REVIEW
    return ConstructionMethodStatus.DEGRADED


def _solver_posture(
    *,
    definition: ConstructionMethodDefinition,
    solver_available: bool,
) -> ConstructionSolverPosture:
    if not definition.requires_solver:
        return ConstructionSolverPosture(
            solver_required=False,
            solver_available=solver_available,
            solver_engine=None,
            reason_code="SOLVER_NOT_REQUIRED",
        )
    if solver_available:
        return ConstructionSolverPosture(
            solver_required=True,
            solver_available=True,
            solver_engine="cvxpy",
            reason_code="SOLVER_AVAILABLE",
        )
    return ConstructionSolverPosture(
        solver_required=True,
        solver_available=False,
        solver_engine=None,
        reason_code="SOLVER_UNAVAILABLE",
    )
