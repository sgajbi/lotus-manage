from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import src.api.services.core_resolver_service as core_resolver_service
import src.api.services.rebalance_async_config as async_config
import src.api.services.rebalance_async_manual_execution as async_manual_execution
import src.api.services.rebalance_async_operation_completion as async_completion
import src.api.services.rebalance_async_operation_payload as async_payload
import src.api.services.rebalance_async_operation_runner as async_runner
import src.api.services.rebalance_async_submission as async_submission
import src.api.services.rebalance_async_submission_payload as async_submission_payload
import src.api.services.rebalance_batch_execution as batch_execution
import src.api.services.rebalance_batch_scenario_execution as batch_scenario_execution
import src.api.services.rebalance_idempotency_replay as idempotency_replay
import src.api.services.rebalance_policy_pack_execution as policy_pack_execution
import src.api.services.rebalance_request_envelope_resolution as envelope_resolution
import src.api.services.rebalance_runtime_overrides as runtime_overrides
import src.api.services.rebalance_source_lineage as source_lineage_service
import src.api.services.rebalance_simulation_service as service
import src.api.services.rebalance_stateful_source_context as stateful_source_context
import src.api.services.rebalance_sync_execution as sync_execution
import src.api.services.rebalance_supportability_write as supportability_write
import src.api.request_models as request_models
from src.api.services.rebalance_batch_analysis import resolve_base_snapshot_ids
import src.api.services.rebalance_run_support_service as run_support_service
import src.api.main as api_main
from src.api.request_models import (
    BatchExecutionRequestEnvelope,
    RebalanceExecutionRequestEnvelope,
    RebalanceRequest,
)
from src.api.routers.rebalance_simulation_http import rebalance_envelope_http_exception
from src.api.routers.runtime_utils import (
    assert_feature_enabled,
    normalize_backend_init_error,
    postgres_connection_exception_types,
)
from src.core.dpm_source_context import DpmCoreContextIncompleteError, DpmStatefulInput
from src.core.models import BatchRebalanceRequest
from src.core.rebalance.policy_packs import (
    DpmEffectivePolicyPackResolution,
    DpmPolicyPackDefinition,
)
from src.core.rebalance.engine import run_simulation
from src.core.rebalance_runs import (
    DpmAsyncAcceptedResponse,
    DpmAsyncOperationConflictError,
    DpmRunNotFoundError,
)
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


def test_request_envelopes_accept_valid_stateless_and_stateful_payloads() -> None:
    rebalance_request = RebalanceRequest.model_validate(valid_api_payload())
    batch_request = BatchRebalanceRequest.model_validate(
        {
            **valid_api_payload(),
            "scenarios": {"baseline": {"options": {}}},
        }
    )

    rebalance_envelope = RebalanceExecutionRequestEnvelope(
        input_mode="stateless",
        stateless_input=rebalance_request,
    )
    batch_envelope = BatchExecutionRequestEnvelope(
        input_mode="stateless",
        stateless_input=batch_request,
    )
    stateful_batch_envelope = BatchExecutionRequestEnvelope(
        input_mode="stateful",
        stateful_input=_stateful_input(),
        scenarios={"baseline": {"options": {}}},
    )

    assert rebalance_envelope.stateless_input is rebalance_request
    assert batch_envelope.stateless_input is batch_request
    assert stateful_batch_envelope.stateful_input == _stateful_input()
    assert set(stateful_batch_envelope.scenarios) == {"baseline"}


def test_input_mode_payload_helpers_preserve_error_codes() -> None:
    with pytest.raises(ValueError, match="DPM_STATELESS_INPUT_REQUIRED"):
        request_models._require_input_mode_payload(
            input_mode="stateless",
            stateless_input=None,
            stateful_input=None,
        )

    with pytest.raises(ValueError, match="DPM_STATEFUL_INPUT_REQUIRED"):
        request_models._require_input_mode_payload(
            input_mode="stateful",
            stateless_input=None,
            stateful_input=None,
        )

    with pytest.raises(ValueError, match="DPM_STATEFUL_SCENARIOS_REQUIRED"):
        request_models._require_stateful_scenarios(input_mode="stateful", scenarios={})


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


def test_rebalance_runtime_overrides_fall_back_for_missing_main_exports() -> None:
    def _default_callable() -> str:
        return "default"

    assert (
        runtime_overrides.resolve_callable_override(
            "__missing_lotus_manage_override__",
            _default_callable,
        )
        is _default_callable
    )
    assert runtime_overrides.resolve_main_override("__missing_lotus_manage_override__") is None


def test_main_does_not_export_unused_async_runner_override() -> None:
    assert not hasattr(api_main, "_run_analyze_async_operation")
    assert "_run_analyze_async_operation" not in api_main.__all__


def test_rebalance_run_support_provider_raises_application_error(monkeypatch) -> None:
    run_support_service.reset_dpm_run_support_service_for_tests()

    def _raise_missing_dsn():
        raise RuntimeError("DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED")

    monkeypatch.setattr(
        run_support_service.rebalance_run_support_config, "build_repository", _raise_missing_dsn
    )

    with pytest.raises(run_support_service.DpmRunSupportServiceUnavailableError) as exc_info:
        run_support_service.get_dpm_run_support_service()

    assert exc_info.value.detail == "DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED"


def test_rebalance_batch_analysis_resolves_base_snapshot_ids() -> None:
    batch_payload = valid_api_payload()
    batch_payload.pop("options")
    batch_payload["scenarios"] = {"baseline": {"options": {}}}
    batch_payload["portfolio_snapshot"]["snapshot_id"] = None
    batch_payload["market_data_snapshot"]["snapshot_id"] = None
    request = BatchRebalanceRequest.model_validate(batch_payload)

    assert resolve_base_snapshot_ids(request) == {
        "portfolio_snapshot_id": request.portfolio_snapshot.portfolio_id,
        "market_data_snapshot_id": "md",
    }


