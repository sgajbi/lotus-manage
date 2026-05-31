from __future__ import annotations

from typing import Optional

from src.api.services import rebalance_run_support_config
from src.core.models import RebalanceResult
from src.core.rebalance_runs import DpmRunSupportService
from src.core.rebalance_runs.repository import DpmRunRepository

_REPOSITORY: Optional[DpmRunRepository] = None
_SERVICE: Optional[DpmRunSupportService] = None


class DpmRunSupportServiceUnavailableError(RuntimeError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def _backend_init_error_detail(detail: str) -> str:
    if detail == "DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED":
        return detail
    return "DPM_SUPPORTABILITY_POSTGRES_CONNECTION_FAILED"


def _build_repository() -> DpmRunRepository:
    return rebalance_run_support_config.build_repository()


def get_dpm_run_support_service() -> DpmRunSupportService:
    global _REPOSITORY
    global _SERVICE
    if _REPOSITORY is None:
        try:
            _REPOSITORY = _build_repository()
        except RuntimeError as exc:
            raise DpmRunSupportServiceUnavailableError(
                _backend_init_error_detail(str(exc))
            ) from exc
    if _SERVICE is None:
        _SERVICE = DpmRunSupportService(
            repository=_REPOSITORY,
            async_operation_ttl_seconds=rebalance_run_support_config.env_int(
                "DPM_ASYNC_OPERATIONS_TTL_SECONDS",
                86400,
            ),
            supportability_retention_days=rebalance_run_support_config.env_non_negative_int(
                "DPM_SUPPORTABILITY_RETENTION_DAYS",
                0,
            ),
            workflow_enabled=rebalance_run_support_config.env_flag("DPM_WORKFLOW_ENABLED", False),
            workflow_requires_review_for_statuses=rebalance_run_support_config.env_csv_set(
                "DPM_WORKFLOW_REQUIRES_REVIEW_FOR_STATUSES",
                {"PENDING_REVIEW"},
            ),
            artifact_store_mode=rebalance_run_support_config.artifact_store_mode(),
        )
    return _SERVICE


def record_dpm_run_for_support(
    *,
    result: RebalanceResult,
    request_hash: str,
    portfolio_id: str,
    idempotency_key: Optional[str],
) -> None:
    service = get_dpm_run_support_service()
    service.record_run(
        result=result,
        request_hash=request_hash,
        portfolio_id=portfolio_id,
        idempotency_key=idempotency_key,
    )


def reset_dpm_run_support_service_for_tests() -> None:
    global _REPOSITORY
    global _SERVICE
    _REPOSITORY = None
    _SERVICE = None


__all__ = [
    "DpmRunSupportServiceUnavailableError",
    "get_dpm_run_support_service",
    "record_dpm_run_for_support",
    "reset_dpm_run_support_service_for_tests",
]
