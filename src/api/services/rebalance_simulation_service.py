import logging
import uuid
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
from src.api.services.rebalance_policy_pack_service import (
    load_dpm_policy_pack_catalog,
)
from src.api.services.rebalance_policy_pack_execution import (
    resolve_execution_policy_pack_context,
    resolve_selected_policy_pack_definition as resolve_selected_policy_pack_definition_from_catalog,
)
from src.api.services.rebalance_request_envelope_resolution import (
    resolve_batch_request_envelope as resolve_batch_request_envelope_from_source,
    resolve_rebalance_request_envelope as resolve_rebalance_request_envelope_from_source,
)
from src.api.services.rebalance_async_config import (
    async_manual_execution_enabled,
    async_operations_enabled,
    env_flag,
    resolve_async_execution_mode,
)
from src.api.services.rebalance_async_operation_runner import (
    run_analyze_async_operation_from_store,
)
from src.api.services.rebalance_async_submission_payload import build_analyze_async_request_json
from src.api.services.rebalance_async_submission import submit_analyze_async_request
from src.api.services.rebalance_async_manual_execution import (
    execute_analyze_async_operation_now,
)
from src.api.services.rebalance_batch_execution import execute_batch_scenarios
from src.api.services.rebalance_sync_execution import execute_simulation_request
from src.api.services.rebalance_run_support_service import (
    DpmRunSupportServiceUnavailableError,
    get_dpm_run_support_service,
    record_dpm_run_for_support,
)
from src.api.services.rebalance_source_lineage import apply_source_lineage, source_input_mode
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
from src.core.rebalance.policy_packs import (
    DpmEffectivePolicyPackResolution,
    DpmPolicyPackDefinition,
    resolve_policy_pack_replay_enabled,
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
    return resolve_selected_policy_pack_definition_from_catalog(
        policy_pack=policy_pack,
        catalog_loader=load_dpm_policy_pack_catalog,
    )


def _resolve_stateful_source_context(
    *,
    envelope: RebalanceExecutionRequestEnvelope | BatchExecutionRequestEnvelope,
    correlation_id: Optional[str],
) -> DpmResolvedSourceContext:
    resolver_factory = _main_override("build_core_resolver_client") or build_core_resolver_client
    return resolve_stateful_source_context(
        envelope=envelope,
        correlation_id=correlation_id,
        stateful_enabled=stateful_core_sourcing_enabled(),
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
    resolved_correlation_id = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
    current_logger.info("Simulating rebalance request")
    default_replay_enabled = env_flag("DPM_IDEMPOTENCY_REPLAY_ENABLED", True)
    request_payload = request.model_dump(mode="json")
    request_hash = hash_canonical_payload(request_payload)
    policy_context = resolve_execution_policy_pack_context(
        request_policy_pack_id=policy_pack_id,
        tenant_default_policy_pack_id=tenant_default_policy_pack_id,
        tenant_id=tenant_id,
        surface="simulate",
        catalog_loader=load_dpm_policy_pack_catalog,
    )
    replay_enabled = resolve_policy_pack_replay_enabled(
        default_replay_enabled=default_replay_enabled,
        policy_pack=policy_context.definition,
    )
    current_logger.debug(
        "Resolved lotus-manage policy pack for simulate. enabled=%s source=%s policy_pack_id=%s",
        policy_context.resolution.enabled,
        policy_context.resolution.source,
        policy_context.resolution.selected_policy_pack_id,
    )

    return execute_simulation_request(
        request=request,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        correlation_id=resolved_correlation_id,
        policy_pack_definition=policy_context.definition,
        replay_enabled=replay_enabled,
        source_context=source_context,
        support_service_factory=get_dpm_run_support_service,
        run_simulation_fn=_main_override("run_simulation") or run_simulation,
        record_for_support=_main_override("record_dpm_run_for_support")
        or record_dpm_run_for_support,
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
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    current_logger.info("Analyzing scenario batch")

    policy_context = resolve_execution_policy_pack_context(
        request_policy_pack_id=request_policy_pack_id,
        tenant_default_policy_pack_id=tenant_default_policy_pack_id,
        tenant_id=tenant_id,
        surface="analyze",
        catalog_loader=load_dpm_policy_pack_catalog,
    )

    return execute_batch_scenarios(
        request=request,
        batch_id=batch_id,
        correlation_id=correlation_id,
        policy_definition=policy_context.definition,
        source_context=source_context,
        run_simulation_fn=_main_override("run_simulation") or run_simulation,
        record_for_support=_main_override("record_dpm_run_for_support")
        or record_dpm_run_for_support,
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
        execute_batch_fn=_main_override("_execute_batch_analysis") or execute_batch_analysis,
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
    if not async_operations_enabled():
        raise DpmRebalanceAsyncOperationsDisabledError("DPM_ASYNC_OPERATIONS_DISABLED")
    try:
        service = get_dpm_run_support_service()
    except DpmRunSupportServiceUnavailableError as exc:
        raise DpmRebalanceAsyncOperationSupportUnavailableError(exc.detail) from exc
    policy_context = resolve_execution_policy_pack_context(
        request_policy_pack_id=policy_pack_id,
        tenant_default_policy_pack_id=tenant_default_policy_pack_id,
        tenant_id=tenant_id,
        surface="analyze_async",
        catalog_loader=load_dpm_policy_pack_catalog,
        load_definition=False,
    )
    current_logger.debug(
        "Resolved lotus-manage policy pack for analyze async. enabled=%s source=%s policy_pack_id=%s",
        policy_context.resolution.enabled,
        policy_context.resolution.source,
        policy_context.resolution.selected_policy_pack_id,
    )
    execution_mode = resolve_async_execution_mode()
    accepted = submit_analyze_async_request(
        service=service,
        correlation_id=correlation_id,
        request_json=build_analyze_async_request_json(
            request=request,
            policy_pack_id=policy_pack_id,
            tenant_default_policy_pack_id=tenant_default_policy_pack_id,
            tenant_id=tenant_id,
            source_context=source_context,
        ),
        source_context=source_context,
        execution_mode_label=execution_mode.lower(),
    )
    if execution_mode == "ACCEPT_ONLY":
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
