from src.api.services.wave_supportability_payload import wave_supportability_payload
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveEvent, DpmWaveRepository


def search_wave_summaries(
    *,
    wave_repository: DpmWaveRepository,
    state: str | None = None,
    trigger_type: str | None = None,
    as_of_date: str | None = None,
    supportability_state: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, object]]:
    waves = wave_repository.list_waves(
        state=state,
        trigger_type=trigger_type,
        as_of_date=as_of_date,
        limit=limit,
        offset=offset,
    )
    return [
        summary
        for wave in waves
        if (
            summary := _searchable_wave_summary(
                wave=wave,
                supportability_state=supportability_state,
            )
        )
        is not None
    ]


def _searchable_wave_summary(
    *,
    wave: DpmRebalanceWave,
    supportability_state: str | None,
) -> dict[str, object] | None:
    supportability = wave_supportability_payload(wave)
    if not _matches_supportability_state(
        supportability=supportability,
        supportability_state=supportability_state,
    ):
        return None
    return _wave_summary(wave=wave, supportability=supportability)


def _matches_supportability_state(
    *,
    supportability: dict[str, object],
    supportability_state: str | None,
) -> bool:
    if supportability_state is None:
        return True
    return supportability["supportability_state"] == supportability_state


def _wave_summary(
    *,
    wave: DpmRebalanceWave,
    supportability: dict[str, object],
) -> dict[str, object]:
    latest_event = _latest_wave_event(wave)
    return {
        "wave_id": wave.wave_id,
        "wave_state": wave.state,
        "trigger_type": wave.trigger.trigger_type,
        "trigger_id": wave.trigger.trigger_id,
        "as_of_date": wave.as_of_date,
        "created_at": wave.created_at,
        "created_by": wave.created_by,
        "item_count": len(wave.items),
        "aggregate_metrics": wave.aggregate_metrics,
        "supportability_state": supportability["supportability_state"],
        "supportability_reason": supportability["reason"],
        "latest_event_type": latest_event.event_type if latest_event is not None else None,
        "latest_event_reason_code": latest_event.reason_code if latest_event is not None else None,
    }


def _latest_wave_event(wave: DpmRebalanceWave) -> DpmRebalanceWaveEvent | None:
    if not wave.events:
        return None
    return wave.events[-1]


__all__ = ["search_wave_summaries"]
