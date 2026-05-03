from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import src.api.services.rebalance_simulation_service as service
from src.api.request_models import BatchExecutionRequestEnvelope, RebalanceExecutionRequestEnvelope
from src.api.routers.runtime_utils import (
    assert_feature_enabled,
    normalize_backend_init_error,
    postgres_connection_exception_types,
)
from src.core.dpm_source_context import DpmCoreContextIncompleteError, DpmStatefulInput
from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError
from tests.shared.factories import valid_api_payload


def _stateful_input() -> DpmStatefulInput:
    return DpmStatefulInput(portfolio_id="PF_TEST", as_of=date(2026, 4, 10))


def test_request_envelopes_require_matching_stateful_payloads() -> None:
    with pytest.raises(ValidationError, match="DPM_STATEFUL_INPUT_REQUIRED"):
        RebalanceExecutionRequestEnvelope(input_mode="stateful")

    with pytest.raises(ValidationError, match="DPM_STATELESS_INPUT_REQUIRED"):
        BatchExecutionRequestEnvelope(input_mode="stateless")

    with pytest.raises(ValidationError, match="DPM_STATEFUL_SCENARIOS_REQUIRED"):
        BatchExecutionRequestEnvelope(input_mode="stateful", stateful_input=_stateful_input())


def test_runtime_utils_feature_and_backend_guards(monkeypatch) -> None:
    monkeypatch.setenv("DPM_DISABLED_FEATURE", "false")

    with pytest.raises(HTTPException) as exc_info:
        assert_feature_enabled(name="DPM_DISABLED_FEATURE", default=True, detail="FEATURE_DISABLED")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "FEATURE_DISABLED"
    assert (
        normalize_backend_init_error(
            detail="missing-required",
            required_detail="missing-required",
            fallback_detail="fallback",
        )
        == "missing-required"
    )
    assert (
        normalize_backend_init_error(
            detail="driver-error",
            required_detail="missing-required",
            fallback_detail="fallback",
        )
        == "fallback"
    )
    assert ConnectionError in postgres_connection_exception_types()


def test_stateful_source_context_maps_validation_and_resolver_errors(monkeypatch) -> None:
    monkeypatch.setenv("DPM_STATEFUL_CORE_SOURCING_ENABLED", "true")
    envelope = RebalanceExecutionRequestEnvelope(
        input_mode="stateful",
        stateful_input=_stateful_input(),
    )

    class _UnavailableResolver:
        def resolve_execution_context(self, **_kwargs):
            raise DpmCoreResolverUnavailableError("down")

    monkeypatch.setattr(service, "build_core_resolver_client", lambda: _UnavailableResolver())
    with pytest.raises(HTTPException) as unavailable:
        service._resolve_stateful_source_context(envelope=envelope, correlation_id="corr")
    assert unavailable.value.status_code == 503

    class _IncompleteResolver:
        def resolve_execution_context(self, **_kwargs):
            raise DpmCoreResolverError("bad")

    monkeypatch.setattr(service, "build_core_resolver_client", lambda: _IncompleteResolver())
    with pytest.raises(HTTPException) as incomplete:
        service._resolve_stateful_source_context(envelope=envelope, correlation_id="corr")
    assert incomplete.value.status_code == 424

    class _InvalidResolver:
        def resolve_execution_context(self, **_kwargs):
            DpmStatefulInput.model_validate({})

    monkeypatch.setattr(service, "build_core_resolver_client", lambda: _InvalidResolver())
    with pytest.raises(HTTPException) as invalid:
        service._resolve_stateful_source_context(envelope=envelope, correlation_id="corr")
    assert invalid.value.status_code == 424


def test_stateful_source_context_rejects_missing_payload_and_disabled_feature(monkeypatch) -> None:
    missing_payload = RebalanceExecutionRequestEnvelope.model_construct(
        input_mode="stateful",
        stateful_input=None,
        stateless_input=None,
        options_override={},
    )

    with pytest.raises(HTTPException) as missing:
        service._resolve_stateful_source_context(envelope=missing_payload, correlation_id="corr")
    assert missing.value.status_code == 422
    assert missing.value.detail == "DPM_STATEFUL_INPUT_REQUIRED"

    monkeypatch.setenv("DPM_STATEFUL_CORE_SOURCING_ENABLED", "false")
    envelope = RebalanceExecutionRequestEnvelope.model_construct(
        input_mode="stateful",
        stateful_input=_stateful_input(),
        stateless_input=None,
        options_override={},
    )

    with pytest.raises(HTTPException) as disabled:
        service._resolve_stateful_source_context(envelope=envelope, correlation_id="corr")
    assert disabled.value.status_code == 409
    assert disabled.value.detail == "DPM_STATEFUL_INPUT_DISABLED"


