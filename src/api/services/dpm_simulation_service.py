import logging
import os
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, cast

from fastapi import HTTPException, status
from pydantic import ValidationError

from src.api.request_models import RebalanceRequest
from src.api.routers.dpm_policy_packs import load_dpm_policy_pack_catalog, resolve_dpm_policy_pack
from src.api.routers.dpm_runs import get_dpm_run_support_service, record_dpm_run_for_support
from src.core.common.canonical import hash_canonical_payload
from src.core.dpm.engine import run_simulation
from src.core.dpm.policy_packs import (
    apply_policy_pack_to_engine_options,
    resolve_policy_pack_definition,
    resolve_policy_pack_replay_enabled,
)
from src.core.dpm_runs import (
    DpmAsyncAcceptedResponse,
    DpmAsyncOperationStatusResponse,
    DpmRunLookupResponse,
    DpmRunNotFoundError,
    DpmRunSupportService,
)
from src.core.models import (
    BatchRebalanceRequest,
    BatchRebalanceResult,
    BatchScenarioMetric,
    EngineOptions,
    Money,
    RebalanceResult,
)

logger = logging.getLogger(__name__)

DPM_IDEMPOTENCY_CACHE: "OrderedDict[str, Dict[str, object]]" = OrderedDict()
DEFAULT_DPM_IDEMPOTENCY_CACHE_SIZE = 1000


def _main_override(name: str) -> Any | None:
    try:
        from src.api import main as main_module
    except ImportError:
        return None
    return getattr(main_module, name, None)


def _resolved_logger() -> logging.Logger | Any:
    return _main_override("logger") or logger


def env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed >= 1 else default


def resolve_async_execution_mode() -> str:
    value = os.getenv("DPM_ASYNC_EXECUTION_MODE", "INLINE")
    normalized = value.strip().upper()
    if normalized in {"INLINE", "ACCEPT_ONLY"}:
        return normalized
    return "INLINE"


def async_manual_execution_enabled() -> bool:
    return env_flag("DPM_ASYNC_MANUAL_EXECUTION_ENABLED", True)


def to_invalid_options_error(exc: ValidationError) -> str:
    first_error = exc.errors()[0]
    return f"INVALID_OPTIONS: {first_error.get('msg', 'validation failed')}"


def resolve_base_snapshot_ids(request: BatchRebalanceRequest) -> Dict[str, str]:
    return {
        "portfolio_snapshot_id": (
            request.portfolio_snapshot.snapshot_id or request.portfolio_snapshot.portfolio_id
        ),
        "market_data_snapshot_id": request.market_data_snapshot.snapshot_id or "md",
    }


def build_comparison_metric(
    scenario_result: RebalanceResult,
    base_currency: str,
) -> BatchScenarioMetric:
    security_intents = [
        intent for intent in scenario_result.intents if intent.intent_type == "SECURITY_TRADE"
    ]
    turnover_proxy = sum(
        (
            intent.notional_base.amount
            for intent in security_intents
            if intent.notional_base is not None
        ),
        Decimal("0"),
    )
    return BatchScenarioMetric(
        status=scenario_result.status,
        security_intent_count=len(security_intents),
        gross_turnover_notional_base=Money(amount=turnover_proxy, currency=base_currency),
    )


def simulate_rebalance(
    *,
    request: RebalanceRequest,
    idempotency_key: str,
    correlation_id: Optional[str],
    policy_pack_id: Optional[str],
    tenant_id: Optional[str],
) -> RebalanceResult:
    current_logger = _resolved_logger()
    resolved_correlation_id = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
    current_logger.info(
        "Simulating rebalance. CID=%s Idempotency=%s",
        resolved_correlation_id,
        idempotency_key,
    )
    default_replay_enabled = env_flag("DPM_IDEMPOTENCY_REPLAY_ENABLED", True)
    request_payload = request.model_dump(mode="json")
    request_hash = hash_canonical_payload(request_payload)
    policy_pack = resolve_dpm_policy_pack(
        request_policy_pack_id=policy_pack_id,
        tenant_id=tenant_id,
    )
    policy_pack_definition = resolve_policy_pack_definition(
        resolution=policy_pack,
        catalog=load_dpm_policy_pack_catalog(),
    )
    effective_options = apply_policy_pack_to_engine_options(
        options=request.options,
        policy_pack=policy_pack_definition,
    )
    replay_enabled = resolve_policy_pack_replay_enabled(
        default_replay_enabled=default_replay_enabled,
        policy_pack=policy_pack_definition,
    )
    current_logger.debug(
        "Resolved DPM policy pack for simulate. enabled=%s source=%s policy_pack_id=%s",
        policy_pack.enabled,
        policy_pack.source,
        policy_pack.selected_policy_pack_id,
    )

    if replay_enabled:
        support_service = get_dpm_run_support_service()
        existing = None
        try:
            existing = support_service.get_idempotency_lookup(idempotency_key=idempotency_key)
        except DpmRunNotFoundError:
            existing = None
        if existing is not None and existing.request_hash != request_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="IDEMPOTENCY_KEY_CONFLICT: request hash mismatch",
            )
        if existing is not None:
            try:
                replay_run: DpmRunLookupResponse = support_service.get_run(
                    rebalance_run_id=existing.rebalance_run_id
                )
            except DpmRunNotFoundError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="DPM_IDEMPOTENCY_STORE_INCONSISTENT",
                ) from exc
            return cast(RebalanceResult, RebalanceResult.model_validate(replay_run.result))

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
    except (HTTPException, RuntimeError, ValueError) as exc:
        if replay_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="DPM_IDEMPOTENCY_STORE_WRITE_FAILED",
            ) from exc
        current_logger.exception(
            "Supportability persistence failed. RunID=%s CorrelationID=%s",
            result.rebalance_run_id,
            result.correlation_id,
        )

    if result.status == "BLOCKED":
        current_logger.warning("Run blocked. Diagnostics: %s", result.diagnostics)

    return result


