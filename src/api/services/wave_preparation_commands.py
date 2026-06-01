from src.api.request_models import RebalanceRequest
from src.api.services.wave_simulation import build_simulated_wave
from src.api.services.wave_simulation_item import DpmWaveSimulationInput
from src.api.services.wave_source_check import build_source_checked_wave
from src.api.services.wave_transition_execution import (
    persist_transitioned_wave,
    prepare_wave_transition,
)
from src.core.construction.repository import ConstructionRepository
from src.core.construction.vocabulary import ConstructionMethod
from src.core.mandate_repository import DpmMandateRepository
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves import DpmRebalanceWave, DpmWaveRepository
from src.infrastructure.risk_authority import LotusRiskAuthorityClient


def source_check_persisted_wave(
    *,
    wave_id: str,
    actor_id: str,
    correlation_id: str,
    mandate_repository: DpmMandateRepository,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    prepared = prepare_wave_transition(
        wave_id=wave_id,
        wave_repository=wave_repository,
        replay_states={"SOURCE_CHECKED"},
        allowed_states={"CREATED"},
        error_code="DPM_WAVE_SOURCE_CHECK_INVALID_STATE",
        action_phrase="be source-checked",
    )
    if prepared.replayed:
        return prepared.wave, True

    checked = build_source_checked_wave(
        wave=prepared.wave,
        actor_id=actor_id,
        correlation_id=correlation_id,
        mandate_repository=mandate_repository,
    )
    persist_transitioned_wave(
        wave_repository=wave_repository,
        source_wave=prepared.wave,
        transitioned_wave=checked,
    )
    return checked, False


def simulate_persisted_wave(
    *,
    wave_id: str,
    actor_id: str,
    correlation_id: str,
    item_inputs: dict[str, RebalanceRequest | DpmWaveSimulationInput],
    methods: list[ConstructionMethod] | None,
    construction_repository: ConstructionRepository,
    run_service: DpmRunSupportService,
    wave_repository: DpmWaveRepository,
    risk_authority_client: LotusRiskAuthorityClient | None = None,
) -> tuple[DpmRebalanceWave, bool]:
    prepared = prepare_wave_transition(
        wave_id=wave_id,
        wave_repository=wave_repository,
        replay_states={"SIMULATED", "PARTIALLY_SIMULATED", "SIMULATION_FAILED"},
        allowed_states={"SOURCE_CHECKED"},
        error_code="DPM_WAVE_SIMULATION_INVALID_STATE",
        action_phrase="be simulated",
    )
    if prepared.replayed:
        return prepared.wave, True

    completed = build_simulated_wave(
        wave=prepared.wave,
        actor_id=actor_id,
        correlation_id=correlation_id,
        item_inputs=item_inputs,
        methods=methods,
        construction_repository=construction_repository,
        run_service=run_service,
        risk_authority_client=risk_authority_client,
    )
    persist_transitioned_wave(
        wave_repository=wave_repository,
        source_wave=prepared.wave,
        transitioned_wave=completed,
    )
    return completed, False


__all__ = [
    "simulate_persisted_wave",
    "source_check_persisted_wave",
]
