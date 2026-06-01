from decimal import Decimal

import pytest

from src.api.services.construction_selection import build_construction_selection
from src.core.construction.models import (
    ConstructionAlternative,
    ConstructionComparisonMetrics,
)
from src.core.construction.repository import ConstructionAlternativeNotFoundError
from src.core.construction.vocabulary import ConstructionMethod, ConstructionMethodStatus


def _alternative_set():
    from src.core.construction.alternative_engine import build_alternative_set

    return build_alternative_set(
        alternative_set_id="cas_select_001",
        portfolio_id="pf_select",
        as_of="2026-06-01",
        alternatives=[
            ConstructionAlternative(
                alternative_id="alt_heuristic_explainable",
                method=ConstructionMethod.HEURISTIC_EXPLAINABLE,
                method_status=ConstructionMethodStatus.READY,
                summary="Test alternative.",
                objective_trace=[],
                constraint_trace=[],
                comparison_metrics=ConstructionComparisonMetrics(
                    drift_before=Decimal("0.0000"),
                    drift_after=Decimal("0.0000"),
                    drift_reduction=Decimal("0.0000"),
                    turnover_weight=Decimal("0.0000"),
                    trade_count=0,
                    estimated_transaction_cost=None,
                    cash_weight_after=None,
                ),
            )
        ],
    )


def test_build_construction_selection_preserves_selection_fields() -> None:
    selection = build_construction_selection(
        selection_id="casel_test_001",
        alternative_set=_alternative_set(),
        alternative_id="alt_heuristic_explainable",
        actor_id="pm_1",
        reason_code="PM_SELECTED_HEURISTIC",
        comment="Selected for review.",
        correlation_id="corr_1",
    )

    assert selection.selection_id == "casel_test_001"
    assert selection.alternative_set_id == "cas_select_001"
    assert selection.alternative_id == "alt_heuristic_explainable"
    assert selection.actor_id == "pm_1"
    assert selection.reason_code == "PM_SELECTED_HEURISTIC"
    assert selection.comment == "Selected for review."
    assert selection.correlation_id == "corr_1"


def test_build_construction_selection_rejects_unknown_alternative() -> None:
    with pytest.raises(
        ConstructionAlternativeNotFoundError,
        match="CONSTRUCTION_ALTERNATIVE_NOT_FOUND",
    ):
        build_construction_selection(
            selection_id="casel_test_001",
            alternative_set=_alternative_set(),
            alternative_id="alt_missing",
            actor_id="pm_1",
            reason_code="PM_SELECTED_HEURISTIC",
            comment=None,
            correlation_id=None,
        )
