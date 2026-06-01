from datetime import datetime, timedelta, timezone

from src.api.services.proof_pack_persistence import (
    PROOF_PACK_RETENTION_DAYS,
    persist_proof_pack,
)
from tests.unit.dpm.proof_packs.test_proof_pack_repository import _proof_pack


class _CapturingProofPackRepository:
    def __init__(self) -> None:
        self.saved: dict[str, object] | None = None

    def save_proof_pack(
        self,
        *,
        proof_pack: object,
        idempotency_key: str | None,
        retention_expires_at: datetime | None,
    ) -> None:
        self.saved = {
            "proof_pack": proof_pack,
            "idempotency_key": idempotency_key,
            "retention_expires_at": retention_expires_at,
        }


def test_persist_proof_pack_applies_seven_year_retention_from_persisted_at() -> None:
    repository = _CapturingProofPackRepository()
    proof_pack = _proof_pack()
    persisted_at = datetime(2026, 6, 1, 8, 30, tzinfo=timezone.utc)

    persist_proof_pack(
        proof_pack_repository=repository,  # type: ignore[arg-type]
        proof_pack=proof_pack,
        idempotency_key="idem-proof-pack-persistence",
        persisted_at=persisted_at,
    )

    assert repository.saved == {
        "proof_pack": proof_pack,
        "idempotency_key": "idem-proof-pack-persistence",
        "retention_expires_at": persisted_at + timedelta(days=PROOF_PACK_RETENTION_DAYS),
    }


def test_proof_pack_persistence_exports_retention_policy_surface() -> None:
    from src.api.services import proof_pack_persistence

    assert proof_pack_persistence.__all__ == [
        "PROOF_PACK_RETENTION_DAYS",
        "persist_proof_pack",
    ]
