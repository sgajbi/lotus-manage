from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from src.core.mandates import (
    DpmMandateConstraintSet,
    DpmMandateDigitalTwin,
    DpmMandateHealthSnapshot,
    DpmMandateHealthInput,
    DpmMandateReviewPolicy,
    MandateHealthDimension,
    MandateHealthState,
    calculate_mandate_health,
    monitoring_exceptions_from_health,
)
from src.infrastructure.mandates import InMemoryDpmMandateRepository
import src.infrastructure.mandates.postgres as mandate_postgres
from src.infrastructure.mandates.postgres import PostgresDpmMandateRepository
from src.infrastructure.mandates.serialization import dump_model_json, load_model_json


def _twin(*, version: str = "1", as_of: date = date(2026, 5, 3)) -> DpmMandateDigitalTwin:
    return DpmMandateDigitalTwin(
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        mandate_version=version,
        as_of_date=as_of,
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


def _health_snapshot(twin: DpmMandateDigitalTwin) -> DpmMandateHealthSnapshot:
    return calculate_mandate_health(
        DpmMandateHealthInput(
            twin=twin,
            current_weights={
                "EQ_US_AAPL": Decimal("0.60"),
                "FI_US_TREASURY_10Y": Decimal("0.40"),
            },
            target_weights={
                "EQ_US_AAPL": Decimal("0.60"),
                "FI_US_TREASURY_10Y": Decimal("0.40"),
            },
            cash_weight=Decimal("0.05"),
        )
    )


def test_repository_persists_mandate_versions_idempotently_and_lists_latest() -> None:
    repository = InMemoryDpmMandateRepository()
    old_twin = _twin(version="1", as_of=date(2026, 5, 1))
    latest_twin = _twin(version="2", as_of=date(2026, 5, 3))

    repository.save_mandate_snapshot(old_twin)
    repository.save_mandate_snapshot(latest_twin)
    repository.save_mandate_snapshot(latest_twin.model_copy(update={"risk_profile": "GROWTH"}))

    by_portfolio = repository.get_latest_mandate_by_portfolio(portfolio_id="PB_SG_GLOBAL_BAL_001")
    by_mandate = repository.get_latest_mandate(mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001")
    versions = repository.list_mandate_versions(mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001")

    assert by_portfolio is not None
    assert by_portfolio.mandate_version == "2"
    assert by_portfolio.risk_profile == "GROWTH"
    assert by_mandate is not None
    assert by_mandate.mandate_version == "2"
    assert [version.mandate_version for version in versions] == ["2", "1"]


def test_repository_returns_defensive_copies() -> None:
    repository = InMemoryDpmMandateRepository()
    repository.save_mandate_snapshot(_twin())

    stored = repository.get_latest_mandate(mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001")
    assert stored is not None
    stored.risk_profile = "MUTATED"

    reloaded = repository.get_latest_mandate(mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001")
    assert reloaded is not None
    assert reloaded.risk_profile == "BALANCED"


def test_repository_persists_latest_health_snapshot() -> None:
    repository = InMemoryDpmMandateRepository()
    twin = _twin()
    first = _health_snapshot(twin)
    second = first.model_copy(
        update={
            "health_snapshot_id": "mh_second",
            "calculated_at": first.calculated_at + timedelta(minutes=1),
            "health_score": 91,
        }
    )

    repository.save_health_snapshot(first)
    repository.save_health_snapshot(second)

    latest = repository.get_latest_health_snapshot(mandate_id=twin.mandate_id)
    assert latest is not None
    assert latest.health_snapshot_id == "mh_second"
    assert latest.health_score == 91


def test_repository_filters_pages_and_resolves_monitoring_exceptions() -> None:
    repository = InMemoryDpmMandateRepository()
    twin = _twin()
    snapshot = calculate_mandate_health(
        DpmMandateHealthInput(
            twin=twin,
            current_weights={"EQ_US_AAPL": Decimal("0.60")},
            target_weights={"EQ_US_AAPL": Decimal("0.60")},
            cash_weight=Decimal("0.05"),
            restricted_held_instruments=["EQ_RESTRICTED"],
        )
    )
    exceptions = monitoring_exceptions_from_health(snapshot, source_lineage=twin.source_lineage)
    assert exceptions
    repository.save_monitoring_exception(exceptions[0])

    rows, cursor = repository.list_monitoring_exceptions(
        mandate_id=twin.mandate_id,
        portfolio_id=twin.portfolio_id,
        state="ACTIVE",
        limit=1,
        cursor=None,
    )
    assert cursor is None
    assert rows[0].dimension == MandateHealthDimension.ELIGIBILITY_RESTRICTIONS

    resolved = repository.resolve_monitoring_exception(
        exception_id=rows[0].exception_id,
        resolved_at=datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc),
        resolution_reason="PM_CONFIRMED_EXIT_REQUIRED",
    )
    assert resolved is not None
    assert resolved.state == "RESOLVED"
    assert resolved.resolution_reason == "PM_CONFIRMED_EXIT_REQUIRED"

    active_rows, _ = repository.list_monitoring_exceptions(
        mandate_id=twin.mandate_id,
        portfolio_id=None,
        state="ACTIVE",
        limit=10,
        cursor=None,
    )
    assert active_rows == []

    missing_cursor_rows, missing_cursor = repository.list_monitoring_exceptions(
        mandate_id=twin.mandate_id,
        portfolio_id=None,
        state=None,
        limit=10,
        cursor="UNKNOWN_CURSOR",
    )
    assert missing_cursor_rows == []
    assert missing_cursor is None

    missing_resolution = repository.resolve_monitoring_exception(
        exception_id="UNKNOWN_EXCEPTION",
        resolved_at=datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc),
        resolution_reason="NOT_FOUND",
    )
    assert missing_resolution is None


def test_repository_retention_keeps_active_exceptions_but_purges_old_resolved_records() -> None:
    repository = InMemoryDpmMandateRepository()
    old_twin = _twin(as_of=date(2024, 1, 1))
    repository.save_mandate_snapshot(old_twin)
    old_health = _health_snapshot(old_twin).model_copy(
        update={"calculated_at": datetime(2024, 1, 1, tzinfo=timezone.utc)}
    )
    repository.save_health_snapshot(old_health)
    old_exception = monitoring_exceptions_from_health(
        calculate_mandate_health(
            DpmMandateHealthInput(
                twin=old_twin,
                cash_weight=Decimal("0.50"),
                current_weights={"EQ_US_AAPL": Decimal("0.60")},
                target_weights={"EQ_US_AAPL": Decimal("0.60")},
            )
        ),
        source_lineage=[],
    )[0].model_copy(update={"detected_at": datetime(2024, 1, 1, tzinfo=timezone.utc)})
    repository.save_monitoring_exception(old_exception)
    repository.resolve_monitoring_exception(
        exception_id=old_exception.exception_id,
        resolved_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
        resolution_reason="OLD_EXCEPTION_RESOLVED",
    )

    purged = repository.purge_mandate_records_before(
        cutoff=datetime(2025, 1, 1, tzinfo=timezone.utc)
    )

    assert purged == 3
    assert repository.get_latest_mandate(mandate_id=old_twin.mandate_id) is None
    assert repository.get_latest_health_snapshot(mandate_id=old_twin.mandate_id) is None
    rows, _ = repository.list_monitoring_exceptions(
        mandate_id=old_twin.mandate_id,
        portfolio_id=None,
        state=None,
        limit=10,
        cursor=None,
    )
    assert rows == []


def test_repository_serialization_round_trip_preserves_domain_types() -> None:
    snapshot = _health_snapshot(_twin())

    payload = dump_model_json(snapshot)
    reloaded = load_model_json(type(snapshot), payload)
    reloaded_from_dict = load_model_json(type(snapshot), snapshot.model_dump(mode="json"))

    assert reloaded.health_state == MandateHealthState.READY
    assert reloaded_from_dict.health_state == MandateHealthState.READY
    assert reloaded.dimension_scores[0].dimension in set(MandateHealthDimension)


class _FakeResult:
    def __init__(
        self,
        *,
        rows: list[dict[str, Any]] | None = None,
        rowcount: int = 0,
    ) -> None:
        self._rows = rows or []
        self.rowcount = rowcount

    def fetchone(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[dict[str, Any]]:
        return self._rows


class _FakePostgresStore:
    def __init__(self) -> None:
        self.mandates: dict[tuple[str, str], dict[str, Any]] = {}
        self.health: dict[str, dict[str, Any]] = {}
        self.exceptions: dict[str, dict[str, Any]] = {}
        self.deleted_rowcount = 2
        self.commits = 0
        self.migration_calls = 0


class _FakeConnection:
    def __init__(self, store: _FakePostgresStore) -> None:
        self.store = store
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def commit(self) -> None:
        self.store.commits += 1

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> _FakeResult:
        normalized = " ".join(query.split()).lower()
        if normalized.startswith("delete from"):
            return _FakeResult(rowcount=self.store.deleted_rowcount)
        if normalized.startswith("insert into dpm_mandate_snapshots"):
            row = {
                "mandate_id": params[1],
                "portfolio_id": params[2],
                "mandate_version": params[3],
                "as_of_date": params[4],
                "payload_json": params[7],
            }
            self.store.mandates[(str(params[1]), str(params[3]))] = row
            return _FakeResult(rowcount=1)
        if "from dpm_mandate_snapshots" in normalized:
            rows = list(self.store.mandates.values())
            if "where portfolio_id" in normalized:
                rows = [row for row in rows if row["portfolio_id"] == params[0]]
            if "where mandate_id" in normalized:
                rows = [row for row in rows if row["mandate_id"] == params[0]]
            rows = sorted(
                rows, key=lambda row: (row["as_of_date"], row["mandate_version"]), reverse=True
            )
            return _FakeResult(rows=[{"payload_json": row["payload_json"]} for row in rows])

        if normalized.startswith("insert into dpm_mandate_health_snapshots"):
            self.store.health[str(params[0])] = {
                "mandate_id": params[1],
                "created_at": params[10],
                "payload_json": params[9],
            }
            return _FakeResult(rowcount=1)
        if "from dpm_mandate_health_snapshots" in normalized:
            rows = [row for row in self.store.health.values() if row["mandate_id"] == params[0]]
            rows = sorted(rows, key=lambda row: row["created_at"], reverse=True)
            return _FakeResult(rows=[{"payload_json": row["payload_json"]} for row in rows])

        if normalized.startswith("insert into dpm_monitoring_exceptions"):
            self.store.exceptions[str(params[0])] = {
                "exception_id": params[0],
                "mandate_id": params[2],
                "portfolio_id": params[3],
                "state": params[8],
                "detected_at": params[17],
                "payload_json": params[16],
            }
            return _FakeResult(rowcount=1)
        if (
            "select payload_json from dpm_monitoring_exceptions" in normalized
            and "where exception_id" in normalized
        ):
            exception_row: dict[str, Any] | None = self.store.exceptions.get(str(params[0]))
            return (
                _FakeResult(rows=[{"payload_json": exception_row["payload_json"]}])
                if exception_row is not None
                else _FakeResult()
            )
        if "select payload_json, exception_id from dpm_monitoring_exceptions" in normalized:
            rows = list(self.store.exceptions.values())
            arg_index = 0
            if "mandate_id = %s" in normalized:
                rows = [row for row in rows if row["mandate_id"] == params[arg_index]]
                arg_index += 1
            if "portfolio_id = %s" in normalized:
                rows = [row for row in rows if row["portfolio_id"] == params[arg_index]]
                arg_index += 1
            if "state = %s" in normalized:
                rows = [row for row in rows if row["state"] == params[arg_index]]
                arg_index += 1
            if "exception_id < %s" in normalized:
                cursor = params[arg_index]
                arg_index += 3
                rows = [row for row in rows if row["exception_id"] < cursor]
            limit = int(params[-1])
            rows = sorted(
                rows, key=lambda row: (row["detected_at"], row["exception_id"]), reverse=True
            )
            rows = rows[:limit]
            return _FakeResult(
                rows=[
                    {"payload_json": row["payload_json"], "exception_id": row["exception_id"]}
                    for row in rows
                ]
            )
        raise AssertionError(f"Unexpected fake SQL: {query}")


class _FakePsycopg:
    def __init__(self, store: _FakePostgresStore) -> None:
        self.store = store

    def connect(self, _dsn: str, *, row_factory: object) -> _FakeConnection:
        assert row_factory == "dict_row"
        return _FakeConnection(self.store)


def _postgres_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[PostgresDpmMandateRepository, _FakePostgresStore]:
    store = _FakePostgresStore()
    monkeypatch.setattr(mandate_postgres, "has_psycopg", lambda: True)
    monkeypatch.setattr(
        mandate_postgres, "_import_psycopg", lambda: (_FakePsycopg(store), "dict_row")
    )
    monkeypatch.setattr(
        mandate_postgres,
        "apply_postgres_migrations",
        lambda *, connection, namespace: setattr(
            store, "migration_calls", store.migration_calls + 1
        ),
    )
    return PostgresDpmMandateRepository(dsn="postgresql://lotus.test/dpm"), store


def test_postgres_repository_requires_dsn_and_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(RuntimeError, match="DPM_MANDATE_POSTGRES_DSN_REQUIRED"):
        PostgresDpmMandateRepository(dsn="")

    monkeypatch.setattr(mandate_postgres, "has_psycopg", lambda: False)
    with pytest.raises(RuntimeError, match="DPM_MANDATE_POSTGRES_DRIVER_MISSING"):
        PostgresDpmMandateRepository(dsn="postgresql://lotus.test/dpm")


def test_postgres_repository_persists_reads_versions_and_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, store = _postgres_repository(monkeypatch)
    twin_v1 = _twin(version="1", as_of=date(2026, 5, 1))
    twin_v2 = _twin(version="2", as_of=date(2026, 5, 3))
    health = _health_snapshot(twin_v2)

    repository.save_mandate_snapshot(twin_v1)
    repository.save_mandate_snapshot(twin_v2)
    repository.save_health_snapshot(health)

    assert store.migration_calls == 1
    assert repository.get_latest_mandate_by_portfolio(portfolio_id=twin_v2.portfolio_id) == twin_v2
    assert repository.get_latest_mandate(mandate_id=twin_v2.mandate_id) == twin_v2
    assert [
        row.mandate_version
        for row in repository.list_mandate_versions(mandate_id=twin_v2.mandate_id)
    ] == [
        "2",
        "1",
    ]
    assert repository.get_latest_mandate(mandate_id="UNKNOWN") is None
    assert repository.get_latest_health_snapshot(mandate_id=twin_v2.mandate_id) == health
    assert repository.get_latest_health_snapshot(mandate_id="UNKNOWN") is None


def test_postgres_repository_lists_resolves_and_purges_exceptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, store = _postgres_repository(monkeypatch)
    twin = _twin()
    snapshot = calculate_mandate_health(
        DpmMandateHealthInput(
            twin=twin,
            current_weights={"EQ_US_AAPL": Decimal("0.60")},
            target_weights={"EQ_US_AAPL": Decimal("0.60")},
            cash_weight=Decimal("0.05"),
            restricted_held_instruments=["EQ_RESTRICTED"],
        )
    )
    exception = monitoring_exceptions_from_health(snapshot, source_lineage=twin.source_lineage)[0]
    second_exception = exception.model_copy(update={"exception_id": "me_second"})

    repository.save_monitoring_exception(exception)
    repository.save_monitoring_exception(second_exception)
    page, cursor = repository.list_monitoring_exceptions(
        mandate_id=twin.mandate_id,
        portfolio_id=twin.portfolio_id,
        state="ACTIVE",
        limit=1,
        cursor=None,
    )
    cursor_page, cursor_page_next = repository.list_monitoring_exceptions(
        mandate_id=twin.mandate_id,
        portfolio_id=twin.portfolio_id,
        state="ACTIVE",
        limit=1,
        cursor=page[0].exception_id,
    )
    resolved = repository.resolve_monitoring_exception(
        exception_id=page[0].exception_id,
        resolved_at=datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc),
        resolution_reason="PM_CONFIRMED_EXIT_REQUIRED",
    )
    missing = repository.resolve_monitoring_exception(
        exception_id="UNKNOWN",
        resolved_at=datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc),
        resolution_reason="NOT_FOUND",
    )
    removed = repository.purge_mandate_records_before(
        cutoff=datetime(2026, 5, 4, tzinfo=timezone.utc)
    )

    assert len(page) == 1
    assert cursor == page[0].exception_id
    assert len(cursor_page) == 1
    assert cursor_page_next is None
    assert resolved is not None
    assert resolved.state == "RESOLVED"
    assert resolved.resolution_reason == "PM_CONFIRMED_EXIT_REQUIRED"
    assert missing is None
    assert removed == store.deleted_rowcount * 3
    assert store.commits >= 4
