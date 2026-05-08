from src.core.construction import (
    FIRST_WAVE_CONSTRUCTION_METHODS,
    SOURCE_AWARE_CONSTRUCTION_METHODS,
    ConstructionMethod,
    ConstructionMethodStatus,
    ConstructionSourceFamily,
    ConstructionTraceTerm,
)


def test_first_wave_methods_are_explicit_and_ordered_for_rfc0039() -> None:
    assert FIRST_WAVE_CONSTRUCTION_METHODS == (
        ConstructionMethod.DO_NOTHING_BASELINE,
        ConstructionMethod.HEURISTIC_EXPLAINABLE,
        ConstructionMethod.MIN_TURNOVER,
        ConstructionMethod.TAX_AWARE,
    )


def test_method_statuses_are_bounded_and_do_not_add_ready_with_warnings() -> None:
    assert {status.value for status in ConstructionMethodStatus} == {
        "READY",
        "PENDING_REVIEW",
        "DEGRADED",
        "BLOCKED",
    }


def test_source_aware_methods_require_source_supportability_posture() -> None:
    assert ConstructionMethod.TAX_AWARE in SOURCE_AWARE_CONSTRUCTION_METHODS
    assert ConstructionMethod.COST_AWARE in SOURCE_AWARE_CONSTRUCTION_METHODS
    assert ConstructionMethod.DO_NOTHING_BASELINE not in SOURCE_AWARE_CONSTRUCTION_METHODS
    assert ConstructionSourceFamily.TAX_LOTS.value == "TAX_LOTS"
    assert ConstructionSourceFamily.TRANSACTION_COST.value == "TRANSACTION_COST"
    assert ConstructionSourceFamily.RISK_ENRICHMENT.value == "RISK_ENRICHMENT"


def test_trace_terms_are_bounded_for_safe_audit_and_observability() -> None:
    assert ConstructionTraceTerm.DRIFT.value == "DRIFT"
    assert ConstructionTraceTerm.SOURCE_SUPPORTABILITY.value == "SOURCE_SUPPORTABILITY"
    assert "CLIENT" not in {term.value for term in ConstructionTraceTerm}
