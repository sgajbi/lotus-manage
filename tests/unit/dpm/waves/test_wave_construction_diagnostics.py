from src.api.services.wave_construction_diagnostics import (
    proposed_changes_from_alternative_set,
)
from src.core.construction.models import ConstructionAlternative, ConstructionAlternativeSet


def _alternative(diagnostics: dict[str, object]) -> ConstructionAlternative:
    return ConstructionAlternative.model_construct(
        alternative_id="alt_001",
        method="heuristic",
        method_status="READY",
        summary="Candidate rebalance alternative.",
        objective_trace=[],
        constraint_trace=[],
        comparison_metrics=None,
        diagnostics=diagnostics,
    )


def _alternative_set(
    alternatives: list[ConstructionAlternative],
) -> ConstructionAlternativeSet:
    return ConstructionAlternativeSet.model_construct(
        alternative_set_id="cas_001",
        portfolio_id="PB_SG_CONSTRUCTION",
        as_of="2026-05-03",
        status="READY",
        alternatives=alternatives,
    )


def test_proposed_changes_uses_first_populated_alternative_changes() -> None:
    changes = proposed_changes_from_alternative_set(
        _alternative_set(
            [
                _alternative({"proposed_changes": []}),
                _alternative(
                    {
                        "proposed_changes": [
                            {"security_id": "SEC_A", "target_weight": "0.10"},
                            "not-a-change",
                            {"security_id": "SEC_B", "target_weight": "0.20"},
                        ]
                    }
                ),
            ]
        )
    )

    assert changes == [
        {"security_id": "SEC_A", "target_weight": "0.10"},
        {"security_id": "SEC_B", "target_weight": "0.20"},
    ]


def test_proposed_changes_returns_empty_for_missing_or_non_list_changes() -> None:
    assert (
        proposed_changes_from_alternative_set(
            _alternative_set(
                [
                    _alternative({}),
                    _alternative({"proposed_changes": {"security_id": "SEC_A"}}),
                ]
            )
        )
        == []
    )


def test_wave_construction_diagnostics_exports_only_diagnostic_helpers() -> None:
    from src.api.services import wave_construction_diagnostics

    assert wave_construction_diagnostics.__all__ == ["proposed_changes_from_alternative_set"]
