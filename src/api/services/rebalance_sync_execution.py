import logging
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from src.observability.metrics import record_execution_call
from src.api.request_models import RebalanceRequest
from src.api.services.rebalance_client_restriction_policy import apply_client_restriction_policy
from src.api.services.rebalance_run_support_service import DpmRunSupportServiceUnavailableError
from src.api.services.rebalance_simulation_errors import (
    DpmRebalanceIdempotencyConflictError,
    DpmRebalanceIdempotencyStoreInconsistentError,
    DpmRebalanceIdempotencyStoreWriteFailedError,
    DpmRebalanceSubmissionInProgressError,
    DpmRebalanceSupportabilityStoreUnavailableError,
)
from src.api.services.rebalance_source_lineage import apply_source_lineage, source_input_mode
from src.core.dpm_source_context import DpmResolvedSourceContext
from src.core.models import RebalanceResult
from src.core.rebalance.policy_packs import (
    DpmPolicyPackDefinition,
    apply_policy_pack_to_engine_options,
)
from src.core.rebalance_runs import DpmRunSupportService
from src.core.rebalance_runs.models import DpmSimulationSubmissionClaimRecord
from src.core.rebalance_runs.repository import DpmRunRepositoryConflictError

RunSimulationFn = Callable[..., RebalanceResult]
RecordForSupportFn = Callable[..., object]
SupportServiceFactory = Callable[[], DpmRunSupportService]


def execution_outcome_for_status(status_value: str) -> str:
    return "blocked" if status_value == "BLOCKED" else "success"


def execution_status_label(status_value: str) -> str:
    return status_value.lower()


def execute_simulation_request(
    *,
    request: RebalanceRequest,
    idempotency_key: str,
    request_hash: str,
    correlation_id: str,
    policy_pack_definition: Optional[DpmPolicyPackDefinition],
    replay_enabled: bool,
    source_context: Optional[DpmResolvedSourceContext],
    tenant_id: str,
    support_service_factory: SupportServiceFactory,
    run_simulation_fn: RunSimulationFn,
    record_for_support: RecordForSupportFn,
    current_logger: logging.Logger | Any,
) -> RebalanceResult:
    effective_options = apply_policy_pack_to_engine_options(
        options=request.options,
        policy_pack=policy_pack_definition,
    )

    del replay_enabled, record_for_support
    try:
        support_service = support_service_factory()
    except DpmRunSupportServiceUnavailableError as exc:
        raise DpmRebalanceSupportabilityStoreUnavailableError(exc.detail) from exc

    claim_token = uuid.uuid4().hex
    claim = _claim_submission(
        support_service=support_service,
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        claim_token=claim_token,
    )
    replay = _resolved_claim_result(
        support_service=support_service,
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        claim_token=claim_token,
        claim=claim,
        source_context=source_context,
    )
    if replay is not None:
        return replay

    try:
        result = run_simulation_fn(
            portfolio=request.portfolio_snapshot,
            market_data=request.market_data_snapshot,
            model=request.model_portfolio,
            shelf=request.shelf_entries,
            options=effective_options,
            request_hash=request_hash,
            correlation_id=correlation_id,
        )
        result = apply_source_lineage(result=result, source_context=source_context)
        result = apply_client_restriction_policy(
            request=request,
            result=result,
            source_context=source_context,
        )
        support_service.complete_simulation_submission(
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            claim_token=claim_token,
            result=result,
            portfolio_id=request.portfolio_snapshot.portfolio_id,
        )
    except DpmRunRepositoryConflictError:
        replay = _wait_for_completed_submission(
            support_service=support_service,
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            source_context=source_context,
        )
        if replay is not None:
            return replay
        raise DpmRebalanceSubmissionInProgressError("DPM_REBALANCE_REQUEST_IN_PROGRESS")
    except (RuntimeError, ValueError) as exc:
        support_service.abandon_simulation_submission_claim(
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            claim_token=claim_token,
        )
        raise DpmRebalanceIdempotencyStoreWriteFailedError(
            "DPM_IDEMPOTENCY_STORE_WRITE_FAILED"
        ) from exc
    except Exception:
        support_service.abandon_simulation_submission_claim(
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            claim_token=claim_token,
        )
        raise

    if result.status == "BLOCKED":
        current_logger.warning("Run blocked by DPM engine safety rules")

    record_execution_call(
        operation="simulate",
        input_mode=source_input_mode(source_context),
        outcome=execution_outcome_for_status(result.status),
        result_status=execution_status_label(result.status),
    )
    return result