def test_stateful_source_context_maps_validation_and_resolver_errors(monkeypatch) -> None:
    monkeypatch.setenv("DPM_STATEFUL_CORE_SOURCING_ENABLED", "true")
    envelope = RebalanceExecutionRequestEnvelope(
        input_mode="stateful",
        stateful_input=_stateful_input(),
    )

    class _UnavailableResolver:
        def resolve_execution_context(self, **_kwargs):
            raise DpmCoreResolverUnavailableError("down")

    monkeypatch.setattr(
        core_resolver_service, "build_core_resolver_client", lambda: _UnavailableResolver()
    )
    with pytest.raises(service.DpmRebalanceCoreResolverUnavailableError) as unavailable:
        service._resolve_stateful_source_context(envelope=envelope, correlation_id="corr")
    assert rebalance_envelope_http_exception(unavailable.value).status_code == 503

    class _IncompleteResolver:
        def resolve_execution_context(self, **_kwargs):
            raise DpmCoreResolverError("bad")

    monkeypatch.setattr(
        core_resolver_service, "build_core_resolver_client", lambda: _IncompleteResolver()
    )
    with pytest.raises(service.DpmRebalanceCoreContextIncompleteError) as incomplete:
        service._resolve_stateful_source_context(envelope=envelope, correlation_id="corr")
    assert incomplete.value.detail == "DPM_CORE_CONTEXT_INCOMPLETE"
    assert rebalance_envelope_http_exception(incomplete.value).status_code == 424

    class _DerivedIncompleteResolver:
        def resolve_execution_context(self, **_kwargs):
            raise DpmCoreContextIncompleteError("MARKET_DATA_STALE")

    monkeypatch.setattr(
        core_resolver_service, "build_core_resolver_client", lambda: _DerivedIncompleteResolver()
    )
    with pytest.raises(service.DpmRebalanceCoreContextIncompleteError) as derived_incomplete:
        service._resolve_stateful_source_context(envelope=envelope, correlation_id="corr")
    assert derived_incomplete.value.detail == "DPM_CORE_CONTEXT_INCOMPLETE"
    assert rebalance_envelope_http_exception(derived_incomplete.value).status_code == 424

    class _InvalidResolver:
        def resolve_execution_context(self, **_kwargs):
            DpmStatefulInput.model_validate({})

    monkeypatch.setattr(
        core_resolver_service, "build_core_resolver_client", lambda: _InvalidResolver()
    )
    with pytest.raises(service.DpmRebalanceCoreContextIncompleteError) as invalid:
        service._resolve_stateful_source_context(envelope=envelope, correlation_id="corr")
    assert rebalance_envelope_http_exception(invalid.value).status_code == 424


def test_stateful_source_context_rejects_missing_payload_and_disabled_feature(monkeypatch) -> None:
    missing_payload = RebalanceExecutionRequestEnvelope.model_construct(
        input_mode="stateful",
        stateful_input=None,
        stateless_input=None,
        options_override={},
    )

    with pytest.raises(service.DpmRebalanceEnvelopeValidationError) as missing:
        service._resolve_stateful_source_context(envelope=missing_payload, correlation_id="corr")
    assert missing.value.detail == "DPM_STATEFUL_INPUT_REQUIRED"
    assert rebalance_envelope_http_exception(missing.value).status_code == 422

    monkeypatch.setenv("DPM_STATEFUL_CORE_SOURCING_ENABLED", "false")
    envelope = RebalanceExecutionRequestEnvelope.model_construct(
        input_mode="stateful",
        stateful_input=_stateful_input(),
        stateless_input=None,
        options_override={},
    )

    with pytest.raises(service.DpmRebalanceStatefulInputDisabledError) as disabled:
        service._resolve_stateful_source_context(envelope=envelope, correlation_id="corr")
    assert disabled.value.detail == "DPM_STATEFUL_INPUT_DISABLED"
    assert rebalance_envelope_http_exception(disabled.value).status_code == 409


def test_stateful_source_context_helper_gates_before_resolver_call() -> None:
    def _unexpected_resolver():
        raise AssertionError("resolver should not be constructed")

    missing_payload = RebalanceExecutionRequestEnvelope.model_construct(
        input_mode="stateful",
        stateful_input=None,
        stateless_input=None,
        options_override={},
    )
    with pytest.raises(service.DpmRebalanceEnvelopeValidationError):
        stateful_source_context.resolve_stateful_source_context(
            envelope=missing_payload,
            correlation_id="corr",
            stateful_enabled=True,
            resolver_factory=_unexpected_resolver,
        )

    disabled_payload = RebalanceExecutionRequestEnvelope.model_construct(
        input_mode="stateful",
        stateful_input=_stateful_input(),
        stateless_input=None,
        options_override={},
    )
    with pytest.raises(service.DpmRebalanceStatefulInputDisabledError):
        stateful_source_context.resolve_stateful_source_context(
            envelope=disabled_payload,
            correlation_id="corr",
            stateful_enabled=False,
            resolver_factory=_unexpected_resolver,
        )


