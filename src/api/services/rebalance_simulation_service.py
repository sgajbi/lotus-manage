import logging
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import ValidationError

from src.api.observability import (
    DPM_CORE_RESOLVER_OPERATION,
    record_async_operation,
    record_core_resolver_call,
    record_execution_call,
    record_policy_pack_resolution,
)
from src.api.request_models import (
    BatchExecutionRequestEnvelope,
    RebalanceExecutionRequestEnvelope,
    RebalanceRequest,
)
from src.api.services import core_resolver_service
from src.api.services.rebalance_simulation_errors import (
    DpmRebalanceAsyncManualExecutionDisabledError,
    DpmRebalanceAsyncOperationConflictError,
    DpmRebalanceAsyncOperationError,
    DpmRebalanceAsyncOperationNotExecutableError,
    DpmRebalanceAsyncOperationNotFoundError,
    DpmRebalanceAsyncOperationSupportUnavailableError,
    DpmRebalanceAsyncOperationsDisabledError,
    DpmRebalanceCoreContextIncompleteError,
    DpmRebalanceCoreResolverUnavailableError,
    DpmRebalanceEnvelopeError,
    DpmRebalanceEnvelopeValidationError,
    DpmRebalanceIdempotencyConflictError,
    DpmRebalanceIdempotencyStoreInconsistentError,
    DpmRebalanceIdempotencyStoreWriteFailedError,
    DpmRebalancePolicyPackCatalogUnavailableError,
    DpmRebalanceSimulationError,
    DpmRebalanceSupportabilityStoreUnavailableError,
    DpmRebalanceStatefulInputDisabledError,
)
from src.api.services.rebalance_policy_pack_service import (
    DpmPolicyPackCatalogUnavailableError,
    load_dpm_policy_pack_catalog,
    resolve_dpm_policy_pack,
)
from src.api.services.rebalance_async_config import (
    async_manual_execution_enabled,
    async_operations_enabled,
    env_flag,
    resolve_async_execution_mode,
)
from src.api.services.rebalance_run_support_service import (
    DpmRunSupportServiceUnavailableError,
    get_dpm_run_support_service,
    record_dpm_run_for_support,
)
from src.api.services.rebalance_source_lineage import apply_source_lineage, source_input_mode
from src.api.services.rebalance_batch_analysis import (
    build_comparison_metric,
    resolve_base_snapshot_ids,
    to_invalid_options_error,
)
from src.core.common.canonical import hash_canonical_payload
from src.core.dpm_source_context import (
    DpmCoreContextIncompleteError,
    DpmResolvedSourceContext,
    build_batch_rebalance_request_from_core_context,
    build_rebalance_request_from_core_context,
)
from src.core.rebalance.engine import run_simulation
from src.core.rebalance.policy_packs import (
    DpmEffectivePolicyPackResolution,
    DpmPolicyPackDefinition,
    apply_policy_pack_to_engine_options,
    resolve_policy_pack_definition,
    resolve_policy_pack_replay_enabled,
)
from src.core.rebalance_runs import (
    DpmAsyncAcceptedResponse,
    DpmAsyncOperationConflictError,
    DpmAsyncOperationStatusResponse,
    DpmRunLookupResponse,
    DpmRunNotFoundError,
    DpmRunSupportService,
)
from src.core.models import (
    BatchRebalanceRequest,
    BatchRebalanceResult,
    EngineOptions,
    RebalanceResult,
)
from src.infrastructure.core_sourcing import (
    DpmCoreResolverError,
    DpmCoreResolverUnavailableError,
)

logger = logging.getLogger(__name__)

DPM_IDEMPOTENCY_CACHE: "OrderedDict[str, Dict[str, object]]" = OrderedDict()
DEFAULT_DPM_IDEMPOTENCY_CACHE_SIZE = 1000
build_core_resolver_client = core_resolver_service.build_core_resolver_client
env_float = core_resolver_service.env_float
env_int = core_resolver_service.env_int
stateful_core_sourcing_enabled = core_resolver_service.stateful_core_sourcing_enabled
_source_input_mode = source_input_mode
_apply_source_lineage = apply_source_lineage


