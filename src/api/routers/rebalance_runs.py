from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.routers.route_registration import register_route_modules
from src.api.routers.runtime_utils import (
    assert_feature_enabled,
    reject_unexpected_query_params,
)
from src.api.services import rebalance_run_support_config
from src.api.services.rebalance_run_support_service import (
    DpmRunSupportServiceUnavailableError,
)
from src.api.services.rebalance_run_support_service import (
    get_dpm_run_support_service as get_dpm_run_support_application_service,
)
from src.api.services.rebalance_run_support_service import (
    record_dpm_run_for_support as record_dpm_run_for_support_application,
)
from src.api.services.rebalance_run_support_service import (
    reset_dpm_run_support_service_for_tests as reset_dpm_run_support_application_service_for_tests,
)
from src.core.rebalance_runs import DpmRunSupportService
from src.core.models import RebalanceResult

router = APIRouter(tags=["lotus-manage Run Supportability"])


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
    return rebalance_run_support_config.supportability_store_backend_name()


_reject_unexpected_query_params = reject_unexpected_query_params


def get_dpm_run_support_service() -> DpmRunSupportService:
    try:
        return get_dpm_run_support_application_service()
    except DpmRunSupportServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.detail,
        ) from exc


def record_dpm_run_for_support(
    *,
    result: RebalanceResult,
    request_hash: str,
    portfolio_id: str,
    idempotency_key: Optional[str],
) -> None:
    try:
        record_dpm_run_for_support_application(
            result=result,
            request_hash=request_hash,
            portfolio_id=portfolio_id,
            idempotency_key=idempotency_key,
        )
    except DpmRunSupportServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.detail,
        ) from exc


def reset_dpm_run_support_service_for_tests() -> None:
    reset_dpm_run_support_application_service_for_tests()


_ROUTE_MODULES: tuple[str, ...] = (
    "src.api.routers.rebalance_runs_inventory_routes",
    "src.api.routers.rebalance_runs_lookup_correlation_routes",
    "src.api.routers.rebalance_runs_lookup_request_hash_routes",
    "src.api.routers.rebalance_runs_lookup_idempotency_routes",
    "src.api.routers.rebalance_runs_lookup_idempotency_history_routes",
    "src.api.routers.rebalance_runs_lookup_run_routes",
    "src.api.routers.rebalance_runs_support_bundle_run_routes",
    "src.api.routers.rebalance_runs_support_bundle_correlation_routes",
    "src.api.routers.rebalance_runs_support_bundle_idempotency_routes",
    "src.api.routers.rebalance_runs_support_bundle_operation_routes",
    "src.api.routers.rebalance_runs_artifact_routes",
    "src.api.routers.rebalance_runs_async_operation_inventory_routes",
    "src.api.routers.rebalance_runs_async_operation_lookup_routes",
    "src.api.routers.rebalance_runs_lineage_routes",
    "src.api.routers.rebalance_runs_workflow_decision_routes",
    "src.api.routers.rebalance_runs_workflow_state_routes",
    "src.api.routers.rebalance_runs_workflow_action_routes",
    "src.api.routers.rebalance_runs_workflow_history_routes",
)

register_route_modules(_ROUTE_MODULES)

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
