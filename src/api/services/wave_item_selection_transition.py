from __future__ import annotations

from src.api.services.wave_event_append import append_same_state_event
from src.api.services.wave_event_evidence import build_wave_event
from src.api.services.wave_item_collection import wave_with_items_and_aggregate
from src.api.services.wave_selection_item import with_selection_and_proof_pack
from src.api.services.wave_workflow_metadata import selection_event_metadata
from src.core.construction.repository import ConstructionRepository
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem


def build_wave_with_selected_item_alternative(
    *,
    wave: DpmRebalanceWave,
    selected_item: DpmRebalanceWaveItem,
    alternative_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    tenant_id: str,
    generate_proof_pack: bool,
    construction_repository: ConstructionRepository,
    proof_pack_repository: DpmProofPackRepository,
    mandate_repository: DpmMandateRepository,
    run_service: DpmRunSupportService,
) -> DpmRebalanceWave:
    assert selected_item.alternative_set_id is not None
    updated_item = with_selection_and_proof_pack(
        item=selected_item,
        alternative_id=alternative_id,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
        tenant_id=tenant_id,
        generate_proof_pack=generate_proof_pack,
        construction_repository=construction_repository,
        proof_pack_repository=proof_pack_repository,
        mandate_repository=mandate_repository,
        run_service=run_service,
    )
    updated_items = [
        updated_item if item.wave_item_id == selected_item.wave_item_id else item
        for item in wave.items
    ]
    return append_same_state_event(
        wave=wave_with_items_and_aggregate(wave=wave, items=updated_items),
        event=build_wave_event(
            wave_id=wave.wave_id,
            from_state=wave.state,
            to_state=wave.state,
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_ITEM_ALTERNATIVE_SELECTED",
            event_type="ITEM_SELECTION",
            metadata=selection_event_metadata(
                wave_item_id=selected_item.wave_item_id,
                alternative_set_id=selected_item.alternative_set_id,
                selected_alternative_id=alternative_id,
                proof_pack_id=updated_item.proof_pack_id,
                proof_pack_state=updated_item.diagnostics.get("proof_pack_state"),
            ),
        ),
    )


__all__ = ["build_wave_with_selected_item_alternative"]
