from src.api.services import wave_item_collection
from src.api.services.wave_item_collection import wave_with_items_and_aggregate
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem


def _item(
    *,
    item_id: str,
    state: str,
) -> DpmRebalanceWaveItem:
    return DpmRebalanceWaveItem.model_construct(
        wave_item_id=item_id,
        portfolio_id=f"PB_{item_id}",
        state=state,
        reason_codes=[],
        diagnostics={},
    )


def _wave() -> DpmRebalanceWave:
    return DpmRebalanceWave.model_construct(
        wave_id="dwv_collection",
        state="APPROVED",
        items=[_item(item_id="dwi_old", state="APPROVED")],
        handoff_refs=[],
    )


def test_wave_with_items_and_aggregate_replaces_items_and_recomputes_metrics() -> None:
    updated = wave_with_items_and_aggregate(
        wave=_wave(),
        items=[
            _item(item_id="dwi_1", state="STAGED"),
            _item(item_id="dwi_2", state="BLOCKED"),
        ],
    )

    assert [item.wave_item_id for item in updated.items] == ["dwi_1", "dwi_2"]
    assert updated.aggregate_metrics.item_count == 2
    assert updated.aggregate_metrics.state_counts == {"STAGED": 1, "BLOCKED": 1}


def test_wave_with_items_and_aggregate_preserves_extra_updates() -> None:
    updated = wave_with_items_and_aggregate(
        wave=_wave(),
        items=[_item(item_id="dwi_1", state="HANDOFF_READY")],
        extra_updates={"handoff_refs": ["handoff:dwv_collection"]},
    )

    assert updated.handoff_refs == ["handoff:dwv_collection"]
    assert updated.aggregate_metrics.state_counts == {"HANDOFF_READY": 1}


def test_wave_item_collection_exports_public_surface() -> None:
    assert wave_item_collection.__all__ == ["wave_with_items_and_aggregate"]
