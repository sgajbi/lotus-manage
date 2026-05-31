from src.core.portfolio_memory.proof_pack_collection import proof_pack_memory_events
from src.infrastructure.proof_packs import InMemoryDpmProofPackRepository
from tests.unit.dpm.api.test_portfolio_memory_api import PORTFOLIO_ID
from tests.unit.dpm.proof_packs.test_proof_pack_repository import _proof_pack


def test_proof_pack_memory_events_projects_proof_pack_and_timeline_events() -> None:
    repository = InMemoryDpmProofPackRepository()
    proof_pack = _proof_pack().model_copy(update={"portfolio_id": PORTFOLIO_ID})
    repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key=None,
        retention_expires_at=None,
    )

    events = proof_pack_memory_events(
        portfolio_id=PORTFOLIO_ID,
        proof_pack_repository=repository,
        limit=100,
    )

    assert [event.event_type for event in events] == [
        "PROOF_PACK_CREATED",
        *(["PROOF_PACK_TIMELINE_EVENT"] * len(proof_pack.decision_timeline.events)),
    ]
    assert events[0].source_id == proof_pack.proof_pack_id
    assert events[0].metadata["rebalance_run_id"] == proof_pack.rebalance_run_id
    assert all(
        event.metadata == {"proof_pack_id": proof_pack.proof_pack_id} for event in events[1:]
    )


def test_proof_pack_memory_events_uses_portfolio_filter() -> None:
    repository = InMemoryDpmProofPackRepository()
    repository.save_proof_pack(
        proof_pack=_proof_pack().model_copy(update={"portfolio_id": "PB_OTHER_001"}),
        idempotency_key=None,
        retention_expires_at=None,
    )

    events = proof_pack_memory_events(
        portfolio_id=PORTFOLIO_ID,
        proof_pack_repository=repository,
        limit=100,
    )

    assert events == []
