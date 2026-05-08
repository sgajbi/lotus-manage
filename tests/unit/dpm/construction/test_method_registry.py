from src.core.construction import (
    METHOD_REGISTRY,
    ConstructionMethod,
    ConstructionMethodStatus,
    ConstructionSourceFamily,
    classify_solver_failure,
    first_wave_method_definitions,
    resolve_method_plan,
)


def test_registry_contains_every_declared_construction_method() -> None:
    assert set(METHOD_REGISTRY) == set(ConstructionMethod)


def test_first_wave_registry_matches_rfc0039_order_and_required_sources() -> None:
    definitions = first_wave_method_definitions()

    assert [definition.method for definition in definitions] == [
        ConstructionMethod.DO_NOTHING_BASELINE,
        ConstructionMethod.HEURISTIC_EXPLAINABLE,
        ConstructionMethod.MIN_TURNOVER,
        ConstructionMethod.TAX_AWARE,
    ]
    tax_definition = METHOD_REGISTRY[ConstructionMethod.TAX_AWARE]
    assert ConstructionSourceFamily.TAX_LOTS in tax_definition.required_source_families
    cost_definition = METHOD_REGISTRY[ConstructionMethod.COST_AWARE]
    assert cost_definition.first_wave is False
    assert ConstructionSourceFamily.TRANSACTION_COST in cost_definition.required_source_families


def test_solver_method_falls_back_explicitly_when_solver_unavailable() -> None:
    plan = resolve_method_plan(
        ConstructionMethod.SOLVER_CONSTRAINED,
        solver_available=False,
    )

    assert plan.requested_method == ConstructionMethod.SOLVER_CONSTRAINED
    assert plan.effective_method == ConstructionMethod.HEURISTIC_EXPLAINABLE
    assert plan.method_status == ConstructionMethodStatus.PENDING_REVIEW
    assert plan.fallback_method == ConstructionMethod.HEURISTIC_EXPLAINABLE
    assert plan.reason_codes == ["SOLVER_UNAVAILABLE_FALLBACK_HEURISTIC"]
    assert plan.solver_posture.reason_code == "SOLVER_UNAVAILABLE"


def test_solver_method_is_ready_when_solver_available() -> None:
    plan = resolve_method_plan(
        ConstructionMethod.SOLVER_CONSTRAINED,
        solver_available=True,
    )

    assert plan.effective_method == ConstructionMethod.SOLVER_CONSTRAINED
    assert plan.method_status == ConstructionMethodStatus.READY
    assert plan.fallback_method is None
    assert plan.solver_posture.reason_code == "SOLVER_AVAILABLE"


def test_solver_failure_classification_is_bounded() -> None:
    assert classify_solver_failure("INFEASIBLE_INFEASIBLE") == ConstructionMethodStatus.BLOCKED
    assert classify_solver_failure("UNBOUNDED_UNBOUNDED") == ConstructionMethodStatus.BLOCKED
    assert classify_solver_failure("SOLVER_ERROR") == ConstructionMethodStatus.PENDING_REVIEW
    assert (
        classify_solver_failure("SOLVER_NON_OPTIMAL_USER_LIMIT")
        == ConstructionMethodStatus.PENDING_REVIEW
    )
    assert classify_solver_failure("UNKNOWN_SOLVER_WARNING") == ConstructionMethodStatus.DEGRADED
