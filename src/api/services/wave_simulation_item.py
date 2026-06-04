from dataclasses import dataclass

from src.api.request_models import RebalanceRequest
from src.api.services import construction_service
from src.api.services.wave_construction_diagnostics import proposed_changes_from_alternative_set
from src.api.services.authority_client_service import RiskAuthorityClient
from src.core.construction.repository import ConstructionRepository
from src.core.construction.vocabulary import ConstructionMethod
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves import DpmRebalanceWaveItem
from src.core.waves.source_analytics import build_source_analytics_from_alternative_set
from src.core.construction.models import ConstructionAuthorityContext


@dataclass(frozen=True)
class DpmWaveSimulationInput:
    stateless_input: RebalanceRequest
    authority_context: ConstructionAuthorityContext | None = None


def simulate_item(
    *,
    item: DpmRebalanceWaveItem,
    correlation_id: str,
    item_inputs: dict[str, RebalanceRequest | DpmWaveSimulationInput],
    methods: list[ConstructionMethod] | None,
    construction_repository: ConstructionRepository,
    run_service: DpmRunSupportService,
    risk_authority_client: RiskAuthorityClient | None,
) -> DpmRebalanceWaveItem:
    if item.state != "SOURCE_READY":
        return item
    simulation_input = item_inputs.get(item.wave_item_id) or item_inputs.get(item.portfolio_id)
    if simulation_input is None:
        return item.model_copy(
            update={
                "state": "SIMULATION_BLOCKED",
                "reason_codes": ["CONSTRUCTION_INPUT_MISSING"],
                "diagnostics": {
                    **item.diagnostics,
                    "source_owner": "wave-simulation-request",
                    "required_action": "SUPPLY_RFC0039_REBALANCE_REQUEST",
                },
            },
            deep=True,
        )
    if isinstance(simulation_input, DpmWaveSimulationInput):
        rebalance_request = simulation_input.stateless_input
        authority_context = simulation_input.authority_context
    else:
        rebalance_request = simulation_input
        authority_context = None
    try:
        alternative_set = construction_service.generate_construction_alternative_set(
            request=rebalance_request,
            idempotency_key=f"wave:{item.wave_item_id}:simulate",
            correlation_id=correlation_id,
            repository=construction_repository,
            methods=methods,
            authority_context=authority_context,
            risk_authority_client=risk_authority_client,
            run_service=run_service,
        )
    except Exception as exc:
        return item.model_copy(
            update={
                "state": "SIMULATION_BLOCKED",
                "reason_codes": ["CONSTRUCTION_ALTERNATIVE_GENERATION_FAILED"],
                "diagnostics": {
                    **item.diagnostics,
                    "source_owner": "lotus-manage-construction",
                    "required_action": "REVIEW_CONSTRUCTION_INPUTS",
                    "construction_error": type(exc).__name__,
                },
            },
            deep=True,
        )
    return item.model_copy(
        update={
            "state": "SIMULATED",
            "alternative_set_id": alternative_set.alternative_set_id,
            "reason_codes": ["CONSTRUCTION_ALTERNATIVES_GENERATED"],
            "diagnostics": {
                **item.diagnostics,
                "construction_state": alternative_set.status.value,
                "alternative_count": len(alternative_set.alternatives),
                "proposed_changes": proposed_changes_from_alternative_set(alternative_set),
                "source_analytics": build_source_analytics_from_alternative_set(alternative_set),
            },
        },
        deep=True,
    )


__all__ = ["DpmWaveSimulationInput", "simulate_item"]
