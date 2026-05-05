from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.core.outcomes import (
    DpmExpectedOutcomeSnapshot,
    DpmOutcomeEvent,
    DpmOutcomeMetricValue,
    DpmOutcomeReviewWindow,
    DpmOutcomeSourceFreshness,
    DpmOutcomeSourceRef,
    DpmOutcomeSupportability,
    DpmOutcomeTolerance,
    DpmPostTradeOutcomeReview,
    DpmRealizedOutcomeSnapshot,
    compare_outcome_dimension,
)
from src.core.outcomes.models import DpmOutcomeDimensionInput
from src.core.outcomes.repository import DpmOutcomeReviewConflictError
from src.infrastructure.outcomes import InMemoryDpmOutcomeReviewRepository
from src.infrastructure.outcomes.postgres import (
    PostgresDpmOutcomeReviewRepository,
    _insert_event,
    _import_psycopg,
    _payload,
)


class _Cursor:
    def __init__(
        self, *, row: dict[str, object] | None = None, rows: list[dict[str, object]] | None = None
    ):
        self._row = row
        self._rows = rows or []

    def fetchone(self) -> dict[str, object] | None:
        return self._row

    def fetchall(self) -> list[dict[str, object]]:
        return self._rows


class _FakeConnection:
    def __init__(self, cursors: list[_Cursor] | None = None) -> None:
        self._cursors = cursors or []
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.committed = False
        self.closed = False

    def execute(self, sql: str, params: tuple[object, ...] = ()) -> _Cursor:
        self.executed.append((sql, params))
        if self._cursors:
            return self._cursors.pop(0)
        return _Cursor()

    def commit(self) -> None:
        self.committed = True

    def close(self) -> None:
        self.closed = True


def _window() -> DpmOutcomeReviewWindow:
    return DpmOutcomeReviewWindow(
        start_at="2026-05-05T01:00:00Z",
        end_at="2026-05-06T01:00:00Z",
        as_of_date="2026-05-06",
    )


def _source_ref(source_id: str) -> DpmOutcomeSourceRef:
    return DpmOutcomeSourceRef(
        source_system="lotus-manage",
        source_type="TEST_SOURCE",
        source_id=source_id,
        content_hash=f"sha256:{source_id}",
    )


def _metric(value: str) -> DpmOutcomeMetricValue:
    return DpmOutcomeMetricValue(
        value=Decimal(value),
        unit="ratio",
        source_refs=[_source_ref("metric")],
        source_freshness=DpmOutcomeSourceFreshness(
            observed_at="2026-05-06T01:10:00Z",
            as_of_date="2026-05-06",
            freshness_state="CURRENT",
        ),
        supportability=DpmOutcomeSupportability(state="READY", reason_codes=["SOURCE_READY"]),
    )


