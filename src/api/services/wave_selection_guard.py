from __future__ import annotations

from src.api.services.wave_errors import DpmWaveLookupError, DpmWaveValidationError
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem


def selectable_wave_item(
    *,
    wave: DpmRebalanceWave,
    wave_item_id: str,
) -> DpmRebalanceWaveItem:
    selected_item = next((item for item in wave.items if item.wave_item_id == wave_item_id), None)
    if selected_item is None:
        raise DpmWaveLookupError("DPM_WAVE_ITEM_NOT_FOUND", f"Wave item {wave_item_id} not found.")
    if selected_item.alternative_set_id is None:
        raise DpmWaveValidationError(
            "DPM_WAVE_ITEM_ALTERNATIVES_MISSING",
            f"Wave item {wave_item_id} has no generated alternatives.",
        )
    return selected_item


__all__ = ["selectable_wave_item"]
