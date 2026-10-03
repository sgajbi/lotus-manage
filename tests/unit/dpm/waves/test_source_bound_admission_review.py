"""Regression proof for concurrent admission and bounded HTTP input adapters."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock

import pytest

from src.api.request_models import RebalanceRequest
from src.api.routers.wave_request_models import DpmWaveSimulationRequest
from src.api.routers.wave_simulation_http import build_wave_simulation_item_inputs
from src.api.routers.wave_simulation_http import simulate_wave_response
from src.api.services.rebalance_simulation_errors import (
    DpmRebalanceCoreContextIncompleteError,
    DpmRebalanceCoreResolverUnavailableError,
    DpmRebalanceEnvelopeValidationError,
    DpmRebalanceStatefulInputDisabledError,
)
from fastapi import HTTPException
from src.api.services.wave_errors import DpmWaveValidationError
from src.api.services.wave_simulation_operations import admit_wave_simulation_operation
from src.infrastructure.waves.in_memory import InMemoryDpmWaveRepository
from tests.unit.dpm.waves.test_source_bound_simulation_inputs import (
    _source,
    _stateless_input,
    _wave,
)


def test_concurrent_exact_admission_resolves_source_once_and_reuses_winner(monkeypatch):
    repository = InMemoryDpmWaveRepository()
    repository.save_wave(
        wave=_wave(), tenant_id="tenant-contract", idempotency_key=None, request_hash=None
    )
    entered, release, second_finished = Event(), Event(), Event()
    calls, mutex = [], Lock()

    def resolve(**_kwargs):
        with mutex:
            calls.append(1)
            first = len(calls) == 1
        if first:
            entered.set()
            assert release.wait(5)
        return RebalanceRequest.model_validate(_stateless_input()), _source()

    monkeypatch.setattr(
        "src.api.services.rebalance_simulation_service.resolve_rebalance_request_envelope", resolve
    )

    def admit(second=False):
        try:
            return admit_wave_simulation_operation(
                wave_id="wave-contract",
                tenant_id="tenant-contract",
                actor_id="pm",
                correlation_id="corr",
                idempotency_key="same",
                item_payloads=[{"wave_item_id": "item-contract", "input_mode": "stateful"}],
                methods=None,
                max_concurrency=1,
                max_attempts=2,
                repository=repository,
            )
        finally:
            if second:
                second_finished.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(admit)
        assert entered.wait(5)
        second = pool.submit(admit, True)
        try:
            second_finished.wait(0.2)
        finally:
            release.set()
        results = [first.result(5), second.result(5)]
    assert calls == [1]
    assert results[0][0] == results[1][0]
    assert sorted(replay for _operation, replay in results) == [False, True]


def test_legacy_http_builder_keeps_item_and_portfolio_aliases():
    request = DpmWaveSimulationRequest.model_validate(
        {
            "actor_id": "pm",
            "item_inputs": [
                {
                    "wave_item_id": "item-contract",
                    "portfolio_id": "portfolio-contract",
                    "stateless_input": _stateless_input(),
                }
            ],
        }
    )
    inputs = build_wave_simulation_item_inputs(request)
    assert inputs["item-contract"] is inputs["portfolio-contract"]
    assert inputs["item-contract"].stateless_input == RebalanceRequest.model_validate(
        _stateless_input()
    )


def test_http_builder_without_persisted_scope_refuses_stateful_input():
    request = DpmWaveSimulationRequest.model_validate(
        {
            "actor_id": "pm",
            "item_inputs": [{"wave_item_id": "item-contract", "input_mode": "stateful"}],
        }
    )
    with pytest.raises(DpmWaveValidationError, match="persisted wave scope"):
        build_wave_simulation_item_inputs(request)


@pytest.mark.parametrize(
    "error,status",
    [
        (DpmRebalanceCoreContextIncompleteError, 424),
        (DpmRebalanceCoreResolverUnavailableError, 503),
        (DpmRebalanceEnvelopeValidationError, 422),
        (DpmRebalanceStatefulInputDisabledError, 409),
    ],
)
def test_synchronous_http_source_refusal_is_bounded_and_leaves_wave_unchanged(
    monkeypatch, error, status
):
    repository = InMemoryDpmWaveRepository()
    original = _wave()
    repository.save_wave(
        wave=original, tenant_id="tenant-contract", idempotency_key=None, request_hash=None
    )

    def fail(**_kwargs):
        raise error("BOUNDED_SOURCE_REFUSAL")

    monkeypatch.setattr(
        "src.api.services.rebalance_simulation_service.resolve_rebalance_request_envelope", fail
    )
    request = DpmWaveSimulationRequest.model_validate(
        {
            "actor_id": "pm",
            "item_inputs": [{"wave_item_id": "item-contract", "input_mode": "stateful"}],
        }
    )
    with pytest.raises(HTTPException) as caught:
        simulate_wave_response(
            wave_id="wave-contract",
            request=request,
            correlation_id="corr",
            construction_repository=None,
            run_service=None,
            wave_repository=repository,
            tenant_id="tenant-contract",
            risk_authority_client=None,
        )
    assert (caught.value.status_code, caught.value.detail) == (status, "BOUNDED_SOURCE_REFUSAL")
    assert repository.get_wave(wave_id="wave-contract", tenant_id="tenant-contract") == original
