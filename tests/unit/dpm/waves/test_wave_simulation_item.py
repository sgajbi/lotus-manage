import pytest
from pytest import MonkeyPatch

from src.api.request_models import RebalanceRequest
from src.api.services import wave_simulation_item
from src.api.services.wave_simulation_item import DpmWaveSimulationInput, simulate_item
from src.core.construction.models import (
    ConstructionAlternative,
    ConstructionAlternativeSet,
    ConstructionAuthorityContext,
)
from src.core.construction.repository import ConstructionIdempotencyConflictError
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.waves import DpmRebalanceWaveItem


def _item(*, state: str = "SOURCE_READY") -> DpmRebalanceWaveItem:
    return DpmRebalanceWaveItem(
        wave_item_id="dwi_simulate",
        portfolio_id="PB_SG_SIMULATE",
        state=state,
        diagnostics={"existing": "value"},
    )


def _request() -> RebalanceRequest:
    return RebalanceRequest.model_construct(portfolio_id="PB_SG_SIMULATE")


def _alternative_set() -> ConstructionAlternativeSet:
    return ConstructionAlternativeSet.model_construct(
        alternative_set_id="cas_simulate",
        portfolio_id="PB_SG_SIMULATE",
        as_of="2026-05-03",
        status=ConstructionMethodStatus.READY,
        alternatives=[
            ConstructionAlternative.model_construct(
                alternative_id="alt_001",
                method="heuristic",
                method_status=ConstructionMethodStatus.READY,
                diagnostics={
                    "proposed_changes": [
                        {"security_id": "SEC_A", "target_weight": "0.10"},
                    ]
                },
            )
        ],
    )


def test_simulate_item_returns_non_source_ready_item_unchanged() -> None:
    item = _item(state="CANDIDATE")

    assert (
        simulate_item(
            item=item,
            correlation_id="corr-simulate",
            item_inputs={},
            methods=None,
            construction_repository=object(),  # type: ignore[arg-type]
            run_service=object(),  # type: ignore[arg-type]
            risk_authority_client=None,
        )
        is item
    )


def test_simulate_item_blocks_missing_construction_input() -> None:
    updated = simulate_item(
        item=_item(),
        correlation_id="corr-simulate",
        item_inputs={},
        methods=None,
        construction_repository=object(),  # type: ignore[arg-type]
        run_service=object(),  # type: ignore[arg-type]
        risk_authority_client=None,
    )

    assert updated.state == "SIMULATION_BLOCKED"
    assert updated.reason_codes == ["CONSTRUCTION_INPUT_MISSING"]
    assert updated.diagnostics == {
        "existing": "value",
        "source_owner": "wave-simulation-request",
        "required_action": "SUPPLY_RFC0039_REBALANCE_REQUEST",
    }


def test_simulation_input_for_item_prefers_wave_item_id_then_portfolio_id() -> None:
    wave_input = DpmWaveSimulationInput(stateless_input=_request())
    portfolio_input = _request()

    assert (
        wave_simulation_item._simulation_input_for_item(
            item=_item(),
            item_inputs={
                "dwi_simulate": wave_input,
                "PB_SG_SIMULATE": portfolio_input,
            },
        )
        is wave_input
    )
    assert (
        wave_simulation_item._simulation_input_for_item(
            item=_item(),
            item_inputs={"PB_SG_SIMULATE": portfolio_input},
        )
        is portfolio_input
    )
    assert wave_simulation_item._simulation_input_for_item(item=_item(), item_inputs={}) is None


def test_simulation_request_and_authority_context_normalizes_input_shapes() -> None:
    request = _request()
    authority_context = ConstructionAuthorityContext()

    wrapped_request, wrapped_context = (
        wave_simulation_item._simulation_request_and_authority_context(
            DpmWaveSimulationInput(
                stateless_input=request,
                authority_context=authority_context,
            )
        )
    )
    plain_request, plain_context = wave_simulation_item._simulation_request_and_authority_context(
        request
    )

    assert wrapped_request is request
    assert wrapped_context is authority_context
    assert plain_request is request
    assert plain_context is None


def test_missing_construction_input_item_preserves_existing_diagnostics() -> None:
    updated = wave_simulation_item._missing_construction_input_item(_item())

    assert updated.state == "SIMULATION_BLOCKED"
    assert updated.reason_codes == ["CONSTRUCTION_INPUT_MISSING"]
    assert updated.diagnostics == {
        "existing": "value",
        "source_owner": "wave-simulation-request",
        "required_action": "SUPPLY_RFC0039_REBALANCE_REQUEST",
    }


