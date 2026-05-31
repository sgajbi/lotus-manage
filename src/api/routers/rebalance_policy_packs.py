import importlib
import os
from typing import Annotated, Optional, cast

from fastapi import APIRouter, HTTPException, Path, Request, status

from src.api.observability import record_policy_pack_resolution
from src.api.routers.rebalance_policy_pack_docs import (
    POLICY_CATALOG_DELETE_DESCRIPTION,
    POLICY_CATALOG_DELETE_RESPONSES,
    POLICY_CATALOG_UPSERT_DESCRIPTION,
    POLICY_CATALOG_UPSERT_RESPONSES,
)
from src.api.routers.runtime_utils import (
    assert_feature_enabled,
    env_flag,
    normalize_backend_init_error,
    reject_unexpected_query_params,
)
from src.core.common.capabilities import psycopg_error_type
from src.core.rebalance.policy_pack_repository import DpmPolicyPackRepository
from src.core.rebalance.policy_packs import (
    DpmEffectivePolicyPackResolution,
    DpmPolicyPackDefinition,
    DpmPolicyPackMutationResponse,
    DpmPolicyPackUpsertRequest,
    resolve_effective_policy_pack,
)
from src.core.rebalance.tenant_policy_packs import build_tenant_policy_pack_resolver
from src.infrastructure.dpm_policy_packs import (
    PostgresDpmPolicyPackRepository,
)

router = APIRouter(tags=["lotus-manage Run Supportability"])

_reject_unexpected_query_params = reject_unexpected_query_params


def resolve_dpm_policy_pack(
    *,
    request_policy_pack_id: Optional[str],
    tenant_default_policy_pack_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> DpmEffectivePolicyPackResolution:
    resolved_tenant_default_policy_pack_id = tenant_default_policy_pack_id
    if resolved_tenant_default_policy_pack_id is None:
        tenant_policy_pack_resolver = build_tenant_policy_pack_resolver(
            enabled=env_flag("DPM_TENANT_POLICY_PACK_RESOLUTION_ENABLED", False),
            mapping_json=os.getenv("DPM_TENANT_POLICY_PACK_MAP_JSON"),
        )
        resolved_tenant_default_policy_pack_id = tenant_policy_pack_resolver.resolve(
            tenant_id=tenant_id
        )
    return resolve_effective_policy_pack(
        policy_packs_enabled=env_flag("DPM_POLICY_PACKS_ENABLED", False),
        request_policy_pack_id=request_policy_pack_id,
        tenant_default_policy_pack_id=resolved_tenant_default_policy_pack_id,
        global_default_policy_pack_id=os.getenv("DPM_DEFAULT_POLICY_PACK_ID"),
    )


def load_dpm_policy_pack_catalog() -> dict[str, DpmPolicyPackDefinition]:
    repository = _get_policy_pack_repository()
    items = repository.list_policy_packs()
    return {item.policy_pack_id: item for item in items}


def _policy_pack_catalog_backend_name() -> str:
    value = os.getenv("DPM_POLICY_PACK_CATALOG_BACKEND", "POSTGRES").strip().upper()
    if value != "POSTGRES":
        raise RuntimeError("DPM_POLICY_PACK_CATALOG_BACKEND_UNSUPPORTED")
    return value


def policy_pack_catalog_backend_name() -> str:
    return _policy_pack_catalog_backend_name()


def _policy_pack_postgres_dsn() -> str:
    return os.getenv(
        "DPM_POLICY_PACK_POSTGRES_DSN",
        os.getenv("DPM_SUPPORTABILITY_POSTGRES_DSN", ""),
    ).strip()


def policy_pack_postgres_dsn() -> str:
    return _policy_pack_postgres_dsn()


def postgres_connection_exception_types() -> tuple[type[BaseException], ...]:
    types: list[type[BaseException]] = [
        ConnectionError,
        OSError,
        TimeoutError,
        TypeError,
        ValueError,
    ]
    error_type = psycopg_error_type()
    if error_type is not None:
        types.append(error_type)
    return tuple(types)


def _postgres_connection_exception_types() -> tuple[type[BaseException], ...]:
    return postgres_connection_exception_types()


def _build_policy_pack_repository() -> DpmPolicyPackRepository:
    _ = _policy_pack_catalog_backend_name()
    dsn = _policy_pack_postgres_dsn()
    if not dsn:
        raise RuntimeError("DPM_POLICY_PACK_POSTGRES_DSN_REQUIRED")
    try:
        return cast(DpmPolicyPackRepository, PostgresDpmPolicyPackRepository(dsn=dsn))
    except RuntimeError:
        raise
    except _postgres_connection_exception_types() as exc:
        raise RuntimeError("DPM_POLICY_PACK_POSTGRES_CONNECTION_FAILED") from exc


def _get_policy_pack_repository() -> DpmPolicyPackRepository:
    try:
        return _build_policy_pack_repository()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=normalize_backend_init_error(
                detail=str(exc),
                required_detail="DPM_POLICY_PACK_POSTGRES_DSN_REQUIRED",
                fallback_detail="DPM_POLICY_PACK_POSTGRES_CONNECTION_FAILED",
            ),
        ) from exc