def test_stateful_source_context_helpers_project_gates_and_success_posture() -> None:
    stateful_input = _stateful_input()
    envelope = RebalanceExecutionRequestEnvelope.model_construct(
        input_mode="stateful",
        stateful_input=stateful_input,
        stateless_input=None,
        options_override={},
    )

    assert (
        stateful_source_context._stateful_source_input(
            envelope=envelope,
            stateful_enabled=True,
        )
        == stateful_input
    )
    with pytest.raises(service.DpmRebalanceStatefulInputDisabledError):
        stateful_source_context._stateful_source_input(
            envelope=envelope,
            stateful_enabled=False,
        )

    ready_context = SimpleNamespace(supportability=SimpleNamespace(state="READY"))
    degraded_context = SimpleNamespace(supportability=SimpleNamespace(state="DEGRADED"))
    assert (
        stateful_source_context._core_resolver_supportability_state(context=ready_context)
        == "ready"
    )
    assert stateful_source_context._core_resolver_success_reason(context=ready_context) == "ready"
    assert (
        stateful_source_context._core_resolver_success_reason(context=degraded_context)
        == "degraded"
    )


def test_rebalance_request_envelope_resolution_handles_stateless_and_transform_failure() -> None:
    request = RebalanceRequest.model_validate(valid_api_payload())
    stateless_envelope = RebalanceExecutionRequestEnvelope(
        input_mode="stateless",
        stateless_input=request,
    )

    resolved_request, source_context = envelope_resolution.resolve_rebalance_request_envelope(
        envelope=stateless_envelope,
        correlation_id="corr",
        stateful_context_resolver=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("stateless should not resolve source context")
        ),
        rebalance_request_builder=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("stateless should not rebuild request")
        ),
    )

    assert resolved_request is request
    assert source_context is None

    stateful_envelope = RebalanceExecutionRequestEnvelope(
        input_mode="stateful",
        stateful_input=_stateful_input(),
    )
    with pytest.raises(service.DpmRebalanceCoreContextIncompleteError):
        envelope_resolution.resolve_rebalance_request_envelope(
            envelope=stateful_envelope,
            correlation_id="corr",
            stateful_context_resolver=lambda **_kwargs: SimpleNamespace(context=object()),
            rebalance_request_builder=lambda **_kwargs: (_ for _ in ()).throw(
                DpmCoreContextIncompleteError("missing")
            ),
        )


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

    with pytest.raises(service.DpmRebalanceCoreContextIncompleteError) as rebalance_error:
        service.resolve_rebalance_request_envelope(
            envelope=RebalanceExecutionRequestEnvelope(
                input_mode="stateful",
                stateful_input=_stateful_input(),
            ),
            correlation_id="corr",
        )
    assert rebalance_envelope_http_exception(rebalance_error.value).status_code == 424

    monkeypatch.setattr(
        service,
        "build_batch_rebalance_request_from_core_context",
        lambda **_kwargs: (_ for _ in ()).throw(DpmCoreContextIncompleteError("missing")),
    )
    with pytest.raises(service.DpmRebalanceCoreContextIncompleteError) as batch_error:
        service.resolve_batch_request_envelope(
            envelope=BatchExecutionRequestEnvelope(
                input_mode="stateful",
                stateful_input=_stateful_input(),
                scenarios={"base": {"options": {}}},
            ),
            correlation_id="corr",
        )
    assert rebalance_envelope_http_exception(batch_error.value).status_code == 424


def test_stateless_envelope_resolution_rejects_missing_constructed_payloads() -> None:
    with pytest.raises(service.DpmRebalanceEnvelopeValidationError) as rebalance_error:
        service.resolve_rebalance_request_envelope(
            envelope=RebalanceExecutionRequestEnvelope.model_construct(
                input_mode="stateless",
                stateless_input=None,
                stateful_input=None,
                options_override={},
            ),
            correlation_id="corr",
        )
    assert rebalance_error.value.detail == "DPM_STATELESS_INPUT_REQUIRED"
    assert rebalance_envelope_http_exception(rebalance_error.value).status_code == 422

    with pytest.raises(service.DpmRebalanceEnvelopeValidationError) as batch_error:
        service.resolve_batch_request_envelope(
            envelope=BatchExecutionRequestEnvelope.model_construct(
                input_mode="stateless",
                stateless_input=None,
                stateful_input=None,
                scenarios={},
            ),
            correlation_id="corr",
        )
    assert batch_error.value.detail == "DPM_STATELESS_INPUT_REQUIRED"
    assert rebalance_envelope_http_exception(batch_error.value).status_code == 422


def test_async_manual_execution_disabled_is_reported(monkeypatch) -> None:
    monkeypatch.setenv("DPM_ASYNC_MANUAL_EXECUTION_ENABLED", "false")

    with pytest.raises(service.DpmRebalanceAsyncManualExecutionDisabledError) as exc_info:
        service.execute_dpm_async_operation(operation_id="op_1", service=object())

    assert exc_info.value.detail == "DPM_ASYNC_MANUAL_EXECUTION_DISABLED"


def test_core_resolver_service_env_helpers_reject_invalid_values(monkeypatch) -> None:
    monkeypatch.setenv("DPM_TEST_INT", "not-int")
    monkeypatch.setenv("DPM_TEST_FLOAT", "0")
    monkeypatch.setenv("DPM_TEST_BAD_FLOAT", "not-float")
    monkeypatch.delenv("DPM_TEST_MISSING", raising=False)
    monkeypatch.delenv("DPM_CORE_BASE_URL", raising=False)

    assert core_resolver_service.env_int("DPM_TEST_INT", 3) == 3
    assert core_resolver_service.env_int("DPM_TEST_FLOAT", 3) == 3
    assert core_resolver_service.env_float("DPM_TEST_FLOAT", 2.5) == 2.5
    assert core_resolver_service.env_float("DPM_TEST_BAD_FLOAT", 2.5) == 2.5
    assert core_resolver_service.env_float("DPM_TEST_MISSING", 2.5) == 2.5
    with pytest.raises(DpmCoreResolverUnavailableError, match="DPM_CORE_RESOLVER_UNAVAILABLE"):
        core_resolver_service.build_core_resolver_client()


