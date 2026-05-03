from datetime import datetime, timezone
from pathlib import Path

import pytest

import src.infrastructure.waves.postgres as postgres_module
from src.core.waves import (
    DpmWaveAlreadyExistsError,
    DpmRebalanceWave,
    DpmRebalanceWaveEvent,
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveIdempotencyConflictError,
    DpmWaveInvalidTransitionError,
    DpmWaveTrigger,
    DpmWaveVersionConflictError,
    WaveState,
    apply_wave_transition,
    validate_wave_transition,
)
from src.infrastructure.waves import InMemoryDpmWaveRepository
from src.infrastructure.waves.postgres import PostgresDpmWaveRepository


ROOT = Path(__file__).resolve().parents[4]


def _wave() -> DpmRebalanceWave:
    item = DpmRebalanceWaveItem(
        wave_item_id="dwi_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        state="CANDIDATE",
    )
    return DpmRebalanceWave(
        wave_id="dwv_001",
        state="DRAFT",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-wave-001",
            rationale="Review the explicitly supplied affected portfolio list.",
        ),
        as_of_date="2026-05-03",
        created_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
        created_by="pm-ops",
        correlation_id="corr-wave-001",
        items=[item],
        aggregate_metrics=DpmWaveAggregateMetrics(
            item_count=1,
            state_counts={"CANDIDATE": 1},
            ready_item_count=0,
            blocked_item_count=0,
            review_required_item_count=0,
            source_degraded_item_count=0,
        ),
    )


def _event(from_state: WaveState, to_state: WaveState) -> DpmRebalanceWaveEvent:
    return DpmRebalanceWaveEvent(
        event_id=f"evt-{from_state.lower()}-{to_state.lower()}",
        wave_id="dwv_001",
        from_state=from_state,
        to_state=to_state,
        event_type="STATE_TRANSITION",
        actor_id="pm-ops",
        reason_code=f"{to_state}_REQUESTED",
        correlation_id="corr-wave-001",
        created_at=datetime(2026, 5, 3, 1, tzinfo=timezone.utc),
    )


def test_wave_state_machine_allows_governed_transition_and_appends_event() -> None:
    wave = _wave()

    updated = apply_wave_transition(
        wave=wave,
        to_state="PREVIEWED",
        event=_event("DRAFT", "PREVIEWED"),
    )

    assert updated.state == "PREVIEWED"
    assert updated.version == 2
    assert [event.event_id for event in updated.events] == ["evt-draft-previewed"]
    assert wave.state == "DRAFT"
    assert wave.events == []


def test_wave_state_machine_rejects_ungoverned_jump() -> None:
    with pytest.raises(DpmWaveInvalidTransitionError) as exc:
        validate_wave_transition(from_state="DRAFT", to_state="STAGED")

    assert str(exc.value) == "DPM_WAVE_INVALID_TRANSITION:DRAFT->STAGED"


def test_wave_transition_requires_matching_event_state() -> None:
    with pytest.raises(DpmWaveInvalidTransitionError) as exc:
        apply_wave_transition(
            wave=_wave(),
            to_state="PREVIEWED",
            event=_event("CREATED", "PREVIEWED"),
        )

    assert str(exc.value) == "DPM_WAVE_EVENT_FROM_STATE_MISMATCH"


def test_in_memory_wave_repository_is_defensive_and_version_guarded() -> None:
    repository = InMemoryDpmWaveRepository()
    wave = _wave()
    repository.save_wave(wave=wave, idempotency_key="idem-1", request_hash="hash-1")

    loaded = repository.get_wave(wave_id=wave.wave_id)
    assert loaded is not None
    loaded.items[0].state = "SOURCE_BLOCKED"

    reloaded = repository.get_wave(wave_id=wave.wave_id)
    assert reloaded is not None
    assert reloaded.items[0].state == "CANDIDATE"

    updated = apply_wave_transition(
        wave=reloaded,
        to_state="PREVIEWED",
        event=_event("DRAFT", "PREVIEWED"),
    )
    repository.update_wave(wave=updated, expected_version=1)
    assert repository.get_wave(wave_id=wave.wave_id).version == 2  # type: ignore[union-attr]

    with pytest.raises(DpmWaveVersionConflictError):
        repository.update_wave(wave=updated, expected_version=1)