def test_simulate_item_records_generated_construction_alternative_set(
    monkeypatch: MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _generate(**kwargs: object) -> ConstructionAlternativeSet:
        captured.update(kwargs)
        return _alternative_set()

    monkeypatch.setattr(
        wave_simulation_item.construction_service,
        "generate_construction_alternative_set",
        _generate,
    )

    updated = simulate_item(
        item=_item(),
        correlation_id="corr-simulate",
        item_inputs={
            "dwi_simulate": DpmWaveSimulationInput(stateless_input=_request()),
        },
        methods=None,
        construction_repository=object(),  # type: ignore[arg-type]
        run_service=object(),  # type: ignore[arg-type]
        risk_authority_client=None,
    )

    assert captured["idempotency_key"] == "wave:dwi_simulate:simulate"
    assert captured["correlation_id"] == "corr-simulate"
    assert updated.state == "SIMULATED"
    assert updated.alternative_set_id == "cas_simulate"
    assert updated.reason_codes == ["CONSTRUCTION_ALTERNATIVES_GENERATED"]
    assert updated.diagnostics["construction_state"] == "READY"
    assert updated.diagnostics["alternative_count"] == 1
    assert updated.diagnostics["proposed_changes"] == [
        {"security_id": "SEC_A", "target_weight": "0.10"}
    ]


def test_simulated_item_records_construction_posture() -> None:
    updated = wave_simulation_item._simulated_item(
        item=_item(),
        alternative_set=_alternative_set(),
    )

    assert updated.state == "SIMULATED"
    assert updated.alternative_set_id == "cas_simulate"
    assert updated.reason_codes == ["CONSTRUCTION_ALTERNATIVES_GENERATED"]
    assert updated.diagnostics["construction_state"] == "READY"
    assert updated.diagnostics["alternative_count"] == 1
    assert updated.diagnostics["proposed_changes"] == [
        {"security_id": "SEC_A", "target_weight": "0.10"}
    ]


def test_simulate_item_blocks_construction_generation_failure(
    monkeypatch: MonkeyPatch,
) -> None:
    def _generate(**_kwargs: object) -> ConstructionAlternativeSet:
        raise ConstructionIdempotencyConflictError("CONSTRUCTION_IDEMPOTENCY_KEY_CONFLICT")

    monkeypatch.setattr(
        wave_simulation_item.construction_service,
        "generate_construction_alternative_set",
        _generate,
    )

    updated = simulate_item(
        item=_item(),
        correlation_id="corr-simulate",
        item_inputs={"PB_SG_SIMULATE": _request()},
        methods=None,
        construction_repository=object(),  # type: ignore[arg-type]
        run_service=object(),  # type: ignore[arg-type]
        risk_authority_client=None,
    )

    assert updated.state == "SIMULATION_BLOCKED"
    assert updated.reason_codes == ["CONSTRUCTION_ALTERNATIVE_GENERATION_FAILED"]
    assert updated.diagnostics == {
        "existing": "value",
        "source_owner": "lotus-manage-construction",
        "required_action": "REVIEW_CONSTRUCTION_INPUTS",
        "construction_error": "ConstructionIdempotencyConflictError",
    }


def test_construction_generation_failed_item_records_safe_error_type() -> None:
    updated = wave_simulation_item._construction_generation_failed_item(
        item=_item(),
        exc=ValueError("raw request details stay out of diagnostics"),
    )

    assert updated.state == "SIMULATION_BLOCKED"
    assert updated.reason_codes == ["CONSTRUCTION_ALTERNATIVE_GENERATION_FAILED"]
    assert updated.diagnostics == {
        "existing": "value",
        "source_owner": "lotus-manage-construction",
        "required_action": "REVIEW_CONSTRUCTION_INPUTS",
        "construction_error": "ValueError",
    }


def test_simulate_item_does_not_hide_unexpected_construction_generation_failure(
    monkeypatch: MonkeyPatch,
) -> None:
    def _generate(**_kwargs: object) -> ConstructionAlternativeSet:
        raise RuntimeError("construction repository side effect failed")

    monkeypatch.setattr(
        wave_simulation_item.construction_service,
        "generate_construction_alternative_set",
        _generate,
    )

    with pytest.raises(RuntimeError, match="construction repository side effect failed"):
        simulate_item(
            item=_item(),
            correlation_id="corr-simulate",
            item_inputs={"PB_SG_SIMULATE": _request()},
            methods=None,
            construction_repository=object(),  # type: ignore[arg-type]
            run_service=object(),  # type: ignore[arg-type]
            risk_authority_client=None,
        )


def test_wave_simulation_item_exports_only_simulation_item_contract() -> None:
    assert wave_simulation_item.__all__ == ["DpmWaveSimulationInput", "simulate_item"]
