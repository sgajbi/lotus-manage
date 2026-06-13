from datetime import date, datetime, timezone

from src.api.services.mandate_command_center import (
    _normalized_source_readiness_states,
    _source_readiness_blocks_command_center,
    _source_readiness_degrades_command_center,
    _source_readiness_supportability_posture,
    attention_buckets,
    build_command_center_summary,
    command_center_completeness,
    command_center_health_distribution,
    command_center_partial_reasons,
    command_center_supportability_state,
    latest_command_center_run,
    recommended_actions,
    run_matches_command_center_filters,
    severity_rank,
)
from src.api.services import mandate_command_center
from src.core.mandates import (
    DpmMonitoringException,
    DpmMonitoringRun,
    MandateHealthDimension,
    MandateRecommendedAction,
    MonitoringSeverity,
)


def _run(
    *,
    source_readiness_summary: dict[str, int] | None = None,
    filters: dict[str, str] | None = None,
    as_of_date: date = date(2026, 5, 3),
) -> DpmMonitoringRun:
    return DpmMonitoringRun(
        monitoring_run_id="dmr_command_center",
        as_of_date=as_of_date,
        requested_at=datetime(2026, 5, 3, 8, 30, tzinfo=timezone.utc),
        completed_at=datetime(2026, 5, 3, 8, 31, tzinfo=timezone.utc),
        status="SUCCEEDED",
        total_mandates=2,
        exception_count=0,
        mandate_ids=["MANDATE_1", "MANDATE_2"],
        health_distribution={"READY": 1, "PENDING_REVIEW": 1},
        filters=filters or {},
        source_readiness_summary=source_readiness_summary or {"READY": 2},
    )


def _exception(
    *,
    exception_id: str,
    dimension: MandateHealthDimension,
    severity: MonitoringSeverity,
    action: MandateRecommendedAction,
    reason_code: str,
) -> DpmMonitoringException:
    return DpmMonitoringException(
        exception_id=exception_id,
        mandate_id=f"MANDATE_{exception_id}",
        portfolio_id=f"PB_{exception_id}",
        detected_at=datetime(2026, 5, 3, 8, 30, tzinfo=timezone.utc),
        as_of_date=date(2026, 5, 3),
        dimension=dimension,
        severity=severity,
        reason_code=reason_code,
        recommended_action=action,
    )


def test_command_center_supportability_state_maps_empty_and_source_postures() -> None:
    assert command_center_supportability_state(
        latest_run=None,
        completeness="EMPTY",
        partial_reasons=[],
    ) == ("EMPTY", "NO_MONITORING_RUN_FOR_COMMAND_CENTER_FILTERS")

    assert command_center_supportability_state(
        latest_run=_run(source_readiness_summary={"BLOCKED": 1}),
        completeness="COMPLETE",
        partial_reasons=[],
    ) == ("BLOCKED", "COMMAND_CENTER_SOURCE_READINESS_BLOCKED")

    assert command_center_supportability_state(
        latest_run=_run(source_readiness_summary={"DEGRADED": 1}),
        completeness="COMPLETE",
        partial_reasons=[],
    ) == ("DEGRADED", "COMMAND_CENTER_SOURCE_READINESS_DEGRADED")

    assert command_center_supportability_state(
        latest_run=_run(),
        completeness="PARTIAL",
        partial_reasons=["PM_BOOK_DISCOVERY_NOT_YET_SOURCED"],
    ) == ("PARTIAL", "PM_BOOK_DISCOVERY_NOT_YET_SOURCED")

    assert command_center_supportability_state(
        latest_run=_run(),
        completeness="COMPLETE",
        partial_reasons=[],
    ) == ("READY", "COMMAND_CENTER_READY")


def test_command_center_source_readiness_helpers_preserve_precedence() -> None:
    source_states = _normalized_source_readiness_states(
        {
            "ready": 2,
            "blocked": 1,
            "stale": 1,
        }
    )

    assert source_states == {"READY", "BLOCKED", "STALE"}
    assert _source_readiness_blocks_command_center(source_states)
    assert _source_readiness_degrades_command_center(source_states)
    assert _source_readiness_supportability_posture(
        source_readiness_summary={"STALE": 1, "BLOCKED": 1}
    ) == ("BLOCKED", "COMMAND_CENTER_SOURCE_READINESS_BLOCKED")
    assert _source_readiness_supportability_posture(source_readiness_summary={"STALE": 1}) == (
        "DEGRADED",
        "COMMAND_CENTER_SOURCE_READINESS_DEGRADED",
    )
    assert _source_readiness_supportability_posture(source_readiness_summary={"READY": 2}) is None


