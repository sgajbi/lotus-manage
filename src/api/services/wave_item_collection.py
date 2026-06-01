from __future__ import annotations

from src.api.services.wave_aggregate_metrics import aggregate_wave_items
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem


def wave_with_items_and_aggregate(
    *,
    wave: DpmRebalanceWave,
    items: list[DpmRebalanceWaveItem],
    extra_updates: dict[str, object] | None = None,
) -> DpmRebalanceWave:
    return wave.model_copy(
        update={
            "items": items,
            "aggregate_metrics": aggregate_wave_items(items),
            **(extra_updates or {}),
        },
        deep=True,
    )


__all__ = ["wave_with_items_and_aggregate"]
