import pytest

from src.api.services import wave_selection_guard
from src.api.services.wave_errors import DpmWaveLookupError, DpmWaveValidationError
from src.api.services.wave_selection_guard import selectable_wave_item
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem


def _item(
    *,
    item_id: str,
    alternative_set_id: str | None,
) -> DpmRebalanceWaveItem:
    return DpmRebalanceWaveItem.model_construct(
        wave_item_id=item_id,
        portfolio_id=f"PB_{item_id}",
        state="SIMULATED",
        alternative_set_id=alternative_set_id,
    )


def _wave() -> DpmRebalanceWave:
    return DpmRebalanceWave.model_construct(
        wave_id="dwv_selection_guard",
        state="SIMULATED",
        items=[
            _item(item_id="dwi_ready", alternative_set_id="alt_set_1"),
            _item(item_id="dwi_missing_alternatives", alternative_set_id=None),
        ],
    )


def test_selectable_wave_item_returns_item_with_alternatives() -> None:
    item = selectable_wave_item(wave=_wave(), wave_item_id="dwi_ready")

    assert item.wave_item_id == "dwi_ready"
    assert item.alternative_set_id == "alt_set_1"


def test_selectable_wave_item_raises_lookup_error_for_missing_item() -> None:
    with pytest.raises(DpmWaveLookupError) as exc_info:
        selectable_wave_item(wave=_wave(), wave_item_id="dwi_unknown")

    assert exc_info.value.code == "DPM_WAVE_ITEM_NOT_FOUND"
    assert exc_info.value.message == "Wave item dwi_unknown not found."


def test_selectable_wave_item_raises_validation_error_without_alternatives() -> None:
    with pytest.raises(DpmWaveValidationError) as exc_info:
        selectable_wave_item(wave=_wave(), wave_item_id="dwi_missing_alternatives")

    assert exc_info.value.code == "DPM_WAVE_ITEM_ALTERNATIVES_MISSING"
    assert (
        exc_info.value.message
        == "Wave item dwi_missing_alternatives has no generated alternatives."
    )


def test_wave_selection_guard_exports_public_surface() -> None:
    assert wave_selection_guard.__all__ == ["selectable_wave_item"]