def _assert_policy_pack_admin_apis_enabled() -> None:
    assert_feature_enabled(
        name="DPM_POLICY_PACK_ADMIN_APIS_ENABLED",
        default=False,
        detail="DPM_POLICY_PACK_ADMIN_APIS_DISABLED",
    )


def reset_dpm_policy_pack_repository_for_tests() -> None:
    # no cached repository state is maintained in POSTGRES-only runtime mode
    return None


def _record_policy_pack_api_resolution(resolution: DpmEffectivePolicyPackResolution) -> None:
    record_policy_pack_resolution(
        surface="api",
        enabled=str(resolution.enabled).lower(),
        source=resolution.source.lower(),
        selected=str(resolution.selected_policy_pack_id is not None).lower(),
    )


importlib.import_module("src.api.routers.rebalance_policy_pack_effective_routes")
importlib.import_module("src.api.routers.rebalance_policy_pack_catalog_routes")


@router.put(
    "/rebalance/policies/catalog/{policy_pack_id}",
    response_model=DpmPolicyPackMutationResponse,
    status_code=status.HTTP_200_OK,
    summary="Upsert lotus-manage Policy Pack",
    description=POLICY_CATALOG_UPSERT_DESCRIPTION,
    responses=POLICY_CATALOG_UPSERT_RESPONSES,
)
def upsert_dpm_policy_pack(
    http_request: Request,
    policy_pack_id: Annotated[
        str,
        Path(
            description="Policy-pack identifier.",
            examples=["dpm_standard_v2"],
        ),
    ],
    upsert_request: DpmPolicyPackUpsertRequest,
) -> DpmPolicyPackMutationResponse:
    _reject_unexpected_query_params(http_request, allowed_params=set())
    _assert_policy_pack_admin_apis_enabled()
    repository = _get_policy_pack_repository()
    policy_pack = DpmPolicyPackDefinition(
        policy_pack_id=policy_pack_id,
        version=upsert_request.version,
        turnover_policy=upsert_request.turnover_policy,
        tax_policy=upsert_request.tax_policy,
        settlement_policy=upsert_request.settlement_policy,
        constraint_policy=upsert_request.constraint_policy,
        workflow_policy=upsert_request.workflow_policy,
        idempotency_policy=upsert_request.idempotency_policy,
    )
    repository.upsert_policy_pack(policy_pack)
    return DpmPolicyPackMutationResponse(item=policy_pack)


@router.delete(
    "/rebalance/policies/catalog/{policy_pack_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete lotus-manage Policy Pack",
    description=POLICY_CATALOG_DELETE_DESCRIPTION,
    responses=POLICY_CATALOG_DELETE_RESPONSES,
)
def delete_dpm_policy_pack(
    request: Request,
    policy_pack_id: Annotated[
        str,
        Path(
            description="Policy-pack identifier.",
            examples=["dpm_standard_v2"],
        ),
    ],
) -> None:
    _reject_unexpected_query_params(request, allowed_params=set())
    _assert_policy_pack_admin_apis_enabled()
    repository = _get_policy_pack_repository()
    deleted = repository.delete_policy_pack(policy_pack_id=policy_pack_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="DPM_POLICY_PACK_NOT_FOUND"
        )