def test_in_memory_wave_repository_enforces_idempotency_conflict() -> None:
    repository = InMemoryDpmWaveRepository()
    repository.save_wave(wave=_wave(), idempotency_key="idem-1", request_hash="hash-1")

    conflicting = _wave().model_copy(update={"wave_id": "dwv_002"}, deep=True)
    with pytest.raises(DpmWaveIdempotencyConflictError):
        repository.save_wave(
            wave=conflicting,
            idempotency_key="idem-1",
            request_hash="hash-2",
        )


def test_in_memory_wave_repository_rejects_duplicate_wave_id() -> None:
    repository = InMemoryDpmWaveRepository()
    wave = _wave()
    repository.save_wave(wave=wave, idempotency_key="idem-1", request_hash="hash-1")

    with pytest.raises(DpmWaveAlreadyExistsError):
        repository.save_wave(wave=wave, idempotency_key="idem-2", request_hash="hash-2")


def test_in_memory_wave_repository_replays_idempotent_wave() -> None:
    repository = InMemoryDpmWaveRepository()
    wave = _wave()
    repository.save_wave(wave=wave, idempotency_key="idem-1", request_hash="hash-1")

    replay = repository.get_wave_by_idempotency(idempotency_key="idem-1")

    assert replay == wave


def test_wave_postgres_migration_declares_persistence_tables() -> None:
    migration = (
        ROOT / "src" / "infrastructure" / "postgres_migrations" / "dpm" / "0007_rebalance_waves.sql"
    ).read_text(encoding="utf-8")

    required_tokens = [
        "CREATE TABLE IF NOT EXISTS dpm_rebalance_waves",
        "wave_json JSONB NOT NULL",
        "CREATE TABLE IF NOT EXISTS dpm_rebalance_wave_idempotency",
        "CREATE TABLE IF NOT EXISTS dpm_rebalance_wave_events",
        "idx_dpm_rebalance_wave_events_wave_created",
    ]
    assert [token for token in required_tokens if token not in migration] == []