def _claim_submission(
    *,
    support_service: DpmRunSupportService,
    tenant_id: str,
    idempotency_key: str,
    request_hash: str,
    claim_token: str,
) -> DpmSimulationSubmissionClaimRecord:
    now = datetime.now(timezone.utc)
    return support_service.claim_simulation_submission(
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        claim_token=claim_token,
        claimed_at=now,
        claim_expires_at=now + timedelta(seconds=60),
    )


def _resolved_claim_result(
    *,
    support_service: DpmRunSupportService,
    tenant_id: str,
    idempotency_key: str,
    request_hash: str,
    claim_token: str,
    claim: Any,
    source_context: Optional[DpmResolvedSourceContext],
) -> RebalanceResult | None:
    if claim.request_hash != request_hash:
        record_execution_call(
            operation="simulate",
            input_mode=source_input_mode(source_context),
            outcome="conflict",
            result_status="failed",
        )
        raise DpmRebalanceIdempotencyConflictError(
            "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"
        )
    if claim.status == "COMPLETED":
        return _load_completed_result(
            support_service=support_service,
            tenant_id=tenant_id,
            rebalance_run_id=claim.rebalance_run_id,
            source_context=source_context,
        )
    if claim.claim_token == claim_token:
        return None
    replay = _wait_for_completed_submission(
        support_service=support_service,
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        source_context=source_context,
    )
    if replay is not None:
        return replay
    raise DpmRebalanceSubmissionInProgressError("DPM_REBALANCE_REQUEST_IN_PROGRESS")


def _wait_for_completed_submission(
    *,
    support_service: DpmRunSupportService,
    tenant_id: str,
    idempotency_key: str,
    request_hash: str,
    source_context: Optional[DpmResolvedSourceContext],
) -> RebalanceResult | None:
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        claim = support_service.get_simulation_submission_claim(
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
        )
        if claim is None:
            return None
        if claim.request_hash != request_hash:
            raise DpmRebalanceIdempotencyConflictError(
                "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"
            )
        if claim.status == "COMPLETED":
            return _load_completed_result(
                support_service=support_service,
                tenant_id=tenant_id,
                rebalance_run_id=claim.rebalance_run_id,
                source_context=source_context,
            )
        if claim.claim_expires_at <= datetime.now(timezone.utc):
            return None
        time.sleep(0.025)
    return None


def _load_completed_result(
    *,
    support_service: DpmRunSupportService,
    tenant_id: str,
    rebalance_run_id: str | None,
    source_context: Optional[DpmResolvedSourceContext],
) -> RebalanceResult:
    if rebalance_run_id is None:
        raise DpmRebalanceIdempotencyStoreInconsistentError("DPM_IDEMPOTENCY_STORE_INCONSISTENT")
    try:
        stored = support_service.get_run_for_tenant(
            tenant_id=tenant_id,
            rebalance_run_id=rebalance_run_id,
        )
    except Exception as exc:
        raise DpmRebalanceIdempotencyStoreInconsistentError(
            "DPM_IDEMPOTENCY_STORE_INCONSISTENT"
        ) from exc
    replay_result = RebalanceResult.model_validate(stored.result)
    record_execution_call(
        operation="simulate",
        input_mode=source_input_mode(source_context),
        outcome="replayed",
        result_status=execution_status_label(replay_result.status),
    )
    return replay_result


__all__ = [
    "RecordForSupportFn",
    "RunSimulationFn",
    "SupportServiceFactory",
    "execute_simulation_request",
    "execution_outcome_for_status",
    "execution_status_label",
]