def test_core_resolver_service_builds_config_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DPM_CORE_BASE_URL", "http://lotus-core.test")
    monkeypatch.setenv("DPM_CORE_QUERY_BASE_URL", "http://lotus-core-query.test")
    monkeypatch.setenv("DPM_CORE_TRANSACTION_COST_LOOKBACK_DAYS", "30")
    monkeypatch.setenv("DPM_CORE_RESOLVER_TIMEOUT_SECONDS", "3.5")
    monkeypatch.setenv("DPM_CORE_RESOLVER_MAX_ATTEMPTS", "4")

    resolver = core_resolver_service.build_core_resolver_client()

    assert resolver._config.base_url == "http://lotus-core.test"
    assert resolver._config.query_base_url == "http://lotus-core-query.test"
    assert resolver._config.transaction_cost_lookback_days == 30
    assert resolver._config.timeout_seconds == 3.5
    assert resolver._config.max_attempts == 4


def test_core_resolver_service_exports_resolver_configuration_surface() -> None:
    assert core_resolver_service.__all__ == [
        "build_core_resolver_client",
        "env_float",
        "env_flag",
        "env_int",
        "stateful_core_sourcing_enabled",
    ]


def test_service_modules_route_core_resolver_types_via_service_boundary() -> None:
    for service_module in (
        "src/api/services/mandate_optional_sources.py",
        "src/api/services/mandate_refresh.py",
        "src/api/services/mandate_service.py",
        "src/api/services/rebalance_stateful_source_context.py",
        "src/api/services/wave_core_portfolio_universe_resolution.py",
    ):
        source = Path(service_module).read_text(encoding="utf-8")
        assert "from src.infrastructure.core_sourcing import" not in source, (
            f"{service_module} should import core resolver symbols via core_resolver_service"
        )


def test_service_modules_route_risk_authority_types_via_service_boundary() -> None:
    for service_module in (
        "src/api/services/construction_alternative_builder.py",
        "src/api/services/construction_method_authority.py",
        "src/api/services/wave_preparation_commands.py",
        "src/api/services/wave_service.py",
        "src/api/services/wave_simulation.py",
        "src/api/services/wave_simulation_item.py",
    ):
        source = Path(service_module).read_text(encoding="utf-8")
        assert "from src.infrastructure.risk_authority import" not in source, (
            f"{service_module} should import risk authority symbols via authority_client_service"
        )


def test_service_modules_do_not_import_infrastructure_directly_except_boundary_adapters() -> None:
    allowed_infra_import_modules = {
        "src/api/services/authority_client_service.py",
        "src/api/services/core_resolver_service.py",
        "src/api/services/rebalance_policy_pack_repository.py",
        "src/api/services/rebalance_run_support_repository.py",
    }
    service_dir = Path("src/api/services")
    for path in sorted(service_dir.glob("*.py")):
        module_path = str(path).replace("\\", "/")
        if module_path in allowed_infra_import_modules:
            continue
        source = path.read_text(encoding="utf-8")
        assert "from src.infrastructure" not in source, (
            f"{module_path} should not import directly from src.infrastructure"
        )


def test_rebalance_source_lineage_stamps_result_metadata() -> None:
    stateless_result = SimpleNamespace(lineage=SimpleNamespace(input_mode="stateful"))

    assert source_lineage_service.source_input_mode(None) == "stateless"
    assert (
        source_lineage_service.apply_source_lineage(
            result=stateless_result,
            source_context=None,
        )
        is stateless_result
    )
    assert stateless_result.lineage.input_mode == "stateless"

    source_context = SimpleNamespace(
        source_system="lotus-core",
        stateful_context_hash="stateful-hash-001",
        context=SimpleNamespace(
            source_lineage=SimpleNamespace(
                portfolio_snapshot_id="core-pf-snap-001",
                market_data_snapshot_id="core-md-snap-001",
                model_portfolio_id="model-balanced",
                model_portfolio_version="2026-04-10",
                shelf_version="shelf-sg-v1",
                integration_policy_version="dpm-core-context.v1",
                source_lineage_bundle_id="lineage-bundle-001",
            ),
            supportability=SimpleNamespace(state="READY"),
        ),
    )
    stateful_result = SimpleNamespace(lineage=SimpleNamespace(input_mode="stateless"))

    assert source_lineage_service.source_input_mode(source_context) == "stateful"
    source_lineage_service.apply_source_lineage(
        result=stateful_result,
        source_context=source_context,
    )

    assert stateful_result.lineage.input_mode == "stateful"
    assert stateful_result.lineage.source_system == "lotus-core"
    assert stateful_result.lineage.portfolio_snapshot_id == "core-pf-snap-001"
    assert stateful_result.lineage.market_data_snapshot_id == "core-md-snap-001"
    assert stateful_result.lineage.model_portfolio_id == "model-balanced"
    assert stateful_result.lineage.model_portfolio_version == "2026-04-10"
    assert stateful_result.lineage.shelf_version == "shelf-sg-v1"
    assert stateful_result.lineage.integration_policy_version == "dpm-core-context.v1"
    assert stateful_result.lineage.source_lineage_bundle_id == "lineage-bundle-001"
    assert stateful_result.lineage.source_supportability_state == "READY"
    assert stateful_result.lineage.stateful_context_hash == "stateful-hash-001"


