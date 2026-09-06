from datetime import datetime, timezone

from pytest import MonkeyPatch

from src.api.services import wave_selection_item
from src.api.services.wave_aggregate_metrics import aggregate_wave_items
from src.api.services.wave_item_selection_transition import (
    build_wave_with_selected_item_alternative,
)
from src.core.proof_packs.models import DpmPreTradeProofPack
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem, DpmWaveTrigger


def _item(
    *,
    wave_item_id: str,
    state: str = "SIMULATED",
    alternative_set_id: str | None = "cas_select",
) -> DpmRebalanceWaveItem:
    return DpmRebalanceWaveItem(
        wave_item_id=wave_item_id,
        portfolio_id=f"PB_SG_{wave_item_id.upper()}",
        mandate_id=f"MANDATE_{wave_item_id.upper()}",
        state=state,
        alternative_set_id=alternative_set_id,
        diagnostics={"existing": "value"},
    )


def _wave(*, items: list[DpmRebalanceWaveItem]) -> DpmRebalanceWave:
    return DpmRebalanceWave(
        wave_id="dwv_select",
        state="SIMULATED",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-selection",
            rationale="Select an alternative for one wave item.",
        ),
        as_of_date="2026-05-03",
        created_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
        created_by="pm_001",
        correlation_id="corr_select",
        items=items,
        aggregate_metrics=aggregate_wave_items(items),
    )


def _build(
    *,
    wave: DpmRebalanceWave,
    selected_item: DpmRebalanceWaveItem,
    generate_proof_pack: bool = False,
) -> DpmRebalanceWave:
    return build_wave_with_selected_item_alternative(
        wave=wave,
        selected_item=selected_item,
        alternative_id="alt_selected",
        actor_id="pm_select",
        reason_code="LOWER_TURNOVER_WITH_ACCEPTABLE_DRIFT",
        comment="Selected by PM desk.",
        correlation_id="corr-selection-event",
        generate_proof_pack=generate_proof_pack,
        construction_repository=object(),  # type: ignore[arg-type]
        proof_pack_repository=object(),  # type: ignore[arg-type]
        mandate_repository=object(),  # type: ignore[arg-type]
        run_service=object(),  # type: ignore[arg-type]
        tenant_id="tenant-test",
    )


def test_build_wave_with_selected_item_alternative_updates_only_selected_item() -> None:
    selected_item = _item(wave_item_id="dwi_selected")
    retained_item = _item(wave_item_id="dwi_retained", alternative_set_id="cas_retained")
    updated = _build(
        wave=_wave(items=[selected_item, retained_item]),
        selected_item=selected_item,
    )

    assert updated.version == 2
    assert updated.state == "SIMULATED"
    assert [item.state for item in updated.items] == ["SELECTED", "SIMULATED"]
    assert updated.items[0].selected_alternative_id == "alt_selected"
    assert updated.items[1].selected_alternative_id is None
    assert updated.aggregate_metrics.state_counts == {"SELECTED": 1, "SIMULATED": 1}


def test_build_wave_with_selected_item_alternative_appends_selection_event() -> None:
    selected_item = _item(wave_item_id="dwi_selected")
    updated = _build(wave=_wave(items=[selected_item]), selected_item=selected_item)

    assert updated.events[-1].event_type == "ITEM_SELECTION"
    assert updated.events[-1].reason_code == "WAVE_ITEM_ALTERNATIVE_SELECTED"
    assert updated.events[-1].actor_id == "pm_select"
    assert updated.events[-1].correlation_id == "corr-selection-event"
    assert updated.events[-1].metadata == {
        "wave_item_id": "dwi_selected",
        "alternative_set_id": "cas_select",
        "selected_alternative_id": "alt_selected",
        "proof_pack_id": None,
        "proof_pack_state": "DEGRADED",
    }


def test_build_wave_with_selected_item_alternative_records_generated_proof_pack(
    monkeypatch: MonkeyPatch,
) -> None:
    def _generate(**_kwargs: object) -> DpmPreTradeProofPack:
        return DpmPreTradeProofPack.model_construct(
            proof_pack_id="dpp_selected",
            status="READY",
        )

    monkeypatch.setattr(
        wave_selection_item.proof_pack_service,
        "generate_proof_pack_from_selected_alternative",
        _generate,
    )

    selected_item = _item(wave_item_id="dwi_selected")
    updated = _build(
        wave=_wave(items=[selected_item]),
        selected_item=selected_item,
        generate_proof_pack=True,
    )

    assert updated.items[0].state == "PROOF_PACK_READY"
    assert updated.items[0].proof_pack_id == "dpp_selected"
    assert updated.events[-1].metadata["proof_pack_id"] == "dpp_selected"
    assert updated.events[-1].metadata["proof_pack_state"] == "READY"


def test_wave_item_selection_transition_exports_only_selection_helper() -> None:
    from src.api.services import wave_item_selection_transition

    assert wave_item_selection_transition.__all__ == ["build_wave_with_selected_item_alternative"]
