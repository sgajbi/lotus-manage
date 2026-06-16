from dataclasses import dataclass

from src.api.request_models import RebalanceRequest
from src.api.services import construction_service
from src.api.services.wave_construction_diagnostics import proposed_changes_from_alternative_set
from src.api.services.authority_client_service import RiskAuthorityClient
from src.core.construction.repository import (
    ConstructionIdempotencyConflictError,
    ConstructionRepository,
)
from src.core.construction.vocabulary import ConstructionMethod
from src.core.rebalance_runs.service import DpmAsyncOperationConflictError, DpmRunSupportService
from src.core.waves import DpmRebalanceWaveItem
from src.core.waves.source_analytics import build_source_analytics_from_alternative_set
from src.core.construction.models import ConstructionAlternativeSet, ConstructionAuthorityContext

_CONSTRUCTION_SIMULATION_BLOCKING_ERRORS = (
    ConstructionIdempotencyConflictError,
    DpmAsyncOperationConflictError,
    ValueError,
)


@dataclass(frozen=True)
class DpmWaveSimulationInput:
    stateless_input: RebalanceRequest
    authority_context: ConstructionAuthorityContext | None = None


def _simulation_input_for_item(
    *,
    item: DpmRebalanceWaveItem,
    item_inputs: dict[str, RebalanceRequest | DpmWaveSimulationInput],
) -> RebalanceRequest | DpmWaveSimulationInput | None:
    return item_inputs.get(item.wave_item_id) or item_inputs.get(item.portfolio_id)


def _simulation_request_and_authority_context(
    simulation_input: RebalanceRequest | DpmWaveSimulationInput,
) -> tuple[RebalanceRequest, ConstructionAuthorityContext | None]:
    if isinstance(simulation_input, DpmWaveSimulationInput):
        return simulation_input.stateless_input, simulation_input.authority_context
    return simulation_input, None


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
    simulation_input = _simulation_input_for_item(item=item, item_inputs=item_inputs)
    if simulation_input is None:
        return _missing_construction_input_item(item)
    rebalance_request, authority_context = _simulation_request_and_authority_context(
        simulation_input
    )
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
    except _CONSTRUCTION_SIMULATION_BLOCKING_ERRORS as exc:
        return _construction_generation_failed_item(item=item, exc=exc)
    return _simulated_item(item=item, alternative_set=alternative_set)


def _missing_construction_input_item(
    item: DpmRebalanceWaveItem,
) -> DpmRebalanceWaveItem:
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


def _construction_generation_failed_item(
    *,
    item: DpmRebalanceWaveItem,
    exc: BaseException,
) -> DpmRebalanceWaveItem:
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


def _simulated_item(
    *,
    item: DpmRebalanceWaveItem,
    alternative_set: ConstructionAlternativeSet,
) -> DpmRebalanceWaveItem:
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
