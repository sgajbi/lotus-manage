from datetime import date
from decimal import Decimal

from src.api.services import mandate_health_result
from src.api.services.mandate_health_result import (
    DpmMandateHealthCalculationResult,
    calculate_mandate_health_result,
)
from src.core.mandates import (
    DpmMandateConstraintSet,
    DpmMandateDigitalTwin,
    DpmMandateHealthInput,
    DpmMandateReviewPolicy,
)


def _twin() -> DpmMandateDigitalTwin:
    return DpmMandateDigitalTwin(
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        mandate_version="3",
        as_of_date=date(2026, 5, 3),
        base_currency="SGD",
        reference_currency="SGD",
        risk_profile="BALANCED",
        investment_objective="LONG_TERM_TOTAL_RETURN",
        time_horizon="LONG_TERM",
        model_portfolio_id="MODEL_PB_SG_GLOBAL_BAL_DPM",
        constraints=DpmMandateConstraintSet(
            cash_band_min_weight=Decimal("0.02"),
            cash_band_max_weight=Decimal("0.10"),
            turnover_budget=Decimal("0.15"),
        ),
        review_policy=DpmMandateReviewPolicy(next_review_due_date=date(2026, 6, 30)),
    )


def test_calculate_mandate_health_result_returns_snapshot_and_exceptions() -> None:
    result = calculate_mandate_health_result(
        DpmMandateHealthInput(twin=_twin()), tenant_id="tenant-test"
    )

    assert isinstance(result, DpmMandateHealthCalculationResult)
    assert result.snapshot.mandate_id == "MANDATE_PB_SG_GLOBAL_BAL_001"
    assert result.snapshot.portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert result.snapshot.as_of_date == date(2026, 5, 3)
    assert result.monitoring_exceptions
    assert {exception.mandate_id for exception in result.monitoring_exceptions} == {
        "MANDATE_PB_SG_GLOBAL_BAL_001"
    }


def test_service_preserves_health_result_import_surface() -> None:
    from src.api.services import mandate_service

    assert mandate_service.DpmMandateHealthCalculationResult is DpmMandateHealthCalculationResult


def test_health_result_helper_exports_public_surface() -> None:
    assert mandate_health_result.__all__ == [
        "DpmMandateHealthCalculationResult",
        "calculate_mandate_health_result",
    ]
