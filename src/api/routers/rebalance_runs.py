import importlib
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.routers import rebalance_runs_config
from src.api.routers.runtime_utils import (
    assert_feature_enabled,
    normalize_backend_init_error,
    reject_unexpected_query_params,
)
from src.core.rebalance_runs import DpmRunSupportService
from src.core.rebalance_runs.repository import DpmRunRepository
from src.core.models import RebalanceResult

router = APIRouter(tags=["lotus-manage Run Supportability"])

_REPOSITORY = None
_SERVICE: Optional[DpmRunSupportService] = None


def _backend_init_error_detail(detail: str) -> str:
    return normalize_backend_init_error(
        detail=detail,
        required_detail="DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED",
        fallback_detail="DPM_SUPPORTABILITY_POSTGRES_CONNECTION_FAILED",
    )


def _assert_support_apis_enabled() -> None:
    assert_feature_enabled(
        name="DPM_SUPPORT_APIS_ENABLED",
        default=True,
        detail="DPM_SUPPORT_APIS_DISABLED",
    )


def _assert_async_operations_enabled() -> None:
    assert_feature_enabled(
        name="DPM_ASYNC_OPERATIONS_ENABLED",
        default=True,
        detail="DPM_ASYNC_OPERATIONS_DISABLED",
    )


def _assert_artifacts_enabled() -> None:
    assert_feature_enabled(
        name="DPM_ARTIFACTS_ENABLED",
        default=True,
        detail="DPM_ARTIFACTS_DISABLED",
    )


def _assert_workflow_enabled() -> None:
    assert_feature_enabled(
        name="DPM_WORKFLOW_ENABLED",
        default=False,
        detail="DPM_WORKFLOW_DISABLED",
    )


def _assert_lineage_apis_enabled() -> None:
    assert_feature_enabled(
        name="DPM_LINEAGE_APIS_ENABLED",
        default=False,
        detail="DPM_LINEAGE_APIS_DISABLED",
    )


def _assert_idempotency_history_apis_enabled() -> None:
    assert_feature_enabled(
        name="DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED",
        default=False,
        detail="DPM_IDEMPOTENCY_HISTORY_APIS_DISABLED",
    )


def _assert_supportability_summary_apis_enabled() -> None:
    assert_feature_enabled(
        name="DPM_SUPPORTABILITY_SUMMARY_APIS_ENABLED",
        default=True,
        detail="DPM_SUPPORTABILITY_SUMMARY_APIS_DISABLED",
    )


def _assert_support_bundle_apis_enabled() -> None:
    assert_feature_enabled(
        name="DPM_SUPPORT_BUNDLE_APIS_ENABLED",
        default=True,
        detail="DPM_SUPPORT_BUNDLE_APIS_DISABLED",
    )


def _supportability_store_backend_name() -> str:
    return rebalance_runs_config.supportability_store_backend_name()


_reject_unexpected_query_params = reject_unexpected_query_params


def _build_repository() -> DpmRunRepository:
    return rebalance_runs_config.build_repository()


def get_dpm_run_support_service() -> DpmRunSupportService:
    global _REPOSITORY
    global _SERVICE
    if _REPOSITORY is None:
        try:
            _REPOSITORY = _build_repository()
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=_backend_init_error_detail(str(exc)),
            ) from exc
    if _SERVICE is None:
        _SERVICE = DpmRunSupportService(
            repository=_REPOSITORY,
            async_operation_ttl_seconds=rebalance_runs_config.env_int(
                "DPM_ASYNC_OPERATIONS_TTL_SECONDS",
                86400,
            ),
            supportability_retention_days=rebalance_runs_config.env_non_negative_int(
                "DPM_SUPPORTABILITY_RETENTION_DAYS",
                0,
            ),
            workflow_enabled=rebalance_runs_config.env_flag("DPM_WORKFLOW_ENABLED", False),
            workflow_requires_review_for_statuses=rebalance_runs_config.env_csv_set(
                "DPM_WORKFLOW_REQUIRES_REVIEW_FOR_STATUSES",
                {"PENDING_REVIEW"},
            ),
            artifact_store_mode=rebalance_runs_config.artifact_store_mode(),
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


importlib.import_module("src.api.routers.rebalance_runs_inventory_routes")
importlib.import_module("src.api.routers.rebalance_runs_lookup_routes")
importlib.import_module("src.api.routers.rebalance_runs_support_bundle_routes")
importlib.import_module("src.api.routers.rebalance_runs_artifact_routes")
importlib.import_module("src.api.routers.rebalance_runs_async_operation_inventory_routes")
importlib.import_module("src.api.routers.rebalance_runs_async_operation_lookup_routes")
importlib.import_module("src.api.routers.rebalance_runs_lineage_routes")
importlib.import_module("src.api.routers.rebalance_runs_workflow_decision_routes")
importlib.import_module("src.api.routers.rebalance_runs_workflow_routes")

__all__ = [
    "Depends",
    "datetime",
    "get_dpm_run_support_service",
    "record_dpm_run_for_support",
    "reset_dpm_run_support_service_for_tests",
    "router",
    "_assert_artifacts_enabled",
    "_assert_async_operations_enabled",
    "_assert_idempotency_history_apis_enabled",
    "_assert_lineage_apis_enabled",
    "_assert_support_apis_enabled",
    "_assert_support_bundle_apis_enabled",
    "_assert_supportability_summary_apis_enabled",
    "_assert_workflow_enabled",
]
