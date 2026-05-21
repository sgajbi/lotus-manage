from __future__ import annotations

from src.api.request_models import RebalanceRequest
from src.api.routers.wave_request_models import DpmWaveSimulationRequest
from src.api.services import wave_service


def build_wave_simulation_item_inputs(
    request: DpmWaveSimulationRequest,
) -> dict[str, RebalanceRequest | wave_service.DpmWaveSimulationInput]:
    item_inputs: dict[str, RebalanceRequest | wave_service.DpmWaveSimulationInput] = {}
    for item_input in request.item_inputs:
        simulation_input = wave_service.DpmWaveSimulationInput(
            stateless_input=item_input.stateless_input,
            authority_context=item_input.authority_context,
        )
        if item_input.wave_item_id:
            item_inputs[item_input.wave_item_id] = simulation_input
        if item_input.portfolio_id:
            item_inputs[item_input.portfolio_id] = simulation_input
    return item_inputs
