from src.api.request_models import RebalanceRequest
from src.api.services.wave_aggregate_metrics import (
    aggregate_wave_items,
    simulation_result_state,
)
from src.api.services.wave_event_evidence import build_wave_event
from src.api.services.wave_simulation_item import DpmWaveSimulationInput, simulate_item
from src.core.construction.repository import ConstructionRepository
from src.core.construction.vocabulary import ConstructionMethod
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves import DpmRebalanceWave, apply_wave_transition
from src.infrastructure.risk_authority import LotusRiskAuthorityClient


def build_simulated_wave(
    *,
    wave: DpmRebalanceWave,
    actor_id: str,
    correlation_id: str,
    item_inputs: dict[str, RebalanceRequest | DpmWaveSimulationInput],
    methods: list[ConstructionMethod] | None,
    construction_repository: ConstructionRepository,
    run_service: DpmRunSupportService,
    risk_authority_client: LotusRiskAuthorityClient | None = None,
) -> DpmRebalanceWave:
    simulating = apply_wave_transition(
        wave=wave,
        to_state="SIMULATING",
        event=build_wave_event(
            wave_id=wave.wave_id,
            from_state="SOURCE_CHECKED",
            to_state="SIMULATING",
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_SIMULATION_STARTED",
            metadata={"ready_item_count": wave.aggregate_metrics.ready_item_count},
        ),
    )
    simulated_items = [
        simulate_item(
            item=item,
            correlation_id=correlation_id,
            item_inputs=item_inputs,
            methods=methods,
            construction_repository=construction_repository,
            run_service=run_service,
            risk_authority_client=risk_authority_client,
        )
        for item in simulating.items
    ]
    candidate = simulating.model_copy(
        update={
            "items": simulated_items,
            "aggregate_metrics": aggregate_wave_items(simulated_items),
        },
        deep=True,
    )
    to_state = simulation_result_state(simulated_items)
    return apply_wave_transition(
        wave=candidate,
        to_state=to_state,
        event=build_wave_event(
            wave_id=wave.wave_id,
            from_state="SIMULATING",
            to_state=to_state,
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_SIMULATION_COMPLETED",
            metadata={
                "state_counts": candidate.aggregate_metrics.state_counts,
                "ready_item_count": candidate.aggregate_metrics.ready_item_count,
                "blocked_item_count": candidate.aggregate_metrics.blocked_item_count,
            },
        ),
    )


__all__ = ["build_simulated_wave"]