def test_run_matches_command_center_filters_uses_bounded_filter_values() -> None:
    run = _run(
        filters={
            "tenant_id": "tenant_1",
            "portfolio_manager_id": "pm_1",
            "book_id": "book_1",
        }
    )

    assert run_matches_command_center_filters(
        run,
        tenant_id="tenant_1",
        portfolio_manager_id="pm_1",
        book_id=None,
        as_of_date=date(2026, 5, 3),
    )
    assert not run_matches_command_center_filters(
        run,
        tenant_id="tenant_2",
        portfolio_manager_id=None,
        book_id=None,
        as_of_date=date(2026, 5, 3),
    )
    assert not run_matches_command_center_filters(
        run,
        tenant_id="tenant_1",
        portfolio_manager_id="pm_1",
        book_id=None,
        as_of_date=date(2026, 5, 4),
    )


def test_latest_command_center_run_returns_first_matching_run() -> None:
    latest = _run(
        filters={"tenant_id": "tenant_1", "portfolio_manager_id": "pm_1"},
        as_of_date=date(2026, 5, 3),
    )
    older = _run(
        filters={"tenant_id": "tenant_1", "portfolio_manager_id": "pm_1"},
        as_of_date=date(2026, 5, 2),
    )

    assert (
        latest_command_center_run(
            [latest, older],
            tenant_id="tenant_1",
            portfolio_manager_id="pm_1",
            book_id=None,
            as_of_date=None,
        )
        is latest
    )
    assert (
        latest_command_center_run(
            [latest, older],
            tenant_id="missing",
            portfolio_manager_id=None,
            book_id=None,
            as_of_date=None,
        )
        is None
    )


def test_attention_buckets_sort_by_severity_count_and_reason_frequency() -> None:
    exceptions = [
        _exception(
            exception_id="1",
            dimension=MandateHealthDimension.SOURCE_READINESS,
            severity=MonitoringSeverity.CRITICAL,
            action=MandateRecommendedAction.FIX_SOURCE_DATA,
            reason_code="SOURCE_BLOCKED_B",
        ),
        _exception(
            exception_id="2",
            dimension=MandateHealthDimension.SOURCE_READINESS,
            severity=MonitoringSeverity.CRITICAL,
            action=MandateRecommendedAction.FIX_SOURCE_DATA,
            reason_code="SOURCE_BLOCKED_A",
        ),
        _exception(
            exception_id="3",
            dimension=MandateHealthDimension.SOURCE_READINESS,
            severity=MonitoringSeverity.CRITICAL,
            action=MandateRecommendedAction.FIX_SOURCE_DATA,
            reason_code="SOURCE_BLOCKED_A",
        ),
        _exception(
            exception_id="4",
            dimension=MandateHealthDimension.MODEL_FRESHNESS,
            severity=MonitoringSeverity.WARNING,
            action=MandateRecommendedAction.SIMULATE_REBALANCE,
            reason_code="MODEL_STALE",
        ),
    ]

    buckets = attention_buckets(exceptions)

    assert buckets[0].severity == MonitoringSeverity.CRITICAL
    assert buckets[0].exception_count == 3
    assert buckets[0].top_reason_codes == ["SOURCE_BLOCKED_A", "SOURCE_BLOCKED_B"]
    assert buckets[1].severity == MonitoringSeverity.WARNING


def test_recommended_actions_sort_by_highest_severity_and_count() -> None:
    actions = recommended_actions(
        [
            _exception(
                exception_id="1",
                dimension=MandateHealthDimension.SOURCE_READINESS,
                severity=MonitoringSeverity.WARNING,
                action=MandateRecommendedAction.SIMULATE_REBALANCE,
                reason_code="MODEL_STALE",
            ),
            _exception(
                exception_id="2",
                dimension=MandateHealthDimension.WORKFLOW_READINESS,
                severity=MonitoringSeverity.CRITICAL,
                action=MandateRecommendedAction.REVIEW_WORKFLOW,
                reason_code="WORKFLOW_BLOCKED",
            ),
        ]
    )

    assert actions[0].recommended_action == MandateRecommendedAction.REVIEW_WORKFLOW
    assert actions[0].highest_severity == MonitoringSeverity.CRITICAL
    assert actions[1].recommended_action == MandateRecommendedAction.SIMULATE_REBALANCE


def test_build_command_center_summary_projects_supportability_and_attention() -> None:
    active_exceptions = [
        _exception(
            exception_id="1",
            dimension=MandateHealthDimension.SOURCE_READINESS,
            severity=MonitoringSeverity.CRITICAL,
            action=MandateRecommendedAction.FIX_SOURCE_DATA,
            reason_code="SOURCE_BLOCKED",
        )
    ]

    summary = build_command_center_summary(
        tenant_id="default",
        portfolio_manager_id=None,
        book_id=None,
        as_of_date=None,
        health_state="PENDING_REVIEW",
        latest_run=_run(),
        active_exceptions=active_exceptions,
        limit=1,
        generated_at=datetime(2026, 5, 3, 8, 32, tzinfo=timezone.utc),
    )

    assert summary.as_of_date == date(2026, 5, 3)
    assert summary.selected_health_state.value == "PENDING_REVIEW"
    assert summary.evaluated_mandates == 2
    assert summary.monitored_mandate_ids == ["MANDATE_1", "MANDATE_2"]
    assert summary.health_distribution == {"PENDING_REVIEW": 1}
    assert summary.active_exception_count == 1
    assert summary.attention_buckets[0].top_reason_codes == ["SOURCE_BLOCKED"]
    assert summary.recommended_actions[0].recommended_action == (
        MandateRecommendedAction.FIX_SOURCE_DATA
    )
    assert summary.supportability.state == "PARTIAL"
    assert summary.supportability.reason == "PM_BOOK_DISCOVERY_NOT_YET_SOURCED"
    assert summary.supportability.source_run_id == "dmr_command_center"
    assert summary.supportability.partial_readiness_reasons == [
        "PM_BOOK_DISCOVERY_NOT_YET_SOURCED",
        "ATTENTION_QUEUE_LIMIT_REACHED",
    ]