def test_postgres_wave_repository_initializes_migrations(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class FakeConnection:
        def close(self) -> None:
            calls.append("close")

    class FakePsycopg:
        @staticmethod
        def connect(dsn: str, *, row_factory: object) -> FakeConnection:
            assert dsn == "postgresql://example"
            assert row_factory == "dict_row"
            calls.append("connect")
            return FakeConnection()

    monkeypatch.setattr(postgres_module, "has_psycopg", lambda: True)
    monkeypatch.setattr(
        postgres_module,
        "_import_psycopg",
        lambda: (FakePsycopg, "dict_row"),
    )
    monkeypatch.setattr(
        postgres_module,
        "apply_postgres_migrations",
        lambda *, connection, namespace: calls.append(f"migrate:{namespace}"),
    )

    PostgresDpmWaveRepository(dsn="postgresql://example")

    assert calls == ["connect", "migrate:dpm", "close"]


class _FakeCursor:
    def __init__(self, row: dict[str, object] | None = None, rowcount: int = 0) -> None:
        self._row = row
        self.rowcount = rowcount

    def fetchone(self) -> dict[str, object] | None:
        return self._row


class _FakeWaveConnection:
    def __init__(self) -> None:
        self.waves: dict[str, dict[str, object]] = {}
        self.idempotency: dict[str, dict[str, object]] = {}
        self.events: dict[str, dict[str, object]] = {}
        self.commits = 0
        self.closed = 0

    def execute(self, query: str, args: tuple[object, ...]) -> _FakeCursor:
        sql = " ".join(str(query).split())
        if "SELECT wave_id, request_hash FROM dpm_rebalance_wave_idempotency" in sql:
            return _FakeCursor(self.idempotency.get(str(args[0])))
        if "INSERT INTO dpm_rebalance_waves" in sql:
            wave_id = str(args[0])
            if wave_id in self.waves:
                return _FakeCursor(rowcount=0)
            self.waves[wave_id] = {
                "wave_id": wave_id,
                "state": args[1],
                "version": args[7],
                "wave_json": args[8],
                "retention_policy": args[9],
            }
            return _FakeCursor(rowcount=1)
        if "INSERT INTO dpm_rebalance_wave_idempotency" in sql:
            self.idempotency[str(args[0])] = {
                "idempotency_key": args[0],
                "wave_id": args[1],
                "request_hash": args[2],
            }
            return _FakeCursor(rowcount=1)
        if "INSERT INTO dpm_rebalance_wave_events" in sql:
            self.events[str(args[0])] = {
                "event_id": args[0],
                "wave_id": args[1],
                "event_json": args[9],
            }
            return _FakeCursor(rowcount=1)
        if "SELECT wave_json FROM dpm_rebalance_waves WHERE wave_id = %s" in sql:
            return _FakeCursor(self.waves.get(str(args[0])))
        if "SELECT w.wave_json FROM dpm_rebalance_wave_idempotency" in sql:
            indexed = self.idempotency.get(str(args[0]))
            if indexed is None:
                return _FakeCursor()
            return _FakeCursor(self.waves.get(str(indexed["wave_id"])))
        if "UPDATE dpm_rebalance_waves" in sql:
            wave_id = str(args[4])
            row = self.waves.get(wave_id)
            if row is None or row["version"] != args[5]:
                return _FakeCursor(rowcount=0)
            row.update(
                {
                    "state": args[0],
                    "version": args[1],
                    "wave_json": args[2],
                    "retention_policy": args[3],
                }
            )
            return _FakeCursor(rowcount=1)
        raise AssertionError(f"Unexpected SQL: {sql}")

    def commit(self) -> None:
        self.commits += 1

    def close(self) -> None:
        self.closed += 1


def _postgres_repository(fake: _FakeWaveConnection) -> PostgresDpmWaveRepository:
    repository = object.__new__(PostgresDpmWaveRepository)
    repository._dsn = "postgresql://example"  # noqa: SLF001
    repository._connect = lambda: fake  # type: ignore[method-assign]  # noqa: SLF001
    return repository


def test_postgres_wave_repository_roundtrip_idempotency_and_update() -> None:
    fake = _FakeWaveConnection()
    repository = _postgres_repository(fake)
    wave = apply_wave_transition(
        wave=_wave(),
        to_state="PREVIEWED",
        event=_event("DRAFT", "PREVIEWED"),
    )

    repository.save_wave(wave=wave, idempotency_key="idem-1", request_hash="hash-1")
    loaded = repository.get_wave(wave_id=wave.wave_id)
    replay = repository.get_wave_by_idempotency(idempotency_key="idem-1")
    updated = apply_wave_transition(
        wave=wave,
        to_state="CREATED",
        event=_event("PREVIEWED", "CREATED"),
    )
    repository.update_wave(wave=updated, expected_version=2)

    assert loaded == wave
    assert replay == wave
    assert repository.get_wave(wave_id=wave.wave_id) == updated
    assert sorted(fake.events) == ["evt-draft-previewed", "evt-previewed-created"]
    assert fake.commits == 2
    assert fake.closed == 5


def test_postgres_wave_repository_conflicts() -> None:
    fake = _FakeWaveConnection()
    repository = _postgres_repository(fake)
    wave = _wave()
    repository.save_wave(wave=wave, idempotency_key="idem-1", request_hash="hash-1")

    with pytest.raises(DpmWaveAlreadyExistsError):
        repository.save_wave(wave=wave, idempotency_key="idem-2", request_hash="hash-2")
    with pytest.raises(DpmWaveIdempotencyConflictError):
        repository.save_wave(
            wave=wave.model_copy(update={"wave_id": "dwv_002"}, deep=True),
            idempotency_key="idem-1",
            request_hash="hash-2",
        )
    with pytest.raises(DpmWaveVersionConflictError):
        repository.update_wave(wave=wave, expected_version=99)


def test_postgres_wave_payload_accepts_non_string_json() -> None:
    fake = _FakeWaveConnection()
    repository = _postgres_repository(fake)
    wave = _wave()
    repository.save_wave(wave=wave, idempotency_key=None, request_hash=None)
    fake.waves[wave.wave_id]["wave_json"] = wave.model_dump(mode="json")

    assert repository.get_wave(wave_id=wave.wave_id) == wave