def _main_override(name: str) -> Any | None:
    try:
        from src.api import main as main_module
    except ImportError:
        return None
    return getattr(main_module, name, None)


def _resolved_logger() -> logging.Logger | Any:
    return _main_override("logger") or logger


def resolve_selected_policy_pack_definition(
    policy_pack: DpmEffectivePolicyPackResolution,
) -> Optional[DpmPolicyPackDefinition]:
    if policy_pack.selected_policy_pack_id is None:
        return None
    try:
        catalog = load_dpm_policy_pack_catalog()
    except DpmPolicyPackCatalogUnavailableError as exc:
        raise DpmRebalancePolicyPackCatalogUnavailableError(exc.detail) from exc
    return resolve_policy_pack_definition(resolution=policy_pack, catalog=catalog)


def _record_policy_resolution(
    *,
    surface: str,
    policy_pack: DpmEffectivePolicyPackResolution,
) -> None:
    record_policy_pack_resolution(
        surface=surface,
        enabled=str(policy_pack.enabled).lower(),
        source=policy_pack.source.lower(),
        selected=str(policy_pack.selected_policy_pack_id is not None).lower(),
    )


def _execution_outcome_for_status(status_value: str) -> str:
    return "blocked" if status_value == "BLOCKED" else "success"


def _execution_status_label(status_value: str) -> str:
    return status_value.lower()


def _resolve_stateful_source_context(
    *,
    envelope: RebalanceExecutionRequestEnvelope | BatchExecutionRequestEnvelope,
    correlation_id: Optional[str],
) -> DpmResolvedSourceContext:
    if envelope.stateful_input is None:
        raise DpmRebalanceEnvelopeValidationError("DPM_STATEFUL_INPUT_REQUIRED")
    if not stateful_core_sourcing_enabled():
        raise DpmRebalanceStatefulInputDisabledError("DPM_STATEFUL_INPUT_DISABLED")

    resolver_factory = _main_override("build_core_resolver_client") or build_core_resolver_client
    try:
        resolver = resolver_factory()
        context = resolver.resolve_execution_context(
            stateful_input=envelope.stateful_input,
            correlation_id=correlation_id,
        )
    except DpmCoreResolverUnavailableError as exc:
        record_core_resolver_call(
            operation=DPM_CORE_RESOLVER_OPERATION,
            outcome="unavailable",
            supportability_state="unavailable",
            reason="resolver_unavailable",
        )
        raise DpmRebalanceCoreResolverUnavailableError("DPM_CORE_RESOLVER_UNAVAILABLE") from exc
    except ValidationError as exc:
        record_core_resolver_call(
            operation=DPM_CORE_RESOLVER_OPERATION,
            outcome="incomplete",
            supportability_state="unknown",
            reason="invalid_response",
        )
        raise DpmRebalanceCoreContextIncompleteError("DPM_CORE_CONTEXT_INCOMPLETE") from exc
    except (DpmCoreContextIncompleteError, DpmCoreResolverError) as exc:
        record_core_resolver_call(
            operation=DPM_CORE_RESOLVER_OPERATION,
            outcome="incomplete",
            supportability_state="unknown",
            reason="context_incomplete",
        )
        raise DpmRebalanceCoreContextIncompleteError("DPM_CORE_CONTEXT_INCOMPLETE") from exc
    record_core_resolver_call(
        operation=DPM_CORE_RESOLVER_OPERATION,
        outcome="success",
        supportability_state=context.supportability.state.lower(),
        reason="degraded" if context.supportability.state == "DEGRADED" else "ready",
    )

    stateful_context_hash = hash_canonical_payload(context.model_dump(mode="json"))
    return DpmResolvedSourceContext(
        stateful_context_hash=stateful_context_hash,
        context=context,
    )


def resolve_rebalance_request_envelope(
    *,
    envelope: RebalanceExecutionRequestEnvelope,
    correlation_id: Optional[str],
) -> tuple[RebalanceRequest, Optional[DpmResolvedSourceContext]]:
    if envelope.input_mode == "stateless":
        if envelope.stateless_input is None:
            raise DpmRebalanceEnvelopeValidationError("DPM_STATELESS_INPUT_REQUIRED")
        return envelope.stateless_input, None

    source_context = _resolve_stateful_source_context(
        envelope=envelope,
        correlation_id=correlation_id,
    )
    try:
        resolved = build_rebalance_request_from_core_context(
            context=source_context.context,
            options_override=envelope.options_override,
        )
    except (DpmCoreContextIncompleteError, ValidationError) as exc:
        raise DpmRebalanceCoreContextIncompleteError("DPM_CORE_CONTEXT_INCOMPLETE") from exc
    return RebalanceRequest.model_validate(resolved.model_dump(mode="python")), source_context