def execute_batch_analysis(
    *,
    request: BatchRebalanceRequest,
    correlation_id: Optional[str],
    request_policy_pack_id: Optional[str] = None,
    tenant_default_policy_pack_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> BatchRebalanceResult:
    current_logger = _resolved_logger()
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    current_logger.info("Analyzing scenario batch. CID=%s BatchID=%s", correlation_id, batch_id)

    results = {}
    comparison_metrics = {}
    failed_scenarios = {}
    warnings = []
    policy_resolution = resolve_dpm_policy_pack(
        request_policy_pack_id=request_policy_pack_id,
        tenant_default_policy_pack_id=tenant_default_policy_pack_id,
        tenant_id=tenant_id,
    )
    policy_definition = resolve_policy_pack_definition(
        resolution=policy_resolution,
        catalog=load_dpm_policy_pack_catalog(),
    )

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
        except (HTTPException, ValidationError, RuntimeError, ValueError) as exc:
            current_logger.exception("Scenario execution failed. Scenario=%s", scenario_name)
            failed_scenarios[scenario_name] = f"SCENARIO_EXECUTION_ERROR: {type(exc).__name__}"

    if failed_scenarios:
        warnings.append("PARTIAL_BATCH_FAILURE")

    return BatchRebalanceResult(
        batch_run_id=batch_id,
        run_at_utc=datetime.now(timezone.utc).isoformat(),
        base_snapshot_ids=resolve_base_snapshot_ids(request),
        results=results,
        comparison_metrics=comparison_metrics,
        failed_scenarios=failed_scenarios,
        warnings=warnings,
    )


def run_analyze_async_operation(*, operation_id: str, service: DpmRunSupportService) -> None:
    current_logger = _resolved_logger()
    request_json, operation_correlation_id = service.prepare_analyze_operation_execution(
        operation_id=operation_id
    )
    try:
        if isinstance(request_json, dict) and "batch_request" in request_json:
            batch_payload = request_json.get("batch_request") or {}
            policy_context = request_json.get("policy_context") or {}
            request_policy_pack_id = policy_context.get("request_policy_pack_id")
            tenant_default_policy_pack_id = policy_context.get("tenant_default_policy_pack_id")
            tenant_id = policy_context.get("tenant_id")
        else:
            batch_payload = request_json
            request_policy_pack_id = None
            tenant_default_policy_pack_id = None
            tenant_id = None
        batch_request = BatchRebalanceRequest.model_validate(batch_payload)
        execute_batch_fn = _main_override("_execute_batch_analysis") or execute_batch_analysis
        result = execute_batch_fn(
            request=batch_request,
            correlation_id=operation_correlation_id,
            request_policy_pack_id=request_policy_pack_id,
            tenant_default_policy_pack_id=tenant_default_policy_pack_id,
            tenant_id=tenant_id,
        )
        service.complete_operation_success(
            operation_id=operation_id,
            result_json=result.model_dump(mode="json"),
        )
    except (DpmRunNotFoundError, ValidationError, HTTPException, RuntimeError, ValueError) as exc:
        current_logger.exception("Asynchronous batch analysis failed. OperationID=%s", operation_id)
        service.complete_operation_failure(
            operation_id=operation_id,
            code=type(exc).__name__,
            message=str(exc),
        )


def submit_and_optionally_execute_async_analysis(
    *,
    request: BatchRebalanceRequest,
    correlation_id: Optional[str],
    policy_pack_id: Optional[str],
    tenant_id: Optional[str],
) -> DpmAsyncAcceptedResponse:
    current_logger = _resolved_logger()
    if not env_flag("DPM_ASYNC_OPERATIONS_ENABLED", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DPM_ASYNC_OPERATIONS_DISABLED",
        )
    service = get_dpm_run_support_service()
    policy_pack = resolve_dpm_policy_pack(
        request_policy_pack_id=policy_pack_id,
        tenant_id=tenant_id,
    )
    current_logger.debug(
        "Resolved DPM policy pack for analyze async. enabled=%s source=%s policy_pack_id=%s",
        policy_pack.enabled,
        policy_pack.source,
        policy_pack.selected_policy_pack_id,
    )
    accepted = service.submit_analyze_async(
        correlation_id=correlation_id,
        request_json={
            "batch_request": request.model_dump(mode="json"),
            "policy_context": {
                "request_policy_pack_id": policy_pack_id,
                "tenant_default_policy_pack_id": None,
                "tenant_id": tenant_id,
            },
        },
    )
    if resolve_async_execution_mode() == "ACCEPT_ONLY":
        return accepted
    run_analyze_async_operation(operation_id=accepted.operation_id, service=service)
    return accepted


def execute_dpm_async_operation(
    *, operation_id: str, service: DpmRunSupportService
) -> DpmAsyncOperationStatusResponse:
    if not env_flag("DPM_ASYNC_OPERATIONS_ENABLED", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DPM_ASYNC_OPERATIONS_DISABLED",
        )
    if not async_manual_execution_enabled():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DPM_ASYNC_MANUAL_EXECUTION_DISABLED",
        )
    try:
        run_analyze_async_operation(operation_id=operation_id, service=service)
    except DpmRunNotFoundError as exc:
        detail = str(exc)
        if detail == "DPM_ASYNC_OPERATION_NOT_EXECUTABLE":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
    return service.get_async_operation(operation_id=operation_id)
