from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from src.api.dependencies import get_mandate_repository
from src.api.main import app
from src.core.mandates import (
    DpmMandateConstraintSet,
    DpmMandateDigitalTwin,
    DpmMandateReviewPolicy,
    DpmMonitoringException,
    MandateHealthDimension,
    MandateRecommendedAction,
    MonitoringSeverity,
)
from src.infrastructure.mandates import InMemoryDpmMandateRepository


MANDATE_ID = "MANDATE_PB_SG_GLOBAL_BAL_001"
PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


def _twin() -> DpmMandateDigitalTwin:
    return DpmMandateDigitalTwin(
        mandate_id=MANDATE_ID,
        portfolio_id=PORTFOLIO_ID,
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


def _client(repository: InMemoryDpmMandateRepository) -> TestClient:
    app.dependency_overrides[get_mandate_repository] = lambda: repository
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_monitoring_run_once_persists_run_health_and_exception_queue() -> None:
    repository = InMemoryDpmMandateRepository()
    twin = _twin()
    repository.save_mandate_snapshot(twin)

    with _client(repository) as client:
        run_response = client.post(
            "/api/v1/dpm/monitoring/run-once",
            json={
                "mandate_ids": [MANDATE_ID],
                "as_of_date": "2026-05-03",
                "tenant_id": "default",
                "portfolio_manager_id": "PM_SG_001",
                "requested_by": "ops_sg_001",
            },
        )
        runs_response = client.get("/api/v1/dpm/monitoring/runs?status_filter=SUCCEEDED")
        run_id = run_response.json()["monitoring_run_id"]
        run_detail = client.get(f"/api/v1/dpm/monitoring/runs/{run_id}")
        exceptions_response = client.get(
            f"/api/v1/dpm/exceptions?mandate_id={MANDATE_ID}&portfolio_id={PORTFOLIO_ID}"
        )

    assert run_response.status_code == 200
    assert run_response.json()["total_mandates"] == 1
    assert run_response.json()["health_distribution"]["PENDING_REVIEW"] == 1
    assert runs_response.status_code == 200
    assert runs_response.json()["items"][0]["monitoring_run_id"] == run_id
    assert run_detail.status_code == 200
    assert exceptions_response.status_code == 200
    assert exceptions_response.json()["items"]
    assert exceptions_response.json()["items"][0]["monitoring_run_id"] == run_id


def test_command_center_summarizes_latest_monitoring_run_and_attention_queue() -> None:
    repository = InMemoryDpmMandateRepository()
    twin = _twin()
    repository.save_mandate_snapshot(twin)

    with _client(repository) as client:
        run_response = client.post(
            "/api/v1/dpm/monitoring/run-once",
            json={
                "mandate_ids": [MANDATE_ID],
                "as_of_date": "2026-05-03",
                "tenant_id": "default",
                "portfolio_manager_id": "PM_SG_001",
                "requested_by": "ops_sg_001",
            },
        )
        run_id = run_response.json()["monitoring_run_id"]
        repository.save_monitoring_exception(
            DpmMonitoringException(
                exception_id="me_info_source_data",
                monitoring_run_id=run_id,
                mandate_id=MANDATE_ID,
                portfolio_id=PORTFOLIO_ID,
                detected_at=datetime(2026, 5, 3, 8, 30, tzinfo=timezone.utc),
                as_of_date=date(2026, 5, 3),
                dimension=MandateHealthDimension.SOURCE_READINESS,
                severity=MonitoringSeverity.INFO,
                reason_code="SOURCE_READINESS_INFO",
                recommended_action=MandateRecommendedAction.FIX_SOURCE_DATA,
            )
        )
        repository.save_monitoring_exception(
            DpmMonitoringException(
                exception_id="me_critical_source_data",
                monitoring_run_id=run_id,
                mandate_id=MANDATE_ID,
                portfolio_id=PORTFOLIO_ID,
                detected_at=datetime(2026, 5, 3, 8, 31, tzinfo=timezone.utc),
                as_of_date=date(2026, 5, 3),
                dimension=MandateHealthDimension.SOURCE_READINESS,
                severity=MonitoringSeverity.CRITICAL,
                reason_code="SOURCE_READINESS_BLOCKED",
                recommended_action=MandateRecommendedAction.FIX_SOURCE_DATA,
            )
        )
        repository.save_monitoring_exception(
            DpmMonitoringException(
                exception_id="me_unrelated_newer_exception",
                monitoring_run_id="dmr_unrelated_20260503_090000",
                mandate_id=MANDATE_ID,
                portfolio_id=PORTFOLIO_ID,
                detected_at=datetime(2026, 5, 3, 9, 0, tzinfo=timezone.utc),
                as_of_date=date(2026, 5, 3),
                dimension=MandateHealthDimension.SOURCE_READINESS,
                severity=MonitoringSeverity.CRITICAL,
                reason_code="UNRELATED_LATER_RUN",
                recommended_action=MandateRecommendedAction.FIX_SOURCE_DATA,
            )
        )
        command_center = client.get(
            "/api/v1/dpm/command-center"
            "?tenant_id=default"
            "&portfolio_manager_id=PM_SG_001"
            "&as_of_date=2026-05-03"
            "&health_state=PENDING_REVIEW"
        )
        limited_command_center = client.get(
            "/api/v1/dpm/command-center"
            "?tenant_id=default"
            "&portfolio_manager_id=PM_SG_001"
            "&as_of_date=2026-05-03"
            "&limit=1"
        )
        partial_book = client.get("/api/v1/dpm/command-center?tenant_id=default&limit=1")
        empty_book = client.get(
            "/api/v1/dpm/command-center"
            "?tenant_id=default"
            "&portfolio_manager_id=PM_SG_001"
            "&as_of_date=2026-05-04"
        )

    payload = command_center.json()
    assert run_response.status_code == 200
    assert command_center.status_code == 200
    assert payload["evaluated_mandates"] == 1
    assert payload["health_distribution"] == {"PENDING_REVIEW": 1}
    assert payload["active_exception_count"] == run_response.json()["exception_count"] + 2
    assert payload["attention_buckets"][0]["exception_count"] >= 1
    assert payload["recommended_actions"][0]["recommended_action"] == "FIX_SOURCE_DATA"
    assert payload["recommended_actions"][0]["highest_severity"] == "CRITICAL"
    assert payload["supportability"]["data_completeness_state"] == "COMPLETE"
    assert payload["supportability"]["source_run_id"] == run_response.json()["monitoring_run_id"]
    assert limited_command_center.status_code == 200
    assert limited_command_center.json()["active_exception_count"] == 1
    assert limited_command_center.json()["supportability"]["source_run_id"] == run_id
    assert partial_book.status_code == 200
    assert partial_book.json()["supportability"]["data_completeness_state"] == "PARTIAL"
    assert (
        "PM_BOOK_DISCOVERY_NOT_YET_SOURCED"
        in partial_book.json()["supportability"]["partial_readiness_reasons"]
    )
    assert (
        "ATTENTION_QUEUE_LIMIT_REACHED"
        in partial_book.json()["supportability"]["partial_readiness_reasons"]
    )
    assert empty_book.status_code == 200
    assert empty_book.json()["supportability"]["data_completeness_state"] == "EMPTY"
    assert (
        "NO_MONITORING_RUN_FOR_COMMAND_CENTER_FILTERS"
        in empty_book.json()["supportability"]["partial_readiness_reasons"]
    )


def test_monitoring_run_and_exception_error_paths_and_resolution() -> None:
    repository = InMemoryDpmMandateRepository()
    repository.save_mandate_snapshot(_twin())

    with _client(repository) as client:
        missing_run_once = client.post(
            "/api/v1/dpm/monitoring/run-once",
            json={"mandate_ids": ["UNKNOWN"], "as_of_date": "2026-05-03"},
        )
        missing_run = client.get("/api/v1/dpm/monitoring/runs/UNKNOWN")
        client.post(
            "/api/v1/dpm/monitoring/run-once",
            json={"mandate_ids": [MANDATE_ID], "as_of_date": "2026-05-03"},
        )
        exception_id = client.get("/api/v1/dpm/exceptions").json()["items"][0]["exception_id"]
        resolved = client.post(
            f"/api/v1/dpm/exceptions/{exception_id}/resolve",
            json={"resolution_reason": "PM_CONFIRMED_EXIT_REQUIRED"},
        )
        missing_exception = client.post(
            "/api/v1/dpm/exceptions/UNKNOWN/resolve",
            json={"resolution_reason": "NOT_FOUND"},
        )

    assert missing_run_once.status_code == 404
    assert missing_run.status_code == 404
    assert resolved.status_code == 200
    assert resolved.json()["state"] == "RESOLVED"
    assert missing_exception.status_code == 404