def resolve_batch_request_envelope(
    *,
    envelope: BatchExecutionRequestEnvelope,
    correlation_id: Optional[str],
) -> tuple[BatchRebalanceRequest, Optional[DpmResolvedSourceContext]]:
    if envelope.input_mode == "stateless":
        if envelope.stateless_input is None:
            raise DpmRebalanceEnvelopeValidationError("DPM_STATELESS_INPUT_REQUIRED")
        return envelope.stateless_input, None

    source_context = _resolve_stateful_source_context(
        envelope=envelope,
        correlation_id=correlation_id,
    )
    try:
        request = build_batch_rebalance_request_from_core_context(
            context=source_context.context,
            scenarios=envelope.scenarios,
        )
    except (DpmCoreContextIncompleteError, ValidationError) as exc:
        raise DpmRebalanceCoreContextIncompleteError("DPM_CORE_CONTEXT_INCOMPLETE") from exc
    return request, source_context


def simulate_rebalance(
    *,
    request: RebalanceRequest,
    idempotency_key: str,
    correlation_id: Optional[str],
    policy_pack_id: Optional[str],
    tenant_default_policy_pack_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    source_context: Optional[DpmResolvedSourceContext] = None,
) -> RebalanceResult:
    current_logger = _resolved_logger()
    resolved_correlation_id = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
    current_logger.info("Simulating rebalance request")
    default_replay_enabled = env_flag("DPM_IDEMPOTENCY_REPLAY_ENABLED", True)
    request_payload = request.model_dump(mode="json")
    request_hash = hash_canonical_payload(request_payload)
    policy_pack = resolve_dpm_policy_pack(
        request_policy_pack_id=policy_pack_id,
        tenant_default_policy_pack_id=tenant_default_policy_pack_id,
        tenant_id=tenant_id,
    )
    _record_policy_resolution(surface="simulate", policy_pack=policy_pack)
    policy_pack_definition = resolve_selected_policy_pack_definition(policy_pack)
    effective_options = apply_policy_pack_to_engine_options(
        options=request.options,
        policy_pack=policy_pack_definition,
    )
    replay_enabled = resolve_policy_pack_replay_enabled(
        default_replay_enabled=default_replay_enabled,
        policy_pack=policy_pack_definition,
    )
    current_logger.debug(
        "Resolved lotus-manage policy pack for simulate. enabled=%s source=%s policy_pack_id=%s",
        policy_pack.enabled,
        policy_pack.source,
        policy_pack.selected_policy_pack_id,
    )

    if replay_enabled:
        try:
            support_service = get_dpm_run_support_service()
        except DpmRunSupportServiceUnavailableError as exc:
            raise DpmRebalanceSupportabilityStoreUnavailableError(exc.detail) from exc
        existing = None
        try:
            existing = support_service.get_idempotency_lookup(idempotency_key=idempotency_key)
        except DpmRunNotFoundError:
            existing = None
        if existing is not None and existing.request_hash != request_hash:
            record_execution_call(
                operation="simulate",
                input_mode=source_input_mode(source_context),
                outcome="conflict",
                result_status="failed",
            )
            raise DpmRebalanceIdempotencyConflictError(
                "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"
            )
        if existing is not None:
            try:
                replay_run: DpmRunLookupResponse = support_service.get_run(
                    rebalance_run_id=existing.rebalance_run_id
                )
            except DpmRunNotFoundError as exc:
                record_execution_call(
                    operation="simulate",
                    input_mode=source_input_mode(source_context),
                    outcome="error",
                    result_status="failed",
                )
                raise DpmRebalanceIdempotencyStoreInconsistentError(
                    "DPM_IDEMPOTENCY_STORE_INCONSISTENT"
                ) from exc
            replay_result = RebalanceResult.model_validate(replay_run.result)
            record_execution_call(
                operation="simulate",
                input_mode=source_input_mode(source_context),
                outcome="replayed",
                result_status=_execution_status_label(replay_result.status),
            )
            return replay_result

    run_fn = _main_override("run_simulation") or run_simulation
    result = run_fn(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        model=request.model_portfolio,
        shelf=request.shelf_entries,
        options=effective_options,
        request_hash=request_hash,
        correlation_id=resolved_correlation_id,
    )
    result = apply_source_lineage(result=result, source_context=source_context)

    try:
        record_for_support = (
            _main_override("record_dpm_run_for_support") or record_dpm_run_for_support
        )
        record_for_support(
            result=result,
            request_hash=request_hash,
            portfolio_id=request.portfolio_snapshot.portfolio_id,
            idempotency_key=idempotency_key,
        )
    except (RuntimeError, ValueError) as exc:
        if replay_enabled:
            record_execution_call(
                operation="simulate",
                input_mode=source_input_mode(source_context),
                outcome="error",
                result_status="failed",
            )
            raise DpmRebalanceIdempotencyStoreWriteFailedError(
                "DPM_IDEMPOTENCY_STORE_WRITE_FAILED"
            ) from exc
        current_logger.exception("Supportability persistence failed")

    if result.status == "BLOCKED":
        current_logger.warning("Run blocked by DPM engine safety rules")

    record_execution_call(
        operation="simulate",
        input_mode=source_input_mode(source_context),
        outcome=_execution_outcome_for_status(result.status),
        result_status=_execution_status_label(result.status),
    )
    return result


