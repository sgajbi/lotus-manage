"""Wave repository collection for portfolio-memory events."""

from src.core.portfolio_memory.models import DpmPortfolioMemoryEvent
from src.core.portfolio_memory.wave_projection import wave_events
from src.core.waves.repository import DpmWaveRepository


def wave_memory_events(
    *,
    portfolio_id: str,
    wave_repository: DpmWaveRepository,
    limit: int,
) -> list[DpmPortfolioMemoryEvent]:
    """Collect rebalance-wave memory events for waves containing one portfolio."""

    events: list[DpmPortfolioMemoryEvent] = []
    for wave in wave_repository.list_waves(limit=limit):
        if not any(item.portfolio_id == portfolio_id for item in wave.items):
            continue
        events.extend(wave_events(wave=wave, portfolio_id=portfolio_id))
    return events
