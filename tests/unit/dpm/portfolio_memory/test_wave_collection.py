from src.core.portfolio_memory.wave_collection import wave_memory_events
from src.infrastructure.waves import InMemoryDpmWaveRepository
from tests.unit.dpm.api.test_portfolio_memory_api import PORTFOLIO_ID, _wave


def test_wave_memory_events_projects_matching_wave_events() -> None:
    repository = InMemoryDpmWaveRepository()
    repository.save_wave(wave=_wave(), idempotency_key=None, request_hash=None)

    events = wave_memory_events(
        portfolio_id=PORTFOLIO_ID,
        wave_repository=repository,
        limit=100,
    )

    assert [event.event_type for event in events] == [
        "WAVE_CREATED",
        "WAVE_EVENT",
        "WAVE_HANDOFF_READY",
    ]
    assert events[0].source_id == "dwv_001"
    assert events[0].metadata["matching_item_count"] == 1
    assert events[2].source_id == "dwh_001"
    assert events[2].metadata["external_execution_claimed"] is False


def test_wave_memory_events_skips_waves_without_matching_portfolio_items() -> None:
    repository = InMemoryDpmWaveRepository()
    wave = _wave()
    repository.save_wave(
        wave=wave.model_copy(
            update={
                "wave_id": "dwv_other",
                "items": [wave.items[0].model_copy(update={"portfolio_id": "PB_OTHER_001"})],
            }
        ),
        idempotency_key=None,
        request_hash=None,
    )

    events = wave_memory_events(
        portfolio_id=PORTFOLIO_ID,
        wave_repository=repository,
        limit=100,
    )

    assert events == []