def execute_batch_analysis(
    *,
    request: BatchRebalanceRequest,
    correlation_id: Optional[str],
    request_policy_pack_id: Optional[str] = None,
    tenant_default_policy_pack_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    source_context: Optional[DpmResolvedSourceContext] = None,
) -> BatchRebalanceResult:
    current_logger = _resolved_logger()
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    current_logger.info("Analyzing scenario batch")

    results = {}
    comparison_metrics = {}
    failed_scenarios = {}
    warnings = []
    policy_resolution = resolve_dpm_policy_pack(
        request_policy_pack_id=request_policy_pack_id,
        tenant_default_policy_pack_id=tenant_default_policy_pack_id,
        tenant_id=tenant_id,
    )
    _record_policy_resolution(surface="analyze", policy_pack=policy_resolution)
    policy_definition = resolve_selected_policy_pack_definition(policy_resolution)

    for scenario_name in sorted(request.scenarios.keys()):
        scenario = request.scenarios[scenario_name]
        try:
            options = EngineOptions.model_validate(scenario.options)
        except ValidationError as exc:
            failed_scenarios[scenario_name] = to_invalid_options_error(exc)
            continue

        try:
            effective_options = apply_policy_pack_to_engine_options(
                options=options,
                policy_pack=policy_definition,
            )
            scenario_correlation_id = (
                f"{correlation_id}:{scenario_name}"
                if correlation_id
                else f"{batch_id}:{scenario_name}"
            )
            request_hash = f"{batch_id}:{scenario_name}"
            run_fn = _main_override("run_simulation") or run_simulation
            scenario_result = run_fn(
                portfolio=request.portfolio_snapshot,
                market_data=request.market_data_snapshot,
                model=request.model_portfolio,
                shelf=request.shelf_entries,
                options=effective_options,
                request_hash=request_hash,
                correlation_id=scenario_correlation_id,
            )
            scenario_result = apply_source_lineage(
                result=scenario_result,
                source_context=source_context,
            )
            record_for_support = (
                _main_override("record_dpm_run_for_support") or record_dpm_run_for_support
            )
            record_for_support(
                result=scenario_result,
                request_hash=request_hash,
                portfolio_id=request.portfolio_snapshot.portfolio_id,
                idempotency_key=None,
            )
            results[scenario_name] = scenario_result
            comparison_metrics[scenario_name] = build_comparison_metric(
                scenario_result=scenario_result,
                base_currency=request.portfolio_snapshot.base_currency,
            )
        except (ValidationError, RuntimeError, ValueError) as exc:
            current_logger.exception("Scenario execution failed")
            failed_scenarios[scenario_name] = f"SCENARIO_EXECUTION_ERROR: {type(exc).__name__}"

    if failed_scenarios:
        warnings.append("PARTIAL_BATCH_FAILURE")
    record_execution_call(
        operation="analyze",
        input_mode=source_input_mode(source_context),
        outcome="partial_failure" if failed_scenarios else "success",
        result_status="partial_success" if failed_scenarios else "ready",
    )

    return BatchRebalanceResult(
        batch_run_id=batch_id,
        run_at_utc=datetime.now(timezone.utc).isoformat(),
        base_snapshot_ids=resolve_base_snapshot_ids(request),
        results=results,
        comparison_metrics=comparison_metrics,
        failed_scenarios=failed_scenarios,
        warnings=warnings,
    )


