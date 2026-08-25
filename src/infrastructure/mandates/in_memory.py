from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from threading import Lock
from typing import Optional

from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import (
    DpmMandateDigitalTwin,
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
    DpmMonitoringRun,
)


class InMemoryDpmMandateRepository(DpmMandateRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._mandates_by_key: dict[tuple[str, str], DpmMandateDigitalTwin] = {}
        self._health_snapshots: dict[str, DpmMandateHealthSnapshot] = {}
        self._monitoring_runs: dict[str, DpmMonitoringRun] = {}
        self._exceptions: dict[str, DpmMonitoringException] = {}

    def save_mandate_snapshot(self, twin: DpmMandateDigitalTwin) -> None:
        with self._lock:
            self._mandates_by_key[(twin.mandate_id, twin.mandate_version)] = deepcopy(twin)

    def get_latest_mandate_by_portfolio(
        self,
        *,
        portfolio_id: str,
    ) -> Optional[DpmMandateDigitalTwin]:
        with self._lock:
            rows = [
                twin for twin in self._mandates_by_key.values() if twin.portfolio_id == portfolio_id
            ]
            latest = _latest_twin(rows)
            return deepcopy(latest) if latest is not None else None

    def get_mandate_by_portfolio_as_of(
        self,
        *,
        portfolio_id: str,
        as_of_date: date,
    ) -> Optional[DpmMandateDigitalTwin]:
        with self._lock:
            rows = [
                twin
                for twin in self._mandates_by_key.values()
                if twin.portfolio_id == portfolio_id and twin.as_of_date <= as_of_date
            ]
            latest = _latest_twin(rows)
            return deepcopy(latest) if latest is not None else None

    def get_latest_mandate(
        self,
        *,
        mandate_id: str,
    ) -> Optional[DpmMandateDigitalTwin]:
        with self._lock:
            rows = [
                twin for twin in self._mandates_by_key.values() if twin.mandate_id == mandate_id
            ]
            latest = _latest_twin(rows)
            return deepcopy(latest) if latest is not None else None

    def list_mandate_versions(
        self,
        *,
        mandate_id: str,
    ) -> list[DpmMandateDigitalTwin]:
        with self._lock:
            rows = [
                twin for twin in self._mandates_by_key.values() if twin.mandate_id == mandate_id
            ]
            rows = sorted(rows, key=lambda row: (row.as_of_date, row.mandate_version), reverse=True)
            return [deepcopy(row) for row in rows]

    def save_health_snapshot(self, snapshot: DpmMandateHealthSnapshot) -> None:
        with self._lock:
            self._health_snapshots[snapshot.health_snapshot_id] = deepcopy(snapshot)

    def get_latest_health_snapshot(
        self,
        *,
        mandate_id: str,
    ) -> Optional[DpmMandateHealthSnapshot]:
        with self._lock:
            rows = [
                snapshot
                for snapshot in self._health_snapshots.values()
                if snapshot.mandate_id == mandate_id
            ]
            if not rows:
                return None
            latest = max(rows, key=lambda row: (row.calculated_at, row.health_snapshot_id))
            return deepcopy(latest)

    def get_health_snapshot_as_of(
        self,
        *,
        mandate_id: str,
        as_of_date: date,
    ) -> Optional[DpmMandateHealthSnapshot]:
        with self._lock:
            rows = [
                snapshot
                for snapshot in self._health_snapshots.values()
                if snapshot.mandate_id == mandate_id and snapshot.as_of_date <= as_of_date
            ]
            if not rows:
                return None
            latest = max(
                rows,
                key=lambda row: (row.as_of_date, row.calculated_at, row.health_snapshot_id),
            )
            return deepcopy(latest)

    def save_monitoring_exception(self, exception: DpmMonitoringException) -> None:
        with self._lock:
            self._exceptions[exception.exception_id] = deepcopy(exception)

    def save_monitoring_run(self, run: DpmMonitoringRun) -> None:
        with self._lock:
            self._monitoring_runs[run.monitoring_run_id] = deepcopy(run)

    def get_monitoring_run(
        self,
        *,
        monitoring_run_id: str,
    ) -> Optional[DpmMonitoringRun]:
        with self._lock:
            run = self._monitoring_runs.get(monitoring_run_id)
            return deepcopy(run) if run is not None else None

    def list_monitoring_runs(
        self,
        *,
        status: Optional[str],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[DpmMonitoringRun], Optional[str]]:
        with self._lock:
            rows = list(self._monitoring_runs.values())
            if status is not None:
                rows = [row for row in rows if row.status == status]
            rows = sorted(
                rows, key=lambda row: (row.requested_at, row.monitoring_run_id), reverse=True
            )
            if cursor is not None:
                cursor_index = next(
                    (index for index, row in enumerate(rows) if row.monitoring_run_id == cursor),
                    None,
                )
                if cursor_index is None:
                    return [], None
                rows = rows[cursor_index + 1 :]
            page = rows[:limit]
            next_cursor = page[-1].monitoring_run_id if len(rows) > limit else None
            return [deepcopy(row) for row in page], next_cursor

    def list_monitoring_exceptions(
        self,
        *,
        monitoring_run_id: Optional[str],
        mandate_id: Optional[str],
        portfolio_id: Optional[str],
        state: Optional[str],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[DpmMonitoringException], Optional[str]]:
        with self._lock:
            rows = _filtered_monitoring_exceptions(
                list(self._exceptions.values()),
                monitoring_run_id=monitoring_run_id,
                mandate_id=mandate_id,
                portfolio_id=portfolio_id,
                state=state,
            )
            page, next_cursor = _monitoring_exception_page(
                rows,
                limit=limit,
                cursor=cursor,
            )
            return [deepcopy(row) for row in page], next_cursor

    def resolve_monitoring_exception(
        self,
        *,
        exception_id: str,
        resolved_at: datetime,
        resolution_reason: str,
    ) -> Optional[DpmMonitoringException]:
        with self._lock:
            exception = self._exceptions.get(exception_id)
            if exception is None:
                return None
            resolved = exception.model_copy(
                update={
                    "state": "RESOLVED",
                    "resolved_at": resolved_at,
                    "resolution_reason": resolution_reason,
                }
            )
            self._exceptions[exception_id] = resolved
            return deepcopy(resolved)

    def purge_mandate_records_before(self, *, cutoff: datetime) -> int:
        cutoff_utc = cutoff.astimezone(timezone.utc)
        with self._lock:
            mandate_keys = _stale_mandate_keys(self._mandates_by_key, cutoff_utc)
            health_keys = _stale_health_snapshot_keys(self._health_snapshots, cutoff_utc)
            run_keys = _stale_monitoring_run_keys(self._monitoring_runs, cutoff_utc)
            exception_keys = _stale_resolved_exception_keys(self._exceptions, cutoff_utc)
            for mandate_key in mandate_keys:
                self._mandates_by_key.pop(mandate_key, None)
            for health_key in health_keys:
                self._health_snapshots.pop(health_key, None)
            for run_key in run_keys:
                self._monitoring_runs.pop(run_key, None)
            for exception_key in exception_keys:
                self._exceptions.pop(exception_key, None)
            return len(mandate_keys) + len(health_keys) + len(run_keys) + len(exception_keys)


def _latest_twin(rows: list[DpmMandateDigitalTwin]) -> Optional[DpmMandateDigitalTwin]:
    if not rows:
        return None
    return max(rows, key=lambda row: (row.as_of_date, row.mandate_version, row.mandate_id))


def _stale_mandate_keys(
    mandates: dict[tuple[str, str], DpmMandateDigitalTwin],
    cutoff_utc: datetime,
) -> list[tuple[str, str]]:
    return [
        key
        for key, twin in mandates.items()
        if datetime.combine(twin.as_of_date, datetime.min.time(), timezone.utc) < cutoff_utc
    ]


def _stale_health_snapshot_keys(
    snapshots: dict[str, DpmMandateHealthSnapshot],
    cutoff_utc: datetime,
) -> list[str]:
    return [key for key, snapshot in snapshots.items() if snapshot.calculated_at < cutoff_utc]


def _stale_monitoring_run_keys(
    runs: dict[str, DpmMonitoringRun],
    cutoff_utc: datetime,
) -> list[str]:
    return [key for key, run in runs.items() if run.requested_at < cutoff_utc]


def _stale_resolved_exception_keys(
    exceptions: dict[str, DpmMonitoringException],
    cutoff_utc: datetime,
) -> list[str]:
    return [
        key
        for key, exception in exceptions.items()
        if exception.detected_at < cutoff_utc
        and (exception.state == "RESOLVED" or exception.resolved_at is not None)
    ]


def _filtered_monitoring_exceptions(
    rows: list[DpmMonitoringException],
    *,
    monitoring_run_id: Optional[str],
    mandate_id: Optional[str],
    portfolio_id: Optional[str],
    state: Optional[str],
) -> list[DpmMonitoringException]:
    filtered = [
        row
        for row in rows
        if _monitoring_exception_matches(
            row,
            monitoring_run_id=monitoring_run_id,
            mandate_id=mandate_id,
            portfolio_id=portfolio_id,
            state=state,
        )
    ]
    return sorted(
        filtered,
        key=lambda row: (row.detected_at, row.exception_id),
        reverse=True,
    )


def _monitoring_exception_matches(
    row: DpmMonitoringException,
    *,
    monitoring_run_id: Optional[str],
    mandate_id: Optional[str],
    portfolio_id: Optional[str],
    state: Optional[str],
) -> bool:
    return (
        _matches_optional_filter(row.monitoring_run_id, monitoring_run_id)
        and _matches_optional_filter(row.mandate_id, mandate_id)
        and _matches_optional_filter(row.portfolio_id, portfolio_id)
        and _matches_optional_filter(row.state, state)
    )


def _matches_optional_filter(value: object, expected: object | None) -> bool:
    return expected is None or value == expected


def _monitoring_exception_page(
    rows: list[DpmMonitoringException],
    *,
    limit: int,
    cursor: Optional[str],
) -> tuple[list[DpmMonitoringException], Optional[str]]:
    if cursor is not None:
        cursor_index = _monitoring_exception_cursor_index(rows, cursor)
        if cursor_index is None:
            return [], None
        rows = rows[cursor_index + 1 :]
    page = rows[:limit]
    next_cursor = page[-1].exception_id if len(rows) > limit else None
    return page, next_cursor


def _monitoring_exception_cursor_index(
    rows: list[DpmMonitoringException],
    cursor: str,
) -> Optional[int]:
    return next(
        (index for index, row in enumerate(rows) if row.exception_id == cursor),
        None,
    )