def test_rebalance_async_config_normalizes_modes_and_flags(monkeypatch) -> None:
    monkeypatch.delenv("DPM_ASYNC_EXECUTION_MODE", raising=False)
    monkeypatch.delenv("DPM_ASYNC_OPERATIONS_ENABLED", raising=False)
    monkeypatch.delenv("DPM_ASYNC_MANUAL_EXECUTION_ENABLED", raising=False)

    assert async_config.resolve_async_execution_mode() == "INLINE"
    assert async_config.async_operations_enabled() is True
    assert async_config.async_manual_execution_enabled() is True

    monkeypatch.setenv("DPM_ASYNC_EXECUTION_MODE", "accept_only")
    monkeypatch.setenv("DPM_ASYNC_OPERATIONS_ENABLED", "false")
    monkeypatch.setenv("DPM_ASYNC_MANUAL_EXECUTION_ENABLED", "0")

    assert async_config.resolve_async_execution_mode() == "ACCEPT_ONLY"
    assert async_config.async_operations_enabled() is False
    assert async_config.async_manual_execution_enabled() is False

    monkeypatch.setenv("DPM_ASYNC_EXECUTION_MODE", "external")
    assert async_config.resolve_async_execution_mode() == "INLINE"


def test_rebalance_async_config_exports_async_configuration_surface() -> None:
    assert async_config.__all__ == [
        "async_manual_execution_enabled",
        "async_operations_enabled",
        "env_flag",
        "resolve_async_execution_mode",
    ]


def test_rebalance_simulation_service_does_not_export_async_configuration_helpers() -> None:
    assert "async_manual_execution_enabled" not in service.__all__
    assert "async_operations_enabled" not in service.__all__
    assert "resolve_async_execution_mode" not in service.__all__


def test_rebalance_simulation_service_does_not_export_core_resolver_helpers() -> None:
    assert not hasattr(service, "build_core_resolver_client")
    assert not hasattr(service, "stateful_core_sourcing_enabled")


def test_rebalance_simulation_service_does_not_export_core_engine_runner() -> None:
    assert not hasattr(service, "run_simulation")
    assert "run_simulation" not in service.__all__


def test_rebalance_async_operation_payload_supports_current_and_legacy_shapes() -> None:
    batch_payload = valid_api_payload()
    batch_payload.pop("options")
    batch_payload["scenarios"] = {"baseline": {"options": {}}}

    legacy = async_payload.resolve_analyze_async_execution_payload(batch_payload)

    assert set(legacy.request.scenarios) == {"baseline"}
    assert legacy.source_context is None
    assert legacy.request_policy_pack_id is None
    assert legacy.tenant_default_policy_pack_id is None
    assert legacy.tenant_id is None

    current = async_payload.resolve_analyze_async_execution_payload(
        {
            "batch_request": batch_payload,
            "policy_context": {
                "request_policy_pack_id": "pack-request",
                "tenant_default_policy_pack_id": "pack-tenant",
                "tenant_id": "tenant-sg",
            },
            "source_context": None,
        }
    )

    assert set(current.request.scenarios) == {"baseline"}
    assert current.source_context is None
    assert current.request_policy_pack_id == "pack-request"
    assert current.tenant_default_policy_pack_id == "pack-tenant"
    assert current.tenant_id == "tenant-sg"


def test_rebalance_async_operation_payload_ignores_malformed_policy_context() -> None:
    batch_payload = valid_api_payload()
    batch_payload.pop("options")
    batch_payload["scenarios"] = {"baseline": {"options": {}}}

    current = async_payload.resolve_analyze_async_execution_payload(
        {
            "batch_request": batch_payload,
            "policy_context": "not-a-policy-context",
            "source_context": None,
        }
    )

    assert set(current.request.scenarios) == {"baseline"}
    assert current.source_context is None
    assert current.request_policy_pack_id is None
    assert current.tenant_default_policy_pack_id is None
    assert current.tenant_id is None


def test_rebalance_async_submission_payload_preserves_policy_context() -> None:
    batch_payload = valid_api_payload()
    batch_payload.pop("options")
    batch_payload["scenarios"] = {"baseline": {"options": {}}}
    request = BatchRebalanceRequest.model_validate(batch_payload)

    request_json = async_submission_payload.build_analyze_async_request_json(
        request=request,
        policy_pack_id="request-pack",
        tenant_default_policy_pack_id="tenant-pack",
        tenant_id="tenant-sg",
        source_context=None,
    )

    assert set(request_json) == {"batch_request", "policy_context", "source_context"}
    assert request_json["source_context"] is None
    assert request_json["policy_context"] == {
        "request_policy_pack_id": "request-pack",
        "tenant_default_policy_pack_id": "tenant-pack",
        "tenant_id": "tenant-sg",
    }
    assert request_json["batch_request"]["scenarios"] == {
        "baseline": {"description": None, "options": {}}
    }


def test_rebalance_async_submission_records_success_and_conflict() -> None:
    accepted = DpmAsyncAcceptedResponse(
        operation_id="op_submit_001",
        operation_type="ANALYZE_SCENARIOS",
        status="PENDING",
        correlation_id="corr-submit",
        created_at="2026-06-01T00:00:00+00:00",
        status_url="/api/v1/rebalance/operations/op_submit_001",
        execute_url="/api/v1/rebalance/operations/op_submit_001/execute",
    )

    class _SubmitService:
        captured: tuple[str | None, dict[str, object]] | None = None

        def submit_analyze_async(self, *, correlation_id: str | None, request_json: dict):
            self.captured = (correlation_id, request_json)
            return accepted

    submit_service = _SubmitService()
    request_json = {"batch_request": {}, "policy_context": {}, "source_context": None}

    assert (
        async_submission.submit_analyze_async_request(
            service=submit_service,
            correlation_id="corr-submit",
            request_json=request_json,
            source_context=None,
            execution_mode_label="inline",
        )
        is accepted
    )
    assert submit_service.captured == ("corr-submit", request_json)

    class _ConflictService:
        def submit_analyze_async(self, *, correlation_id: str | None, request_json: dict):
            raise DpmAsyncOperationConflictError("DPM_ASYNC_OPERATION_CORRELATION_CONFLICT")

    with pytest.raises(
        service.DpmRebalanceAsyncOperationConflictError,
        match="DPM_ASYNC_OPERATION_CORRELATION_CONFLICT",
    ):
        async_submission.submit_analyze_async_request(
            service=_ConflictService(),
            correlation_id="corr-submit",
            request_json=request_json,
            source_context=None,
            execution_mode_label="inline",
        )


