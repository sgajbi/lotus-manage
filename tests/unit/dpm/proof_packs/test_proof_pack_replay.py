from datetime import datetime, timezone
import pytest

from src.api.services.proof_pack_replay import find_replayable_proof_pack
from src.core.proof_packs import ProofPackSourceValidationError
from src.infrastructure.proof_packs import InMemoryDpmProofPackRepository
from tests.unit.dpm.proof_packs.test_proof_pack_repository import _proof_pack


RETENTION_EXPIRES_AT = datetime(2033, 5, 3, 9, 30, tzinfo=timezone.utc)


@pytest.mark.parametrize("idempotency_key", [None, "idem-legacy-no-action"])
def test_historical_no_action_proof_cannot_replay_heuristic_run(
    idempotency_key: str | None,
) -> None:
    repository = InMemoryDpmProofPackRepository()
    pack = _proof_pack()
    selected = pack.sections[0].model_copy(
        update={"section_type": "selected_alternative", "facts": {"method": "DO_NOTHING_BASELINE"}}
    )
    pack = pack.model_copy(
        update={"rebalance_run_id": "rr_borrowed_heuristic", "sections": [selected]}
    )
    repository.save_proof_pack(
        proof_pack=pack,
        idempotency_key=idempotency_key,
        retention_expires_at=RETENTION_EXPIRES_AT,
        tenant_id="tenant-test",
    )
    with pytest.raises(
        ProofPackSourceValidationError, match="DPM_NO_ACTION_EVALUATION_RUN_NOT_ECONOMIC_SOURCE"
    ):
        find_replayable_proof_pack(
            proof_pack_id=pack.proof_pack_id,
            idempotency_key=idempotency_key,
            proof_pack_repository=repository,
            tenant_id="tenant-test",
        )
    assert (
        repository.get_proof_pack(proof_pack_id=pack.proof_pack_id, tenant_id="tenant-test") == pack
    )


def test_find_replayable_proof_pack_prefers_idempotency_match() -> None:
    repository = InMemoryDpmProofPackRepository()
    by_idempotency = _proof_pack().model_copy(update={"proof_pack_id": "dpp_by_idempotency"})
    by_source_identity = _proof_pack().model_copy(update={"proof_pack_id": "dpp_by_source"})
    repository.save_proof_pack(
        proof_pack=by_idempotency,
        idempotency_key="idem-proof-pack-replay",
        retention_expires_at=RETENTION_EXPIRES_AT,
        tenant_id="tenant-test",
    )
    repository.save_proof_pack(
        proof_pack=by_source_identity,
        idempotency_key=None,
        retention_expires_at=RETENTION_EXPIRES_AT,
        tenant_id="tenant-test",
    )

    replay = find_replayable_proof_pack(
        proof_pack_id=by_source_identity.proof_pack_id,
        idempotency_key="idem-proof-pack-replay",
        proof_pack_repository=repository,
        tenant_id="tenant-test",
    )

    assert replay == by_idempotency


def test_find_replayable_proof_pack_falls_back_to_source_identity() -> None:
    repository = InMemoryDpmProofPackRepository()
    proof_pack = _proof_pack()
    repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key=None,
        retention_expires_at=RETENTION_EXPIRES_AT,
        tenant_id="tenant-test",
    )

    replay = find_replayable_proof_pack(
        proof_pack_id=proof_pack.proof_pack_id,
        idempotency_key="different-idempotency-key",
        proof_pack_repository=repository,
        tenant_id="tenant-test",
    )

    assert replay == proof_pack


def test_find_replayable_proof_pack_returns_none_when_no_replay_exists() -> None:
    repository = InMemoryDpmProofPackRepository()

    replay = find_replayable_proof_pack(
        proof_pack_id="dpp_missing",
        idempotency_key=None,
        proof_pack_repository=repository,
        tenant_id="tenant-test",
    )

    assert replay is None