def run_analyze_async_operation(
    *,
    operation_id: str,
    service: DpmRunSupportService,
    execution_mode: str = "inline",
) -> None:
    current_logger = _resolved_logger()
    request_json, operation_correlation_id = service.prepare_analyze_operation_execution(
        operation_id=operation_id
    )
    try:
        if isinstance(request_json, dict) and "batch_request" in request_json:
            batch_payload = request_json.get("batch_request") or {}
            policy_context = request_json.get("policy_context") or {}
            source_context_payload = request_json.get("source_context")
            request_policy_pack_id = policy_context.get("request_policy_pack_id")
            tenant_default_policy_pack_id = policy_context.get("tenant_default_policy_pack_id")
            tenant_id = policy_context.get("tenant_id")
        else:
            batch_payload = request_json
            source_context_payload = None
            request_policy_pack_id = None
            tenant_default_policy_pack_id = None
            tenant_id = None
        batch_request = BatchRebalanceRequest.model_validate(batch_payload)
        source_context = (
            DpmResolvedSourceContext.model_validate(source_context_payload)
            if source_context_payload
            else None
        )
        execute_batch_fn = _main_override("_execute_batch_analysis") or execute_batch_analysis
        result = execute_batch_fn(
            request=batch_request,
            correlation_id=operation_correlation_id,
            request_policy_pack_id=request_policy_pack_id,
            tenant_default_policy_pack_id=tenant_default_policy_pack_id,
            tenant_id=tenant_id,
            source_context=source_context,
        )
        service.complete_operation_success(
            operation_id=operation_id,
            result_json=result.model_dump(mode="json"),
        )
        record_async_operation(
            event="execute",
            execution_mode=execution_mode,
            outcome="succeeded",
        )
    except (DpmRunNotFoundError, ValidationError, RuntimeError, ValueError) as exc:
        current_logger.exception("Asynchronous batch analysis failed")
        service.complete_operation_failure(
            operation_id=operation_id,
            code=type(exc).__name__,
            message=str(exc),
        )
        record_async_operation(
            event="execute",
            execution_mode=execution_mode,
            outcome="failed",
        )


