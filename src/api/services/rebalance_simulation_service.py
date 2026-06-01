import logging
from typing import Any, Optional

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
from src.api.services.rebalance_policy_pack_service import load_dpm_policy_pack_catalog
from src.api.services.rebalance_request_envelope_resolution import (
    resolve_batch_request_envelope as resolve_batch_request_envelope_from_source,
    resolve_rebalance_request_envelope as resolve_rebalance_request_envelope_from_source,
)
from src.api.services import rebalance_async_config
from src.api.services.rebalance_async_operation_runner import (
    run_analyze_async_operation_from_store,
)
from src.api.services.rebalance_async_submission import submit_analyze_async_request
from src.api.services.rebalance_async_submission_context import (
    DpmAsyncSubmissionContext as DpmAsyncSubmissionContext,
    build_async_submission_context,
)
from src.api.services.rebalance_async_manual_execution import (
    execute_analyze_async_operation_now,
)
from src.api.services.rebalance_batch_execution_context import (
    DpmBatchExecutionContext as DpmBatchExecutionContext,
    build_batch_execution_context,
)
from src.api.services.rebalance_batch_execution import execute_batch_scenarios
from src.api.services.rebalance_sync_execution import execute_simulation_request
from src.api.services.rebalance_run_support_service import (
    get_dpm_run_support_service,
    record_dpm_run_for_support,
)
from src.api.services.rebalance_runtime_overrides import (
    resolve_callable_override,
    resolve_logger,
)
from src.api.services.rebalance_stateful_source_context import (
    resolve_stateful_source_context,
)
from src.core.common.canonical import hash_canonical_payload
from src.core.dpm_source_context import (
    DpmResolvedSourceContext,
    build_batch_rebalance_request_from_core_context,
    build_rebalance_request_from_core_context,
)
from src.core.rebalance.engine import run_simulation
from src.api.services.rebalance_simulation_execution_context import (
    DpmSimulationExecutionContext as DpmSimulationExecutionContext,
    build_simulation_execution_context,
)
from src.core.rebalance_runs import (
    DpmAsyncAcceptedResponse,
    DpmAsyncOperationStatusResponse,
    DpmRunSupportService,
)
from src.core.models import (
    BatchRebalanceRequest,
    BatchRebalanceResult,
    RebalanceResult,
)

logger = logging.getLogger(__name__)


def _resolved_logger() -> logging.Logger | Any:
    return resolve_logger(logger)


def _resolve_stateful_source_context(
    *,
    envelope: RebalanceExecutionRequestEnvelope | BatchExecutionRequestEnvelope,
    correlation_id: Optional[str],
) -> DpmResolvedSourceContext:
    resolver_factory = resolve_callable_override(
        "build_core_resolver_client",
        core_resolver_service.build_core_resolver_client,
    )
    return resolve_stateful_source_context(
        envelope=envelope,
        correlation_id=correlation_id,
        stateful_enabled=core_resolver_service.stateful_core_sourcing_enabled(),
        resolver_factory=resolver_factory,
    )


def resolve_rebalance_request_envelope(
    *,
    envelope: RebalanceExecutionRequestEnvelope,
    correlation_id: Optional[str],
) -> tuple[RebalanceRequest, Optional[DpmResolvedSourceContext]]:
    return resolve_rebalance_request_envelope_from_source(
        envelope=envelope,
        correlation_id=correlation_id,
        stateful_context_resolver=_resolve_stateful_source_context,
        rebalance_request_builder=build_rebalance_request_from_core_context,
    )


