from datetime import date, datetime, timezone
from decimal import Decimal

from src.api.services import mandate_monitoring_run, mandate_service
from src.api.services.mandate_monitoring_run import (
    DpmMonitoringRunAccumulator,
    DpmMonitoringRunMandateResult,
    build_monitoring_run,
    calculate_monitoring_run_mandate_result,
    exceptions_for_monitoring_run,
    increment_distribution,
    monitoring_run_id_for,
)
from src.core.mandates import (
    DpmMandateConstraintSet,
    DpmMandateDigitalTwin,
    DpmMandateReviewPolicy,
    DpmMonitoringException,
    MandateHealthDimension,
    MandateRecommendedAction,
    MonitoringSeverity,
)


def _twin() -> DpmMandateDigitalTwin:
    return DpmMandateDigitalTwin(
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        mandate_version="3",
        as_of_date=date(2026, 5, 1),
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


def _exception() -> DpmMonitoringException:
    return DpmMonitoringException(
        exception_id="me_source_001",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        detected_at=datetime(2026, 5, 3, 8, 30, tzinfo=timezone.utc),
        as_of_date=date(2026, 5, 3),
        dimension=MandateHealthDimension.SOURCE_READINESS,
        severity=MonitoringSeverity.CRITICAL,
        reason_code="SOURCE_READINESS_BLOCKED",
        recommended_action=MandateRecommendedAction.FIX_SOURCE_DATA,
    )


def test_monitoring_run_id_for_uses_stable_utc_timestamp_shape() -> None:
    assert (
        monitoring_run_id_for(datetime(2026, 5, 3, 8, 30, 4, 123456))
        == "dmr_20260503_083004_123456"
    )


def test_increment_distribution_counts_existing_and_new_keys() -> None:
    distribution = {"READY": 1}

    increment_distribution(distribution, "READY")
    increment_distribution(distribution, "DEGRADED")

    assert distribution == {"READY": 2, "DEGRADED": 1}


def test_exceptions_for_monitoring_run_attaches_run_id_without_mutating_source() -> None:
    source_exception = _exception()

    exceptions = exceptions_for_monitoring_run(
        [source_exception],
        monitoring_run_id="dmr_20260503_083004_123456",
    )

    assert source_exception.monitoring_run_id is None
    assert exceptions[0].monitoring_run_id == "dmr_20260503_083004_123456"
    assert exceptions[0].exception_id == source_exception.exception_id


def test_calculate_monitoring_run_mandate_result_uses_requested_as_of_date_and_run_id() -> None:
    result = calculate_monitoring_run_mandate_result(
        twin=_twin(),
        as_of_date=date(2026, 5, 3),
        monitoring_run_id="dmr_20260503_083004_123456",
    )

    assert isinstance(result, DpmMonitoringRunMandateResult)
    assert result.health_snapshot.mandate_id == "MANDATE_PB_SG_GLOBAL_BAL_001"
    assert result.health_snapshot.as_of_date == date(2026, 5, 3)
    assert result.monitoring_exceptions
    assert {exception.monitoring_run_id for exception in result.monitoring_exceptions} == {
        "dmr_20260503_083004_123456"
    }


def test_monitoring_run_accumulator_counts_health_source_and_exceptions() -> None:
    result = calculate_monitoring_run_mandate_result(
        twin=_twin(),
        as_of_date=date(2026, 5, 3),
        monitoring_run_id="dmr_20260503_083004_123456",
    )
    accumulator = DpmMonitoringRunAccumulator.empty()

    accumulator.record(result)
    accumulator.record(result)

    assert accumulator.health_distribution == {result.health_snapshot.health_state.value: 2}
    assert accumulator.source_readiness_summary == {
        result.health_snapshot.source_readiness_state: 2
    }
    assert accumulator.exception_count == len(result.monitoring_exceptions) * 2


def test_build_monitoring_run_projects_terminal_success_summary() -> None:
    requested_at = datetime(2026, 5, 3, 8, 30, tzinfo=timezone.utc)
    completed_at = datetime(2026, 5, 3, 8, 30, 2, tzinfo=timezone.utc)

    run = build_monitoring_run(
        monitoring_run_id="dmr_20260503_083000_000000",
        as_of_date=date(2026, 5, 3),
        requested_at=requested_at,
        completed_at=completed_at,
        mandate_ids=["MANDATE_PB_SG_GLOBAL_BAL_001"],
        filters={"tenant_id": "default"},
        health_distribution={"PENDING_REVIEW": 1},
        exception_count=2,
        source_readiness_summary={"DEGRADED": 1},
    )

    assert run.monitoring_run_id == "dmr_20260503_083000_000000"
    assert run.status == "SUCCEEDED"
    assert run.total_mandates == 1
    assert run.requested_at == requested_at
    assert run.completed_at == completed_at
    assert run.health_distribution == {"PENDING_REVIEW": 1}
    assert run.source_readiness_summary == {"DEGRADED": 1}


def test_service_preserves_monitoring_run_helper_aliases() -> None:
    assert mandate_service.DpmMonitoringRunAccumulator is DpmMonitoringRunAccumulator
    assert mandate_service._monitoring_run_accumulator is DpmMonitoringRunAccumulator
    assert mandate_service.DpmMonitoringRunMandateResult is DpmMonitoringRunMandateResult
    assert mandate_service._monitoring_run_id_for is monitoring_run_id_for
    assert mandate_service._increment_distribution is increment_distribution
    assert mandate_service._exceptions_for_monitoring_run is exceptions_for_monitoring_run
    assert (
        mandate_service._calculate_monitoring_run_mandate_result
        is calculate_monitoring_run_mandate_result
    )
    assert mandate_service._build_monitoring_run is build_monitoring_run


def test_monitoring_run_helper_exports_public_surface() -> None:
    assert set(mandate_monitoring_run.__all__) == {
        "DpmMonitoringRunAccumulator",
        "DpmMonitoringRunMandateResult",
        "build_monitoring_run",
        "calculate_monitoring_run_mandate_result",
        "exceptions_for_monitoring_run",
        "increment_distribution",
        "monitoring_run_id_for",
    }