def submit_and_optionally_execute_async_analysis(
    *,
    request: BatchRebalanceRequest,
    correlation_id: Optional[str],
    policy_pack_id: Optional[str],
    tenant_default_policy_pack_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    source_context: Optional[DpmResolvedSourceContext] = None,
) -> DpmAsyncAcceptedResponse:
    current_logger = _resolved_logger()
    if not async_operations_enabled():
        raise DpmRebalanceAsyncOperationsDisabledError("DPM_ASYNC_OPERATIONS_DISABLED")
    try:
        service = get_dpm_run_support_service()
    except DpmRunSupportServiceUnavailableError as exc:
        raise DpmRebalanceAsyncOperationSupportUnavailableError(exc.detail) from exc
    policy_pack = resolve_dpm_policy_pack(
        request_policy_pack_id=policy_pack_id,
        tenant_default_policy_pack_id=tenant_default_policy_pack_id,
        tenant_id=tenant_id,
    )
    _record_policy_resolution(surface="analyze_async", policy_pack=policy_pack)
    current_logger.debug(
        "Resolved lotus-manage policy pack for analyze async. enabled=%s source=%s policy_pack_id=%s",
        policy_pack.enabled,
        policy_pack.source,
        policy_pack.selected_policy_pack_id,
    )
    try:
        accepted = service.submit_analyze_async(
            correlation_id=correlation_id,
            request_json={
                "batch_request": request.model_dump(mode="json"),
                "policy_context": {
                    "request_policy_pack_id": policy_pack_id,
                    "tenant_default_policy_pack_id": tenant_default_policy_pack_id,
                    "tenant_id": tenant_id,
                },
                "source_context": (
                    source_context.model_dump(mode="json") if source_context is not None else None
                ),
            },
        )
    except DpmAsyncOperationConflictError as exc:
        record_async_operation(
            event="submit",
            execution_mode=resolve_async_execution_mode().lower(),
            outcome="conflict",
        )
        record_execution_call(
            operation="analyze_async",
            input_mode=source_input_mode(source_context),
            outcome="conflict",
            result_status="failed",
        )
        raise DpmRebalanceAsyncOperationConflictError(str(exc)) from exc
    record_async_operation(
        event="submit",
        execution_mode=resolve_async_execution_mode().lower(),
        outcome="accepted",
    )
    record_execution_call(
        operation="analyze_async",
        input_mode=source_input_mode(source_context),
        outcome="accepted",
        result_status="accepted",
    )
    if resolve_async_execution_mode() == "ACCEPT_ONLY":
        return accepted
    run_analyze_async_operation(
        operation_id=accepted.operation_id,
        service=service,
        execution_mode="inline",
    )
    return accepted


def execute_dpm_async_operation(
    *, operation_id: str, service: DpmRunSupportService
) -> DpmAsyncOperationStatusResponse:
    if not async_operations_enabled():
        raise DpmRebalanceAsyncOperationsDisabledError("DPM_ASYNC_OPERATIONS_DISABLED")
    if not async_manual_execution_enabled():
        raise DpmRebalanceAsyncManualExecutionDisabledError("DPM_ASYNC_MANUAL_EXECUTION_DISABLED")
    try:
        run_analyze_async_operation(
            operation_id=operation_id,
            service=service,
            execution_mode="manual",
        )
    except DpmRunNotFoundError as exc:
        detail = str(exc)
        if detail == "DPM_ASYNC_OPERATION_NOT_EXECUTABLE":
            record_async_operation(
                event="execute",
                execution_mode="manual",
                outcome="not_executable",
            )
            raise DpmRebalanceAsyncOperationNotExecutableError(detail) from exc
        record_async_operation(
            event="execute",
            execution_mode="manual",
            outcome="not_found",
        )
        raise DpmRebalanceAsyncOperationNotFoundError(detail) from exc
    return service.get_async_operation(operation_id=operation_id)


__all__ = [
    "DEFAULT_DPM_IDEMPOTENCY_CACHE_SIZE",
    "DPM_IDEMPOTENCY_CACHE",
    "DpmRebalanceAsyncManualExecutionDisabledError",
    "DpmRebalanceAsyncOperationConflictError",
    "DpmRebalanceAsyncOperationError",
    "DpmRebalanceAsyncOperationNotExecutableError",
    "DpmRebalanceAsyncOperationNotFoundError",
    "DpmRebalanceAsyncOperationSupportUnavailableError",
    "DpmRebalanceAsyncOperationsDisabledError",
    "DpmRebalanceCoreContextIncompleteError",
    "DpmRebalanceCoreResolverUnavailableError",
    "DpmRebalanceEnvelopeError",
    "DpmRebalanceEnvelopeValidationError",
    "DpmRebalanceIdempotencyConflictError",
    "DpmRebalanceIdempotencyStoreInconsistentError",
    "DpmRebalanceIdempotencyStoreWriteFailedError",
    "DpmRebalancePolicyPackCatalogUnavailableError",
    "DpmRebalanceSimulationError",
    "DpmRebalanceStatefulInputDisabledError",
    "DpmRebalanceSupportabilityStoreUnavailableError",
    "async_manual_execution_enabled",
    "async_operations_enabled",
    "env_flag",
    "env_int",
    "execute_batch_analysis",
    "execute_dpm_async_operation",
    "resolve_async_execution_mode",
    "run_analyze_async_operation",
    "run_simulation",
    "simulate_rebalance",
]