def resolve_batch_request_envelope(
    *,
    envelope: BatchExecutionRequestEnvelope,
    correlation_id: Optional[str],
) -> tuple[BatchRebalanceRequest, Optional[DpmResolvedSourceContext]]:
    return resolve_batch_request_envelope_from_source(
        envelope=envelope,
        correlation_id=correlation_id,
        stateful_context_resolver=_resolve_stateful_source_context,
        batch_request_builder=build_batch_rebalance_request_from_core_context,
    )


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
    current_logger.info("Simulating rebalance request")
    execution_context = build_simulation_execution_context(
        request=request,
        correlation_id=correlation_id,
        policy_pack_id=policy_pack_id,
        tenant_default_policy_pack_id=tenant_default_policy_pack_id,
        tenant_id=tenant_id,
        request_hasher=hash_canonical_payload,
        catalog_loader=load_dpm_policy_pack_catalog,
    )
    current_logger.debug(
        "Resolved lotus-manage policy pack for simulate. enabled=%s source=%s policy_pack_id=%s",
        execution_context.policy_resolution_enabled,
        execution_context.policy_resolution_source,
        execution_context.selected_policy_pack_id,
    )

    return execute_simulation_request(
        request=request,
        idempotency_key=idempotency_key,
        request_hash=execution_context.request_hash,
        correlation_id=execution_context.correlation_id,
        policy_pack_definition=execution_context.policy_pack_definition,
        replay_enabled=execution_context.replay_enabled,
        source_context=source_context,
        support_service_factory=get_dpm_run_support_service,
        run_simulation_fn=resolve_callable_override("run_simulation", run_simulation),
        record_for_support=resolve_callable_override(
            "record_dpm_run_for_support",
            record_dpm_run_for_support,
        ),
        current_logger=current_logger,
    )


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
    current_logger.info("Analyzing scenario batch")
    execution_context = build_batch_execution_context(
        request_policy_pack_id=request_policy_pack_id,
        tenant_default_policy_pack_id=tenant_default_policy_pack_id,
        tenant_id=tenant_id,
        catalog_loader=load_dpm_policy_pack_catalog,
    )
    current_logger.debug(
        "Resolved lotus-manage policy pack for analyze. enabled=%s source=%s policy_pack_id=%s",
        execution_context.policy_resolution_enabled,
        execution_context.policy_resolution_source,
        execution_context.selected_policy_pack_id,
    )

    return execute_batch_scenarios(
        request=request,
        batch_id=execution_context.batch_id,
        correlation_id=correlation_id,
        policy_definition=execution_context.policy_pack_definition,
        source_context=source_context,
        run_simulation_fn=resolve_callable_override("run_simulation", run_simulation),
        record_for_support=resolve_callable_override(
            "record_dpm_run_for_support",
            record_dpm_run_for_support,
        ),
        current_logger=current_logger,
    )


def run_analyze_async_operation(
    *,
    operation_id: str,
    service: DpmRunSupportService,
    execution_mode: str = "inline",
) -> None:
    run_analyze_async_operation_from_store(
        operation_id=operation_id,
        service=service,
        execution_mode=execution_mode,
        execute_batch_fn=resolve_callable_override(
            "_execute_batch_analysis",
            execute_batch_analysis,
        ),
        current_logger=_resolved_logger(),
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
    if not rebalance_async_config.async_operations_enabled():
        raise DpmRebalanceAsyncOperationsDisabledError("DPM_ASYNC_OPERATIONS_DISABLED")
    submission_context = build_async_submission_context(
        request=request,
        policy_pack_id=policy_pack_id,
        tenant_default_policy_pack_id=tenant_default_policy_pack_id,
        tenant_id=tenant_id,
        source_context=source_context,
        support_service_factory=get_dpm_run_support_service,
        catalog_loader=load_dpm_policy_pack_catalog,
    )
    current_logger.debug(
        "Resolved lotus-manage policy pack for analyze async. enabled=%s source=%s policy_pack_id=%s",
        submission_context.policy_resolution_enabled,
        submission_context.policy_resolution_source,
        submission_context.selected_policy_pack_id,
    )
    accepted = submit_analyze_async_request(
        service=submission_context.service,
        correlation_id=correlation_id,
        request_json=submission_context.request_json,
        source_context=source_context,
        execution_mode_label=submission_context.execution_mode.lower(),
    )
    if submission_context.execution_mode == "ACCEPT_ONLY":
        return accepted
    run_analyze_async_operation(
        operation_id=accepted.operation_id,
        service=submission_context.service,
        execution_mode="inline",
    )
    return accepted


def execute_dpm_async_operation(
    *, operation_id: str, service: DpmRunSupportService
) -> DpmAsyncOperationStatusResponse:
    if not rebalance_async_config.async_operations_enabled():
        raise DpmRebalanceAsyncOperationsDisabledError("DPM_ASYNC_OPERATIONS_DISABLED")
    if not rebalance_async_config.async_manual_execution_enabled():
        raise DpmRebalanceAsyncManualExecutionDisabledError("DPM_ASYNC_MANUAL_EXECUTION_DISABLED")
    return execute_analyze_async_operation_now(
        operation_id=operation_id,
        service=service,
        runner=run_analyze_async_operation,
    )


__all__ = [
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
    "execute_batch_analysis",
    "execute_dpm_async_operation",
    "run_analyze_async_operation",
    "run_simulation",
    "simulate_rebalance",
]