def test_rebalance_async_manual_execution_maps_missing_and_not_executable() -> None:
    class _StatusService:
        def get_async_operation(self, *, operation_id: str):
            return SimpleNamespace(operation_id=operation_id, status="SUCCEEDED")

    calls: list[tuple[str, str]] = []

    def _runner(**kwargs):
        calls.append((kwargs["operation_id"], kwargs["execution_mode"]))

    status = async_manual_execution.execute_analyze_async_operation_now(
        operation_id="op_manual",
        service=_StatusService(),
        runner=_runner,
    )

    assert calls == [("op_manual", "manual")]
    assert status.operation_id == "op_manual"

    def _missing_runner(**_kwargs):
        raise DpmRunNotFoundError("DPM_ASYNC_OPERATION_NOT_FOUND")

    with pytest.raises(service.DpmRebalanceAsyncOperationNotFoundError):
        async_manual_execution.execute_analyze_async_operation_now(
            operation_id="op_missing",
            service=_StatusService(),
            runner=_missing_runner,
        )

    def _not_executable_runner(**_kwargs):
        raise DpmRunNotFoundError("DPM_ASYNC_OPERATION_NOT_EXECUTABLE")

    with pytest.raises(service.DpmRebalanceAsyncOperationNotExecutableError):
        async_manual_execution.execute_analyze_async_operation_now(
            operation_id="op_done",
            service=_StatusService(),
            runner=_not_executable_runner,
        )


def test_rebalance_async_operation_completion_records_success_and_failure() -> None:
    class _SupportService:
        success: tuple[str, dict] | None = None
        failure: tuple[str, str, str] | None = None

        def complete_operation_success(self, *, operation_id: str, result_json: dict) -> None:
            self.success = (operation_id, result_json)

        def complete_operation_failure(
            self,
            *,
            operation_id: str,
            code: str,
            message: str,
        ) -> None:
            self.failure = (operation_id, code, message)

    service_double = _SupportService()
    result = SimpleNamespace(model_dump=lambda mode: {"batch_run_id": "batch_001"})

    async_completion.complete_analyze_async_operation(
        service=service_double,
        operation_id="op_001",
        result=result,
        execution_mode="inline",
    )

    assert service_double.success == ("op_001", {"batch_run_id": "batch_001"})

    logged_messages: list[str] = []
    async_completion.fail_analyze_async_operation(
        service=service_double,
        operation_id="op_001",
        execution_mode="manual",
        exc=ValueError("bad payload"),
        current_logger=SimpleNamespace(exception=lambda message: logged_messages.append(message)),
    )

    assert service_double.failure == ("op_001", "ValueError", "bad payload")
    assert logged_messages == ["Asynchronous batch analysis failed"]


def test_rebalance_async_operation_runner_executes_current_payload_context() -> None:
    batch_payload = valid_api_payload()
    batch_payload.pop("options")
    batch_payload["scenarios"] = {"baseline": {"options": {}}}
    request_json = {
        "batch_request": batch_payload,
        "policy_context": {
            "request_policy_pack_id": "request-pack",
            "tenant_default_policy_pack_id": "tenant-pack",
            "tenant_id": "tenant-sg",
        },
        "source_context": None,
    }

    class _SupportService:
        completed: tuple[str, dict] | None = None

        def prepare_analyze_operation_execution(self, *, operation_id: str):
            return request_json, "corr-runner"

        def complete_operation_success(self, *, operation_id: str, result_json: dict):
            self.completed = (operation_id, result_json)

        def complete_operation_failure(self, **_kwargs):
            raise AssertionError("current async payload should execute successfully")

    captured: dict[str, object] = {}

    def _execute_batch(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(model_dump=lambda mode: {"batch_run_id": "batch-runner"})

    support_service = _SupportService()
    async_runner.run_analyze_async_operation_from_store(
        operation_id="op_runner",
        service=support_service,
        execution_mode="manual",
        execute_batch_fn=_execute_batch,
        current_logger=SimpleNamespace(exception=lambda *_args, **_kwargs: None),
    )

    assert captured["correlation_id"] == "corr-runner"
    assert captured["request_policy_pack_id"] == "request-pack"
    assert captured["tenant_default_policy_pack_id"] == "tenant-pack"
    assert captured["tenant_id"] == "tenant-sg"
    assert support_service.completed == ("op_runner", {"batch_run_id": "batch-runner"})


def test_rebalance_batch_execution_reports_invalid_options_without_running_engine() -> None:
    batch_payload = valid_api_payload()
    batch_payload.pop("options")
    batch_payload["scenarios"] = {"invalid_case": {"options": {"max_turnover_pct": "bad"}}}
    request = BatchRebalanceRequest.model_validate(batch_payload)

    def _unexpected_run(**_kwargs):
        raise AssertionError("invalid options should fail before engine execution")

    result = batch_execution.execute_batch_scenarios(
        request=request,
        batch_id="batch_test",
        correlation_id="corr_batch",
        policy_definition=None,
        source_context=None,
        run_simulation_fn=_unexpected_run,
        record_for_support=lambda **_kwargs: None,
        current_logger=SimpleNamespace(exception=lambda *_args, **_kwargs: None),
    )

    assert result.batch_run_id == "batch_test"
    assert result.results == {}
    assert result.comparison_metrics == {}
    assert set(result.failed_scenarios) == {"invalid_case"}
    assert result.failed_scenarios["invalid_case"].startswith("INVALID_OPTIONS:")
    assert result.warnings == ["PARTIAL_BATCH_FAILURE"]


def test_rebalance_batch_scenario_helper_reports_invalid_options() -> None:
    batch_payload = valid_api_payload()
    batch_payload.pop("options")
    batch_payload["scenarios"] = {"invalid_case": {"options": {"max_turnover_pct": "bad"}}}
    request = BatchRebalanceRequest.model_validate(batch_payload)

    outcome = batch_execution._execute_batch_scenario(  # noqa: SLF001
        request=request,
        scenario_name="invalid_case",
        batch_id="batch_test",
        correlation_id="corr_batch",
        policy_definition=None,
        source_context=None,
        run_simulation_fn=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("invalid options should fail before engine execution")
        ),
        record_for_support=lambda **_kwargs: None,
        current_logger=SimpleNamespace(exception=lambda *_args, **_kwargs: None),
    )

    assert outcome.result is None
    assert outcome.comparison_metric is None
    assert outcome.error is not None
    assert outcome.error.startswith("INVALID_OPTIONS:")