def test_build_command_center_summary_projects_empty_state_without_run() -> None:
    summary = build_command_center_summary(
        tenant_id=None,
        portfolio_manager_id=None,
        book_id=None,
        as_of_date=None,
        health_state=None,
        latest_run=None,
        active_exceptions=[],
        limit=50,
        generated_at=datetime(2026, 5, 3, 8, 32, tzinfo=timezone.utc),
    )

    assert summary.as_of_date is None
    assert summary.evaluated_mandates == 0
    assert summary.health_distribution == {}
    assert summary.supportability.state == "EMPTY"
    assert summary.supportability.reason == "NO_MONITORING_RUN_FOR_COMMAND_CENTER_FILTERS"


def test_command_center_read_model_collects_projection_state_without_exporting_it() -> None:
    read_model = mandate_command_center._command_center_read_model(
        health_state="PENDING_REVIEW",
        latest_run=_run(),
        portfolio_manager_id=None,
        book_id=None,
        active_exception_count=50,
        limit=50,
    )

    assert read_model.health_distribution == {"PENDING_REVIEW": 1}
    assert read_model.partial_reasons == [
        "PM_BOOK_DISCOVERY_NOT_YET_SOURCED",
        "ATTENTION_QUEUE_LIMIT_REACHED",
    ]
    assert read_model.completeness == "PARTIAL"
    assert read_model.supportability_state == "PARTIAL"
    assert read_model.supportability_reason == "PM_BOOK_DISCOVERY_NOT_YET_SOURCED"
    assert "_command_center_read_model" not in mandate_command_center.__all__


def test_command_center_projection_helpers_preserve_empty_and_latest_run_defaults() -> None:
    run = _run()

    assert mandate_command_center._command_center_as_of_date(
        as_of_date=date(2026, 5, 4),
        latest_run=run,
    ) == date(2026, 5, 4)
    assert mandate_command_center._command_center_as_of_date(
        as_of_date=None,
        latest_run=run,
    ) == date(2026, 5, 3)
    assert mandate_command_center._selected_health_state("READY").value == "READY"
    assert mandate_command_center._selected_health_state(None) is None
    assert mandate_command_center._evaluated_mandates(None) == 0
    assert mandate_command_center._monitored_mandate_ids(run) == ["MANDATE_1", "MANDATE_2"]
    assert mandate_command_center._source_readiness_summary(None) == {}


def test_command_center_health_distribution_filters_selected_state() -> None:
    assert command_center_health_distribution(
        latest_run=_run(),
        health_state="PENDING_REVIEW",
    ) == {"PENDING_REVIEW": 1}
    assert command_center_health_distribution(
        latest_run=None,
        health_state="READY",
    ) == {"READY": 0}


def test_command_center_partial_reasons_name_discovery_limit_and_missing_run() -> None:
    assert command_center_partial_reasons(
        latest_run=None,
        portfolio_manager_id=None,
        book_id=None,
        active_exception_count=10,
        limit=10,
    ) == [
        "NO_MONITORING_RUN_FOR_COMMAND_CENTER_FILTERS",
        "PM_BOOK_DISCOVERY_NOT_YET_SOURCED",
        "ATTENTION_QUEUE_LIMIT_REACHED",
    ]


def test_command_center_completeness_classifies_empty_partial_and_complete() -> None:
    assert command_center_completeness(latest_run=None, partial_reasons=[]) == "EMPTY"
    assert (
        command_center_completeness(
            latest_run=_run(),
            partial_reasons=["PM_BOOK_DISCOVERY_NOT_YET_SOURCED"],
        )
        == "PARTIAL"
    )
    assert command_center_completeness(latest_run=_run(), partial_reasons=[]) == "COMPLETE"


def test_mandate_command_center_exports_only_projection_helpers() -> None:
    assert severity_rank("CRITICAL") == 3
    assert mandate_command_center.__all__ == [
        "attention_buckets",
        "build_command_center_summary",
        "command_center_completeness",
        "command_center_health_distribution",
        "command_center_partial_reasons",
        "command_center_supportability_state",
        "latest_command_center_run",
        "recommended_actions",
        "run_matches_command_center_filters",
        "severity_rank",
    ]
