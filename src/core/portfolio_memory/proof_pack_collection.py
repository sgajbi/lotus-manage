"""Proof-pack repository collection for portfolio-memory events."""

from src.core.portfolio_memory.models import DpmPortfolioMemoryEvent
from src.core.portfolio_memory.proof_pack_projection import proof_pack_events
from src.core.proof_packs.repository import DpmProofPackRepository


def proof_pack_memory_events(
    *,
    portfolio_id: str,
    proof_pack_repository: DpmProofPackRepository,
    limit: int,
) -> list[DpmPortfolioMemoryEvent]:
    """Collect proof-pack memory events for one portfolio."""

    events: list[DpmPortfolioMemoryEvent] = []
    for proof_pack in proof_pack_repository.list_proof_packs(
        portfolio_id=portfolio_id,
        limit=limit,
    ):
        events.extend(proof_pack_events(proof_pack))
    return events
