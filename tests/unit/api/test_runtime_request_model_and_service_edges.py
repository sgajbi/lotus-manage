from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import src.api.services.core_resolver_service as core_resolver_service
import src.api.services.rebalance_async_config as async_config
import src.api.services.rebalance_idempotency_replay as idempotency_replay
import src.api.services.rebalance_source_lineage as source_lineage_service
import src.api.services.rebalance_simulation_service as service
import src.api.services.rebalance_supportability_write as supportability_write
from src.api.services.rebalance_batch_analysis import resolve_base_snapshot_ids
import src.api.services.rebalance_run_support_service as run_support_service
from src.api.request_models import BatchExecutionRequestEnvelope, RebalanceExecutionRequestEnvelope
from src.api.routers.rebalance_simulation_http import rebalance_envelope_http_exception
from src.api.routers.runtime_utils import (
    assert_feature_enabled,
    normalize_backend_init_error,
    postgres_connection_exception_types,
)
from src.core.dpm_source_context import DpmCoreContextIncompleteError, DpmStatefulInput
from src.core.models import BatchRebalanceRequest
from src.core.rebalance_runs import DpmRunNotFoundError
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

    monkeypatch.setattr(service, "build_core_resolver_client", lambda: _UnavailableResolver())
    with pytest.raises(service.DpmRebalanceCoreResolverUnavailableError) as unavailable:
        service._resolve_stateful_source_context(envelope=envelope, correlation_id="corr")
    assert rebalance_envelope_http_exception(unavailable.value).status_code == 503

    class _IncompleteResolver:
        def resolve_execution_context(self, **_kwargs):
            raise DpmCoreResolverError("bad")

    monkeypatch.setattr(service, "build_core_resolver_client", lambda: _IncompleteResolver())
    with pytest.raises(service.DpmRebalanceCoreContextIncompleteError) as incomplete:
        service._resolve_stateful_source_context(envelope=envelope, correlation_id="corr")
    assert incomplete.value.detail == "DPM_CORE_CONTEXT_INCOMPLETE"
    assert rebalance_envelope_http_exception(incomplete.value).status_code == 424

    class _DerivedIncompleteResolver:
        def resolve_execution_context(self, **_kwargs):
            raise DpmCoreContextIncompleteError("MARKET_DATA_STALE")

    monkeypatch.setattr(service, "build_core_resolver_client", lambda: _DerivedIncompleteResolver())
    with pytest.raises(service.DpmRebalanceCoreContextIncompleteError) as derived_incomplete:
        service._resolve_stateful_source_context(envelope=envelope, correlation_id="corr")
    assert derived_incomplete.value.detail == "DPM_CORE_CONTEXT_INCOMPLETE"
    assert rebalance_envelope_http_exception(derived_incomplete.value).status_code == 424

    class _InvalidResolver:
        def resolve_execution_context(self, **_kwargs):
            DpmStatefulInput.model_validate({})

    monkeypatch.setattr(service, "build_core_resolver_client", lambda: _InvalidResolver())
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
