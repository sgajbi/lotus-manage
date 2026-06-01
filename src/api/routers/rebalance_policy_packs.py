from fastapi import APIRouter, HTTPException, status

from src.api.observability import record_policy_pack_resolution
from src.api.routers.runtime_utils import (
    assert_feature_enabled,
    reject_unexpected_query_params,
)
from src.api.routers.route_registration import register_route_modules
from src.api.services.rebalance_policy_pack_service import (
    DpmPolicyPackCatalogUnavailableError,
)
from src.api.services.rebalance_policy_pack_service import (
    get_policy_pack_repository as get_policy_pack_application_repository,
)
from src.api.services.rebalance_policy_pack_service import (
    load_dpm_policy_pack_catalog,
    policy_pack_catalog_backend_name,
    policy_pack_postgres_dsn,
    postgres_connection_exception_types,
    reset_dpm_policy_pack_repository_for_tests,
    resolve_dpm_policy_pack,
)
from src.core.rebalance.policy_pack_repository import DpmPolicyPackRepository
from src.core.rebalance.policy_packs import (
    DpmEffectivePolicyPackResolution,
)

router = APIRouter(tags=["lotus-manage Run Supportability"])

_reject_unexpected_query_params = reject_unexpected_query_params


def _postgres_connection_exception_types() -> tuple[type[BaseException], ...]:
    return postgres_connection_exception_types()


def _get_policy_pack_repository() -> DpmPolicyPackRepository:
    try:
        return get_policy_pack_application_repository()
    except DpmPolicyPackCatalogUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.detail,
        ) from exc


def _assert_policy_pack_admin_apis_enabled() -> None:
    assert_feature_enabled(
        name="DPM_POLICY_PACK_ADMIN_APIS_ENABLED",
        default=False,
        detail="DPM_POLICY_PACK_ADMIN_APIS_DISABLED",
    )


def _record_policy_pack_api_resolution(resolution: DpmEffectivePolicyPackResolution) -> None:
    record_policy_pack_resolution(
        surface="api",
        enabled=str(resolution.enabled).lower(),
        source=resolution.source.lower(),
        selected=str(resolution.selected_policy_pack_id is not None).lower(),
    )


_ROUTE_MODULES: tuple[str, ...] = (
    "src.api.routers.rebalance_policy_pack_effective_routes",
    "src.api.routers.rebalance_policy_pack_catalog_routes",
    "src.api.routers.rebalance_policy_pack_admin_routes",
)

register_route_modules(_ROUTE_MODULES)

__all__ = [
    "_assert_policy_pack_admin_apis_enabled",
    "_get_policy_pack_repository",
    "_postgres_connection_exception_types",
    "_record_policy_pack_api_resolution",
    "_reject_unexpected_query_params",
    "load_dpm_policy_pack_catalog",
    "policy_pack_catalog_backend_name",
    "policy_pack_postgres_dsn",
    "reset_dpm_policy_pack_repository_for_tests",
    "resolve_dpm_policy_pack",
    "router",
]