def _review(
    *,
    outcome_review_id: str = "dor_001",
    content_hash: str = "sha256:review",
    state: str = "READY",
    idempotency_key: str | None = "idem_001",
) -> DpmPostTradeOutcomeReview:
    expected_metric = _metric("0.0350")
    realized_metric = _metric("0.0340")
    dimension_result = compare_outcome_dimension(
        DpmOutcomeDimensionInput(
            dimension="DRIFT_REDUCTION",
            expected=expected_metric,
            realized=realized_metric,
            tolerance=DpmOutcomeTolerance(soft=Decimal("0.0025"), hard=Decimal("0.0100")),
            materiality=Decimal("0.0050"),
            direction="LOWER_IS_BETTER",
        )
    )
    expected_snapshot = DpmExpectedOutcomeSnapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        rebalance_run_id="rr_001",
        alternative_set_id="cas_001",
        selected_alternative_id="alt_min_turnover",
        proof_pack_id="dpp_001",
        wave_id="dwv_001",
        wave_item_id="dwi_001",
        operations_handoff_ref_id="dwh_001",
        expected_values={"DRIFT_REDUCTION": expected_metric},
        supportability=DpmOutcomeSupportability(state="READY", reason_codes=["EXPECTED_READY"]),
        source_lineage=[_source_ref("expected")],
        source_hashes={"expected": "sha256:expected"},
        section_hashes={"selected_alternative": "sha256:selected-section"},
    )
    realized_snapshot = DpmRealizedOutcomeSnapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        realized_values={"DRIFT_REDUCTION": realized_metric},
        supportability=DpmOutcomeSupportability(state="READY", reason_codes=["REALIZED_READY"]),
        source_lineage=[_source_ref("realized")],
        source_hashes={"realized": "sha256:realized"},
        quality_summary={"COMPLETE": 1},
    )
    return DpmPostTradeOutcomeReview(
        outcome_review_id=outcome_review_id,
        state=state,
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        rebalance_run_id="rr_001",
        alternative_set_id="cas_001",
        selected_alternative_id="alt_min_turnover",
        proof_pack_id="dpp_001",
        wave_id="dwv_001",
        wave_item_id="dwi_001",
        operations_handoff_ref_id="dwh_001",
        review_window=_window(),
        expected_snapshot=expected_snapshot,
        realized_snapshot=realized_snapshot,
        dimension_results=[dimension_result],
        overall_outcome="READY_WITHIN_TOLERANCE",
        variance_summary={"DRIFT_REDUCTION": Decimal("-0.0010")},
        supportability=DpmOutcomeSupportability(state=state, reason_codes=["SOURCE_READY"]),
        source_lineage=[_source_ref("expected"), _source_ref("realized")],
        source_hashes={"expected": "sha256:expected", "realized": "sha256:realized"},
        section_hashes={"selected_alternative": "sha256:selected-section"},
        events=[
            DpmOutcomeEvent(
                event_id=f"{outcome_review_id}_created",
                event_type="OUTCOME_REVIEW_CREATED",
                event_time="2026-05-06T01:20:00Z",
                actor="pm_001",
                outcome_review_id=outcome_review_id,
                state=state,
                reason_codes=["SOURCE_READY"],
            )
        ],
        retention_policy="DPM_OUTCOME_REVIEW_7Y",
        legal_hold_state="NONE",
        content_hash=content_hash,
        created_at=datetime(2026, 5, 6, 1, 20, tzinfo=timezone.utc),
        created_by="pm_001",
        correlation_id=f"corr_{outcome_review_id}",
        idempotency_key=idempotency_key,
    )


def _postgres_repository(connection: _FakeConnection) -> PostgresDpmOutcomeReviewRepository:
    repository = PostgresDpmOutcomeReviewRepository.__new__(PostgresDpmOutcomeReviewRepository)
    repository._dsn = "postgresql://unit-test"  # noqa: SLF001
    repository._connect = lambda: connection  # type: ignore[method-assign]  # noqa: SLF001
    return repository


def test_in_memory_outcome_repository_persists_immutable_review_and_retention() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    review = _review()

    repository.save_outcome_review(
        review=review,
        retention_expires_at=datetime(2033, 5, 6, tzinfo=timezone.utc),
    )

    loaded = repository.get_outcome_review(outcome_review_id=review.outcome_review_id)
    assert loaded == review
    assert repository.get_outcome_review_by_idempotency(idempotency_key="idem_001") == review
    retention = repository.get_retention_metadata(outcome_review_id=review.outcome_review_id)
    assert retention is not None
    assert retention.retention_policy == "DPM_OUTCOME_REVIEW_7Y"
    assert retention.retention_expires_at == "2033-05-06T00:00:00+00:00"


def test_in_memory_outcome_repository_rejects_immutable_conflict() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    repository.save_outcome_review(review=_review(), retention_expires_at=None)

    with pytest.raises(DpmOutcomeReviewConflictError, match="IMMUTABLE"):
        repository.save_outcome_review(
            review=_review(content_hash="sha256:different"),
            retention_expires_at=None,
        )


def test_in_memory_outcome_repository_rejects_idempotency_conflict() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    repository.save_outcome_review(review=_review(), retention_expires_at=None)

    with pytest.raises(DpmOutcomeReviewConflictError, match="IDEMPOTENCY"):
        repository.save_outcome_review(
            review=_review(outcome_review_id="dor_002", content_hash="sha256:review-2"),
            retention_expires_at=None,
        )


