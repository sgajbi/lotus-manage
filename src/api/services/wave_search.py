from src.api.services.wave_supportability_payload import wave_supportability_payload
from src.core.waves import DpmWaveRepository


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
    items: list[dict[str, object]] = []
    for wave in waves:
        supportability = wave_supportability_payload(wave)
        if (
            supportability_state is not None
            and supportability["supportability_state"] != supportability_state
        ):
            continue
        items.append(
            {
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
                "latest_event_type": wave.events[-1].event_type if wave.events else None,
                "latest_event_reason_code": wave.events[-1].reason_code if wave.events else None,
            }
        )
    return items


__all__ = ["search_wave_summaries"]