def test_rebalance_batch_scenario_helper_reports_execution_errors() -> None:
    batch_payload = valid_api_payload()
    batch_payload.pop("options")
    batch_payload["scenarios"] = {"baseline": {"options": {}}}
    request = BatchRebalanceRequest.model_validate(batch_payload)
    logged: list[str] = []

    outcome = batch_execution._execute_batch_scenario(  # noqa: SLF001
        request=request,
        scenario_name="baseline",
        batch_id="batch_test",
        correlation_id="corr_batch",
        policy_definition=None,
        source_context=None,
        run_simulation_fn=lambda **_kwargs: (_ for _ in ()).throw(
            RuntimeError("engine unavailable")
        ),
        record_for_support=lambda **_kwargs: None,
        current_logger=SimpleNamespace(exception=lambda message: logged.append(message)),
    )

    assert outcome.result is None
    assert outcome.comparison_metric is None
    assert outcome.error == "SCENARIO_EXECUTION_ERROR: RuntimeError"
    assert logged == ["Scenario execution failed"]


def test_rebalance_batch_scenario_outcome_recorder_routes_failures() -> None:
    results: dict[str, object] = {}
    metrics: dict[str, object] = {}
    failed: dict[str, str] = {}

    batch_execution._record_batch_scenario_outcome(  # noqa: SLF001
        scenario_name="baseline",
        outcome=batch_execution.BatchScenarioOutcome(
            error="SCENARIO_EXECUTION_ERROR: RuntimeError"
        ),
        results=results,
        comparison_metrics=metrics,
        failed_scenarios=failed,
    )

    assert results == {}
    assert metrics == {}
    assert failed == {"baseline": "SCENARIO_EXECUTION_ERROR: RuntimeError"}


def test_batch_scenario_execution_ids_are_deterministic() -> None:
    assert batch_scenario_execution.build_batch_scenario_execution_ids(
        batch_id="batch_test",
        scenario_name="baseline",
        correlation_id="corr_batch",
    ) == batch_scenario_execution.BatchScenarioExecutionIds(
        request_hash="batch_test:baseline",
        correlation_id="corr_batch:baseline",
    )
    assert batch_scenario_execution.build_batch_scenario_execution_ids(
        batch_id="batch_test",
        scenario_name="baseline",
        correlation_id=None,
    ) == batch_scenario_execution.BatchScenarioExecutionIds(
        request_hash="batch_test:baseline",
        correlation_id="batch_test:baseline",
    )


def test_batch_scenario_execution_runs_engine_and_records_supportability() -> None:
    batch_payload = valid_api_payload()
    batch_payload.pop("options")
    batch_payload["scenarios"] = {"baseline": {"options": {}}}
    request = BatchRebalanceRequest.model_validate(batch_payload)
    support_calls: list[dict] = []

    scenario_result, metric = batch_scenario_execution.execute_valid_batch_scenario(
        request=request,
        scenario_name="baseline",
        options=batch_scenario_execution.validate_batch_scenario_options(
            request.scenarios["baseline"]
        ),
        batch_id="batch_test",
        correlation_id="corr_batch",
        policy_definition=None,
        source_context=None,
        run_simulation_fn=run_simulation,
        record_for_support=lambda **kwargs: support_calls.append(kwargs),
    )

    assert scenario_result.correlation_id == "corr_batch:baseline"
    assert scenario_result.lineage.request_hash == "batch_test:baseline"
    assert scenario_result.lineage.input_mode == "stateless"
    assert metric.status == scenario_result.status
    assert metric.gross_turnover_notional_base.currency == request.portfolio_snapshot.base_currency
    assert support_calls[0]["request_hash"] == "batch_test:baseline"
    assert support_calls[0]["portfolio_id"] == request.portfolio_snapshot.portfolio_id
    assert support_calls[0]["idempotency_key"] is None


def test_rebalance_sync_execution_runs_engine_and_records_supportability() -> None:
    request = RebalanceRequest.model_validate(valid_api_payload())
    support_calls: list[dict] = []

    result = sync_execution.execute_simulation_request(
        request=request,
        idempotency_key="idem_sync",
        request_hash="sha256:sync",
        correlation_id="corr-sync",
        policy_pack_definition=None,
        replay_enabled=False,
        source_context=None,
        support_service_factory=lambda: (_ for _ in ()).throw(
            AssertionError("replay-disabled execution should not resolve support service first")
        ),
        run_simulation_fn=run_simulation,
        record_for_support=lambda **kwargs: support_calls.append(kwargs),
        current_logger=SimpleNamespace(warning=lambda *_args, **_kwargs: None),
    )

    assert result.correlation_id == "corr-sync"
    assert result.lineage.request_hash == "sha256:sync"
    assert result.lineage.input_mode == "stateless"
    assert support_calls[0]["request_hash"] == "sha256:sync"
    assert support_calls[0]["idempotency_key"] == "idem_sync"
    assert support_calls[0]["portfolio_id"] == request.portfolio_snapshot.portfolio_id