def test_in_memory_outcome_repository_lists_filters_and_append_only_events() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    ready = _review(outcome_review_id="dor_ready", idempotency_key="idem_ready")
    blocked = _review(
        outcome_review_id="dor_blocked",
        content_hash="sha256:blocked",
        state="BLOCKED",
        idempotency_key="idem_blocked",
    )
    repository.save_outcome_review(review=ready, retention_expires_at=None)
    repository.save_outcome_review(review=blocked, retention_expires_at=None)
    repository.append_event(
        event=DpmOutcomeEvent(
            event_id="dor_ready_refreshed",
            event_type="OUTCOME_REVIEW_SOURCE_REFRESHED",
            event_time="2026-05-06T01:30:00Z",
            actor="system",
            outcome_review_id="dor_ready",
            state="READY",
            reason_codes=["SOURCE_REFRESHED"],
        )
    )

    assert [
        review.outcome_review_id for review in repository.list_outcome_reviews(state="READY")
    ] == ["dor_ready"]
    events = repository.list_events(outcome_review_id="dor_ready")
    assert [event.event_type for event in events] == [
        "OUTCOME_REVIEW_CREATED",
        "OUTCOME_REVIEW_SOURCE_REFRESHED",
    ]


def test_in_memory_outcome_repository_returns_deep_copies() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    repository.save_outcome_review(review=_review(), retention_expires_at=None)

    loaded = repository.get_outcome_review(outcome_review_id="dor_001")
    assert loaded is not None
    loaded.state = "BLOCKED"

    assert repository.get_outcome_review(outcome_review_id="dor_001").state == "READY"  # type: ignore[union-attr]


def test_postgres_outcome_repository_requires_dsn_and_driver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(RuntimeError, match="DSN_REQUIRED"):
        PostgresDpmOutcomeReviewRepository(dsn="")

    monkeypatch.setattr("src.infrastructure.outcomes.postgres.has_psycopg", lambda: False)

    with pytest.raises(RuntimeError, match="DRIVER_MISSING"):
        PostgresDpmOutcomeReviewRepository(dsn="postgresql://unit-test")


def test_postgres_outcome_repository_initializes_when_driver_is_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.infrastructure.outcomes.postgres.has_psycopg", lambda: True)
    monkeypatch.setattr(
        "src.infrastructure.outcomes.postgres.PostgresDpmOutcomeReviewRepository._init_db",
        lambda self: None,
    )

    repository = PostgresDpmOutcomeReviewRepository(dsn="postgresql://unit-test")

    assert repository._dsn == "postgresql://unit-test"  # noqa: SLF001


def test_postgres_outcome_repository_saves_review_events_and_retention() -> None:
    connection = _FakeConnection(cursors=[_Cursor(), _Cursor()])
    repository = _postgres_repository(connection)
    review = _review()

    repository.save_outcome_review(
        review=review,
        retention_expires_at=datetime(2033, 5, 6, tzinfo=timezone.utc),
    )

    assert connection.committed is True
    assert connection.closed is True
    assert len(connection.executed) == 4
    insert_review_params = connection.executed[2][1]
    assert insert_review_params[0] == "dor_001"
    assert insert_review_params[13] == "2033-05-06T00:00:00+00:00"
    insert_event_params = connection.executed[3][1]
    assert insert_event_params[:3] == (
        "dor_001_created",
        "dor_001",
        "OUTCOME_REVIEW_CREATED",
    )


def test_postgres_outcome_repository_rejects_immutable_and_idempotency_conflicts() -> None:
    immutable_connection = _FakeConnection(
        cursors=[_Cursor(row={"content_hash": "sha256:different"})]
    )
    immutable_repository = _postgres_repository(immutable_connection)

    with pytest.raises(DpmOutcomeReviewConflictError, match="IMMUTABLE"):
        immutable_repository.save_outcome_review(review=_review(), retention_expires_at=None)

    idempotency_connection = _FakeConnection(
        cursors=[_Cursor(), _Cursor(row={"outcome_review_id": "dor_other"})]
    )
    idempotency_repository = _postgres_repository(idempotency_connection)

    with pytest.raises(DpmOutcomeReviewConflictError, match="IDEMPOTENCY"):
        idempotency_repository.save_outcome_review(review=_review(), retention_expires_at=None)


