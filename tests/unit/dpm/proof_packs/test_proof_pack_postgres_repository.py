import json
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from src.core.proof_packs.models import DpmProofPackStoredRef
from src.core.proof_packs.repository import DpmProofPackConflictError
from src.infrastructure.proof_packs import postgres as postgres_module
from src.infrastructure.proof_packs.in_memory import RETENTION_POLICY_PRE_TRADE_PROOF_PACK
from src.infrastructure.proof_packs.postgres import PostgresDpmProofPackRepository
from tests.unit.dpm.proof_packs.test_proof_pack_repository import _proof_pack


CREATED_AT = datetime(2026, 5, 3, 9, 30, tzinfo=timezone.utc)
RETENTION_EXPIRES_AT = CREATED_AT + timedelta(days=365 * 7)


class _FakeCursor:
    def __init__(self, row: dict[str, Any] | None = None, rows: list[dict[str, Any]] | None = None):
        self._row = row
        self._rows = rows or ([] if row is None else [row])

    def fetchone(self) -> dict[str, Any] | None:
        return self._row

    def fetchall(self) -> list[dict[str, Any]]:
        return self._rows


class _FakeConnection:
    def __init__(self) -> None:
        self.proof_packs_by_id: dict[str, dict[str, Any]] = {}
        self.proof_packs_by_idempotency: dict[str, dict[str, Any]] = {}
        self.refs_by_proof_pack: dict[str, list[dict[str, Any]]] = {}
        self.commits = 0

    def execute(self, query: str, params: Sequence[Any] = ()) -> _FakeCursor:
        normalized = " ".join(query.split())
        if normalized.startswith("SELECT content_hash FROM dpm_pre_trade_proof_packs"):
            row = self.proof_packs_by_id.get(str(params[0]))
            return _FakeCursor({"content_hash": row["content_hash"]} if row else None)
        if normalized.startswith("SELECT proof_pack_id FROM dpm_pre_trade_proof_packs"):
            row = self.proof_packs_by_idempotency.get(str(params[0]))
            return _FakeCursor({"proof_pack_id": row["proof_pack_id"]} if row else None)
        if normalized.startswith("INSERT INTO dpm_pre_trade_proof_packs"):
            return self._insert_proof_pack(params)
        if normalized.startswith("INSERT INTO dpm_pre_trade_proof_pack_sections"):
            return _FakeCursor()
        if "SELECT payload_json FROM dpm_pre_trade_proof_packs WHERE proof_pack_id" in normalized:
            return _FakeCursor(self.proof_packs_by_id.get(str(params[0])))
        if "SELECT payload_json FROM dpm_pre_trade_proof_packs WHERE idempotency_key" in normalized:
            return _FakeCursor(self.proof_packs_by_idempotency.get(str(params[0])))
        if normalized.startswith("SELECT proof_pack_id, retention_policy, retention_expires_at"):
            return _FakeCursor(self.proof_packs_by_id.get(str(params[0])))
        if normalized.startswith("INSERT INTO dpm_pre_trade_proof_pack_refs"):
            return self._insert_ref(params)
        if normalized.startswith("SELECT payload_json FROM dpm_pre_trade_proof_pack_refs"):
            return _FakeCursor(rows=self.refs_by_proof_pack.get(str(params[0]), []))
        raise AssertionError(f"Unexpected query: {normalized}")

    def _insert_proof_pack(self, params: Sequence[Any]) -> _FakeCursor:
        proof_pack_id = str(params[0])
        if proof_pack_id in self.proof_packs_by_id:
            return _FakeCursor()
        row = {
            "proof_pack_id": proof_pack_id,
            "content_hash": str(params[5]),
            "idempotency_key": params[6],
            "retention_policy": params[7],
            "retention_expires_at": params[8],
            "payload_json": json.loads(str(params[9])),
        }
        self.proof_packs_by_id[proof_pack_id] = row
        if params[6] is not None:
            self.proof_packs_by_idempotency[str(params[6])] = row
        return _FakeCursor()

    def _insert_ref(self, params: Sequence[Any]) -> _FakeCursor:
        row = {"payload_json": json.loads(str(params[5]))}
        self.refs_by_proof_pack.setdefault(str(params[0]), []).append(row)
        return _FakeCursor()

    def commit(self) -> None:
        self.commits += 1

    def close(self) -> None:
        pass


@pytest.fixture
def fake_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[PostgresDpmProofPackRepository, _FakeConnection]:
    connection = _FakeConnection()
    monkeypatch.setattr(postgres_module, "has_psycopg", lambda: True)
    monkeypatch.setattr(postgres_module, "apply_postgres_migrations", lambda **_: None)
    monkeypatch.setattr(
        postgres_module,
        "_import_psycopg",
        lambda: (type("Psycopg", (), {"connect": lambda *_, **__: connection}), object()),
    )
    return PostgresDpmProofPackRepository(dsn="postgresql://unit-test"), connection


def test_postgres_proof_pack_repository_round_trips_pack_retention_and_refs(
    fake_repository: tuple[PostgresDpmProofPackRepository, _FakeConnection],
) -> None:
    repository, connection = fake_repository
    proof_pack = _proof_pack()
    repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key="idem-proof-pack-postgres",
        retention_expires_at=RETENTION_EXPIRES_AT,
    )
    ref = DpmProofPackStoredRef(
        proof_pack_id=proof_pack.proof_pack_id,
        ref_type="DPM_PROOF_PACK_REPORT_INPUT",
        ref_id="dpri_postgres_001",
        source_system="lotus-manage",
        content_hash="sha256:report",
        created_at=CREATED_AT.isoformat(),
    )
    repository.append_ref(ref=ref)

    assert repository.get_proof_pack(proof_pack_id=proof_pack.proof_pack_id) == proof_pack
    assert (
        repository.get_proof_pack_by_idempotency(idempotency_key="idem-proof-pack-postgres")
        == proof_pack
    )
    assert (
        repository.get_retention_metadata(proof_pack_id=proof_pack.proof_pack_id).retention_policy
        == RETENTION_POLICY_PRE_TRADE_PROOF_PACK
    )
    assert repository.list_refs(proof_pack_id=proof_pack.proof_pack_id) == [ref]
    assert connection.commits == 2


def test_postgres_proof_pack_repository_conflict_paths(
    fake_repository: tuple[PostgresDpmProofPackRepository, _FakeConnection],
) -> None:
    repository, _ = fake_repository
    proof_pack = _proof_pack(reason="Initial rationale.")
    repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key="idem-proof-pack-postgres",
        retention_expires_at=None,
    )

    mutated = _proof_pack(reason="Changed rationale.")
    with pytest.raises(DpmProofPackConflictError, match="DPM_PROOF_PACK_IMMUTABLE_CONFLICT"):
        repository.save_proof_pack(
            proof_pack=mutated,
            idempotency_key="idem-proof-pack-postgres",
            retention_expires_at=None,
        )

    other = proof_pack.model_copy(update={"proof_pack_id": "dpp_postgres_other"})
    with pytest.raises(DpmProofPackConflictError, match="DPM_PROOF_PACK_IDEMPOTENCY_CONFLICT"):
        repository.save_proof_pack(
            proof_pack=other,
            idempotency_key="idem-proof-pack-postgres",
            retention_expires_at=None,
        )

    assert repository.get_proof_pack(proof_pack_id="missing") is None
    assert repository.get_proof_pack_by_idempotency(idempotency_key="missing") is None
    assert repository.get_retention_metadata(proof_pack_id="missing") is None