def test_rebalance_policy_pack_execution_loads_selected_catalog_only_when_needed() -> None:
    disabled_resolution = DpmEffectivePolicyPackResolution(
        enabled=False,
        selected_policy_pack_id=None,
        source="DISABLED",
    )

    assert (
        policy_pack_execution.resolve_selected_policy_pack_definition(
            policy_pack=disabled_resolution,
            catalog_loader=lambda: (_ for _ in ()).throw(AssertionError("catalog not needed")),
        )
        is None
    )

    selected_resolution = DpmEffectivePolicyPackResolution(
        enabled=True,
        selected_policy_pack_id="pack-001",
        source="REQUEST",
    )
    definition = DpmPolicyPackDefinition(policy_pack_id="pack-001", version="1")

    assert (
        policy_pack_execution.resolve_selected_policy_pack_definition(
            policy_pack=selected_resolution,
            catalog_loader=lambda: {"pack-001": definition},
        )
        is definition
    )


def test_rebalance_policy_pack_execution_context_preserves_deferred_async_catalog_lookup(
    monkeypatch,
) -> None:
    selected_resolution = DpmEffectivePolicyPackResolution(
        enabled=True,
        selected_policy_pack_id="pack-async",
        source="REQUEST",
    )
    monkeypatch.setattr(
        policy_pack_execution,
        "resolve_dpm_policy_pack",
        lambda **_kwargs: selected_resolution,
    )

    context = policy_pack_execution.resolve_execution_policy_pack_context(
        request_policy_pack_id="pack-async",
        tenant_default_policy_pack_id=None,
        tenant_id=None,
        surface="analyze_async",
        catalog_loader=lambda: (_ for _ in ()).throw(
            AssertionError("async submit should not force catalog resolution")
        ),
        load_definition=False,
    )

    assert context.resolution is selected_resolution
    assert context.definition is None

    definition = DpmPolicyPackDefinition(policy_pack_id="pack-async", version="1")
    loaded_context = policy_pack_execution.resolve_execution_policy_pack_context(
        request_policy_pack_id="pack-async",
        tenant_default_policy_pack_id=None,
        tenant_id=None,
        surface="analyze",
        catalog_loader=lambda: {"pack-async": definition},
    )

    assert loaded_context.definition is definition


def test_rebalance_idempotency_replay_handles_missing_conflict_and_inconsistent_store() -> None:
    class _MissingService:
        def get_idempotency_lookup(self, *, idempotency_key):
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")

    assert (
        idempotency_replay.resolve_idempotency_replay(
            idempotency_key="idem_missing",
            request_hash="sha256:request",
            source_context=None,
            support_service_factory=_MissingService,
        )
        is None
    )

    class _ConflictService:
        def get_idempotency_lookup(self, *, idempotency_key):
            return SimpleNamespace(
                idempotency_key=idempotency_key,
                request_hash="sha256:other",
                rebalance_run_id="rr_001",
            )

    with pytest.raises(
        service.DpmRebalanceIdempotencyConflictError,
        match="IDEMPOTENCY_KEY_CONFLICT",
    ):
        idempotency_replay.resolve_idempotency_replay(
            idempotency_key="idem_conflict",
            request_hash="sha256:request",
            source_context=None,
            support_service_factory=_ConflictService,
        )

    class _InconsistentService:
        def get_idempotency_lookup(self, *, idempotency_key):
            return SimpleNamespace(
                idempotency_key=idempotency_key,
                request_hash="sha256:request",
                rebalance_run_id="rr_missing",
            )

        def get_run(self, *, rebalance_run_id):
            raise DpmRunNotFoundError("DPM_RUN_NOT_FOUND")

    with pytest.raises(service.DpmRebalanceIdempotencyStoreInconsistentError):
        idempotency_replay.resolve_idempotency_replay(
            idempotency_key="idem_inconsistent",
            request_hash="sha256:request",
            source_context=None,
            support_service_factory=_InconsistentService,
        )


def test_rebalance_supportability_write_preserves_replay_failure_gate() -> None:
    def _raise_runtime(**_kwargs):
        raise RuntimeError("store down")

    with pytest.raises(
        service.DpmRebalanceIdempotencyStoreWriteFailedError,
        match="DPM_IDEMPOTENCY_STORE_WRITE_FAILED",
    ):
        supportability_write.record_simulation_supportability(
            result=SimpleNamespace(),
            request_hash="sha256:request",
            portfolio_id="PF_TEST",
            idempotency_key="idem_001",
            replay_enabled=True,
            source_context=None,
            record_for_support=_raise_runtime,
            current_logger=SimpleNamespace(exception=lambda *_args, **_kwargs: None),
        )

    logged_messages: list[str] = []
    supportability_write.record_simulation_supportability(
        result=SimpleNamespace(),
        request_hash="sha256:request",
        portfolio_id="PF_TEST",
        idempotency_key="idem_001",
        replay_enabled=False,
        source_context=None,
        record_for_support=_raise_runtime,
        current_logger=SimpleNamespace(exception=lambda message: logged_messages.append(message)),
    )

    assert logged_messages == ["Supportability persistence failed"]


def test_async_operation_disabled_is_reported_before_manual_gate(monkeypatch) -> None:
    monkeypatch.setenv("DPM_ASYNC_OPERATIONS_ENABLED", "false")

    with pytest.raises(service.DpmRebalanceAsyncOperationsDisabledError) as exc_info:
        service.execute_dpm_async_operation(operation_id="op_1", service=object())

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