def test_stateful_envelope_resolution_maps_transform_failures(monkeypatch) -> None:
    source_context = type("_SourceContext", (), {"context": object()})()
    monkeypatch.setattr(
        service, "_resolve_stateful_source_context", lambda **_kwargs: source_context
    )
    monkeypatch.setattr(
        service,
        "build_rebalance_request_from_core_context",
        lambda **_kwargs: (_ for _ in ()).throw(DpmCoreContextIncompleteError("missing")),
    )

    with pytest.raises(HTTPException) as rebalance_error:
        service.resolve_rebalance_request_envelope(
            envelope=RebalanceExecutionRequestEnvelope(
                input_mode="stateful",
                stateful_input=_stateful_input(),
            ),
            correlation_id="corr",
        )
    assert rebalance_error.value.status_code == 424

    monkeypatch.setattr(
        service,
        "build_batch_rebalance_request_from_core_context",
        lambda **_kwargs: (_ for _ in ()).throw(DpmCoreContextIncompleteError("missing")),
    )
    with pytest.raises(HTTPException) as batch_error:
        service.resolve_batch_request_envelope(
            envelope=BatchExecutionRequestEnvelope(
                input_mode="stateful",
                stateful_input=_stateful_input(),
                scenarios={"base": {"options": {}}},
            ),
            correlation_id="corr",
        )
    assert batch_error.value.status_code == 424


def test_stateless_envelope_resolution_rejects_missing_constructed_payloads() -> None:
    with pytest.raises(HTTPException) as rebalance_error:
        service.resolve_rebalance_request_envelope(
            envelope=RebalanceExecutionRequestEnvelope.model_construct(
                input_mode="stateless",
                stateless_input=None,
                stateful_input=None,
                options_override={},
            ),
            correlation_id="corr",
        )
    assert rebalance_error.value.status_code == 422
    assert rebalance_error.value.detail == "DPM_STATELESS_INPUT_REQUIRED"

    with pytest.raises(HTTPException) as batch_error:
        service.resolve_batch_request_envelope(
            envelope=BatchExecutionRequestEnvelope.model_construct(
                input_mode="stateless",
                stateless_input=None,
                stateful_input=None,
                scenarios={},
            ),
            correlation_id="corr",
        )
    assert batch_error.value.status_code == 422
    assert batch_error.value.detail == "DPM_STATELESS_INPUT_REQUIRED"


def test_async_manual_execution_disabled_is_reported(monkeypatch) -> None:
    monkeypatch.setenv("DPM_ASYNC_MANUAL_EXECUTION_ENABLED", "false")

    with pytest.raises(HTTPException) as exc_info:
        service.execute_dpm_async_operation(operation_id="op_1", service=object())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "DPM_ASYNC_MANUAL_EXECUTION_DISABLED"


def test_service_env_helpers_reject_invalid_values(monkeypatch) -> None:
    monkeypatch.setenv("DPM_TEST_INT", "not-int")
    monkeypatch.setenv("DPM_TEST_FLOAT", "0")
    monkeypatch.setenv("DPM_TEST_BAD_FLOAT", "not-float")
    monkeypatch.delenv("DPM_TEST_MISSING", raising=False)
    monkeypatch.delenv("DPM_CORE_BASE_URL", raising=False)

    assert service.env_int("DPM_TEST_INT", 3) == 3
    assert service.env_int("DPM_TEST_FLOAT", 3) == 3
    assert service.env_float("DPM_TEST_FLOAT", 2.5) == 2.5
    assert service.env_float("DPM_TEST_BAD_FLOAT", 2.5) == 2.5
    assert service.env_float("DPM_TEST_MISSING", 2.5) == 2.5
    with pytest.raises(DpmCoreResolverUnavailableError, match="DPM_CORE_RESOLVER_UNAVAILABLE"):
        service.build_core_resolver_client()


def test_async_operation_disabled_is_reported_before_manual_gate(monkeypatch) -> None:
    monkeypatch.setenv("DPM_ASYNC_OPERATIONS_ENABLED", "false")

    with pytest.raises(HTTPException) as exc_info:
        service.execute_dpm_async_operation(operation_id="op_1", service=object())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "DPM_ASYNC_OPERATIONS_DISABLED"


def test_run_analyze_async_operation_accepts_legacy_request_payload(monkeypatch) -> None:
    batch_payload = valid_api_payload()
    batch_payload.pop("options")
    batch_payload["scenarios"] = {"baseline": {"options": {}}}

    class _SupportService:
        completed: tuple[str, dict] | None = None

        def prepare_analyze_operation_execution(self, *, operation_id: str):
            return batch_payload, "corr-legacy"

        def complete_operation_success(self, *, operation_id: str, result_json: dict):
            self.completed = (operation_id, result_json)

        def complete_operation_failure(self, **_kwargs):
            raise AssertionError("legacy payload should execute successfully")

    fake_service = _SupportService()
    expected = SimpleNamespace(
        model_dump=lambda mode: {
            "results": {"baseline": {"status": "READY"}},
            "comparison_metrics": {},
            "failed_scenarios": {},
        }
    )
    monkeypatch.setattr(service, "execute_batch_analysis", lambda **_kwargs: expected)

    service.run_analyze_async_operation(operation_id="op_legacy", service=fake_service)

    assert fake_service.completed is not None
    assert fake_service.completed[0] == "op_legacy"
    assert set(fake_service.completed[1]["results"]) == {"baseline"}