def test_postgres_outcome_repository_reads_review_lookup_list_retention_and_events() -> None:
    review = _review()
    event = review.events[0]
    payload_json = review.model_dump_json()
    event_json = event.model_dump_json()

    get_connection = _FakeConnection(cursors=[_Cursor(row={"payload_json": payload_json})])
    assert (
        _postgres_repository(get_connection)
        .get_outcome_review(outcome_review_id="dor_001")
        .outcome_review_id
        == "dor_001"
    )

    missing_connection = _FakeConnection(cursors=[_Cursor()])
    assert (
        _postgres_repository(missing_connection).get_outcome_review(outcome_review_id="missing")
        is None
    )

    idempotency_connection = _FakeConnection(cursors=[_Cursor(row={"payload_json": payload_json})])
    assert (
        _postgres_repository(idempotency_connection)
        .get_outcome_review_by_idempotency(idempotency_key="idem_001")
        .idempotency_key
        == "idem_001"
    )
    missing_idempotency_connection = _FakeConnection(cursors=[_Cursor()])
    assert (
        _postgres_repository(missing_idempotency_connection).get_outcome_review_by_idempotency(
            idempotency_key="missing"
        )
        is None
    )

    list_connection = _FakeConnection(
        cursors=[_Cursor(rows=[{"payload_json": payload_json}, {"payload_json": payload_json}])]
    )
    listed = _postgres_repository(list_connection).list_outcome_reviews(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        wave_id="dwv_001",
        rebalance_run_id="rr_001",
        state="READY",
        limit=2,
        offset=1,
    )
    assert [item.outcome_review_id for item in listed] == ["dor_001", "dor_001"]
    assert list_connection.executed[0][1] == (
        "PB_SG_GLOBAL_BAL_001",
        "MANDATE_PB_SG_GLOBAL_BAL_001",
        "dwv_001",
        "rr_001",
        "READY",
        2,
        1,
    )

    retention_connection = _FakeConnection(
        cursors=[
            _Cursor(
                row={
                    "outcome_review_id": "dor_001",
                    "retention_policy": "DPM_OUTCOME_REVIEW_7Y",
                    "retention_expires_at": datetime(2033, 5, 6, tzinfo=timezone.utc),
                    "legal_hold_state": "NONE",
                }
            )
        ]
    )
    retention = _postgres_repository(retention_connection).get_retention_metadata(
        outcome_review_id="dor_001"
    )
    assert retention is not None
    assert retention.retention_expires_at == "2033-05-06T00:00:00+00:00"
    missing_retention_connection = _FakeConnection(cursors=[_Cursor()])
    assert (
        _postgres_repository(missing_retention_connection).get_retention_metadata(
            outcome_review_id="missing"
        )
        is None
    )

    events_connection = _FakeConnection(cursors=[_Cursor(rows=[{"payload_json": event_json}])])
    assert [
        item.event_type
        for item in _postgres_repository(events_connection).list_events(outcome_review_id="dor_001")
    ] == ["OUTCOME_REVIEW_CREATED"]


def test_postgres_outcome_repository_appends_event_and_normalizes_payload() -> None:
    event = _review().events[0]
    connection = _FakeConnection()

    _postgres_repository(connection).append_event(event=event)

    assert connection.committed is True
    assert connection.executed[0][1][:2] == ("dor_001_created", "dor_001")
    assert _payload({"payload_json": {"outcome_review_id": "dor_001"}}) == {
        "outcome_review_id": "dor_001"
    }
    assert _payload({"payload_json": ["not", "a", "dict"]}) == '["not", "a", "dict"]'


def test_postgres_insert_event_uses_idempotent_event_key() -> None:
    event = _review().events[0]
    connection = _FakeConnection()

    _insert_event(connection=connection, event=event)

    sql, params = connection.executed[0]
    assert "ON CONFLICT (event_id) DO NOTHING" in sql
    assert params[:6] == (
        "dor_001_created",
        "dor_001",
        "OUTCOME_REVIEW_CREATED",
        "2026-05-06T01:20:00Z",
        "pm_001",
        "READY",
    )


def test_postgres_init_connect_and_driver_import_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration_calls: list[str] = []
    connection = _FakeConnection()
    repository = _postgres_repository(connection)

    monkeypatch.setattr(
        "src.infrastructure.outcomes.postgres.apply_postgres_migrations",
        lambda *, connection, namespace: migration_calls.append(namespace),
    )

    repository._init_db()  # noqa: SLF001

    assert migration_calls == ["dpm"]
    assert connection.closed is True
    psycopg, dict_row = _import_psycopg()
    assert hasattr(psycopg, "connect")
    assert dict_row is not None
