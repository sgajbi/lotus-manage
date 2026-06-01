from datetime import date, datetime, timezone

from src.api.services import mandate_monitoring_run, mandate_service
from src.api.services.mandate_monitoring_run import (
    build_monitoring_run,
    exceptions_for_monitoring_run,
    increment_distribution,
    monitoring_run_id_for,
)
from src.core.mandates import (
    DpmMonitoringException,
    MandateHealthDimension,
    MandateRecommendedAction,
    MonitoringSeverity,
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
    assert mandate_service._monitoring_run_id_for is monitoring_run_id_for
    assert mandate_service._increment_distribution is increment_distribution
    assert mandate_service._exceptions_for_monitoring_run is exceptions_for_monitoring_run
    assert mandate_service._build_monitoring_run is build_monitoring_run


def test_monitoring_run_helper_exports_public_surface() -> None:
    assert set(mandate_monitoring_run.__all__) == {
        "build_monitoring_run",
        "exceptions_for_monitoring_run",
        "increment_distribution",
        "monitoring_run_id_for",
    }
