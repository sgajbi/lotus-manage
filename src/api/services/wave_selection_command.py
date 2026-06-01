from src.api.services.wave_construction_selection import select_construction_alternative_for_wave
from src.api.services.wave_item_selection_transition import (
    build_wave_with_selected_item_alternative,
)
from src.api.services.wave_selection_guard import selectable_wave_item
from src.api.services.wave_transition_execution import (
    persist_transitioned_wave,
    prepare_wave_transition,
)
from src.core.construction.repository import ConstructionRepository
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves import DpmRebalanceWave, DpmWaveRepository


def select_persisted_wave_item_alternative(
    *,
    wave_id: str,
    wave_item_id: str,
    alternative_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    generate_proof_pack: bool,
    construction_repository: ConstructionRepository,
    proof_pack_repository: DpmProofPackRepository,
    mandate_repository: DpmMandateRepository,
    run_service: DpmRunSupportService,
    wave_repository: DpmWaveRepository,
) -> DpmRebalanceWave:
    prepared = prepare_wave_transition(
        wave_id=wave_id,
        wave_repository=wave_repository,
        replay_states=set(),
        allowed_states={"SIMULATED", "PARTIALLY_SIMULATED"},
        error_code="DPM_WAVE_SELECTION_INVALID_STATE",
        action_phrase="record alternative selection",
    )
    selected_item = selectable_wave_item(wave=prepared.wave, wave_item_id=wave_item_id)
    assert selected_item.alternative_set_id is not None
    select_construction_alternative_for_wave(
        repository=construction_repository,
        alternative_set_id=selected_item.alternative_set_id,
        alternative_id=alternative_id,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
    )

    updated = build_wave_with_selected_item_alternative(
        wave=prepared.wave,
        selected_item=selected_item,
        alternative_id=alternative_id,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
        generate_proof_pack=generate_proof_pack,
        construction_repository=construction_repository,
        proof_pack_repository=proof_pack_repository,
        mandate_repository=mandate_repository,
        run_service=run_service,
    )
    persist_transitioned_wave(
        wave_repository=wave_repository,
        source_wave=prepared.wave,
        transitioned_wave=updated,
    )
    return updated


__all__ = ["select_persisted_wave_item_alternative"]
