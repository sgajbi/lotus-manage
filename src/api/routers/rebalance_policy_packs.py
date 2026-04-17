import os
from typing import Annotated, Optional, cast

from fastapi import APIRouter, Header, HTTPException, Path, Request, status

from src.api.routers.runtime_utils import (
    assert_feature_enabled,
    env_flag,
    normalize_backend_init_error,
)
from src.core.common.capabilities import psycopg_error_type
from src.core.rebalance.policy_pack_repository import DpmPolicyPackRepository
from src.core.rebalance.policy_packs import (
    DpmEffectivePolicyPackResolution,
    DpmPolicyPackCatalogResponse,
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


def _reject_unexpected_query_params(
    request: Request,
    *,
    allowed_params: set[str],
) -> None:
    unexpected = sorted(name for name in request.query_params if name not in allowed_params)
    if unexpected:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "UNSUPPORTED_QUERY_PARAMETER: "
                + ", ".join(unexpected)
                + " not supported for this endpoint"
            ),
        )


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


@router.get(
    "/rebalance/policies/effective",
    response_model=DpmEffectivePolicyPackResolution,
    status_code=status.HTTP_200_OK,
    summary="Resolve Effective lotus-manage Policy Pack",
    description=(
        "Returns the effective lotus-manage policy-pack resolution using configured precedence "
        "(request, tenant default, global default). This endpoint is read-only and "
        "intended for supportability and integration diagnostics. Supply resolution context via "
        "the documented headers rather than query parameters."
    ),
    responses={
        422: {
            "description": "Unsupported query parameters were supplied.",
        },
    },
)
def get_effective_dpm_policy_pack(
    request: Request,
    x_policy_pack_id: Annotated[
        Optional[str],
        Header(
            description="Optional request-scoped policy-pack identifier.",
            examples=["dpm_standard_v1"],
        ),
    ] = None,
    x_tenant_policy_pack_id: Annotated[
        Optional[str],
        Header(
            description="Optional tenant-default policy-pack identifier from upstream context.",
            examples=["dpm_tenant_default_v1"],
        ),
    ] = None,
    x_tenant_id: Annotated[
        Optional[str],
        Header(
            description="Optional tenant identifier used for tenant policy-pack default lookup.",
            examples=["tenant_001"],
        ),
    ] = None,
) -> DpmEffectivePolicyPackResolution:
    _reject_unexpected_query_params(request, allowed_params=set())
    return resolve_dpm_policy_pack(
        request_policy_pack_id=x_policy_pack_id,
        tenant_default_policy_pack_id=x_tenant_policy_pack_id,
        tenant_id=x_tenant_id,
    )


@router.get(
    "/rebalance/policies/catalog",
    response_model=DpmPolicyPackCatalogResponse,
    status_code=status.HTTP_200_OK,
    summary="List lotus-manage Policy Pack Catalog",
    description=(
        "Returns the currently configured lotus-manage policy-pack catalog and the effective "
        "selection context for optional request and tenant headers. Supply resolution context via "
        "the documented headers rather than query parameters."
    ),
    responses={
        422: {
            "description": "Unsupported query parameters were supplied.",
        },
    },
)
def get_dpm_policy_pack_catalog(
    request: Request,
    x_policy_pack_id: Annotated[
        Optional[str],
        Header(
            description="Optional request-scoped policy-pack identifier.",
            examples=["dpm_standard_v1"],
        ),
    ] = None,
    x_tenant_policy_pack_id: Annotated[
        Optional[str],
        Header(
            description="Optional tenant-default policy-pack identifier from upstream context.",
            examples=["dpm_tenant_default_v1"],
        ),
    ] = None,
    x_tenant_id: Annotated[
        Optional[str],
        Header(
            description="Optional tenant identifier used for tenant policy-pack default lookup.",
            examples=["tenant_001"],
        ),
    ] = None,
) -> DpmPolicyPackCatalogResponse:
    _reject_unexpected_query_params(request, allowed_params=set())
    resolution = resolve_dpm_policy_pack(
        request_policy_pack_id=x_policy_pack_id,
        tenant_default_policy_pack_id=x_tenant_policy_pack_id,
        tenant_id=x_tenant_id,
    )
    catalog = load_dpm_policy_pack_catalog()
    items = sorted(catalog.values(), key=lambda item: item.policy_pack_id)
    selected_policy_pack_id = resolution.selected_policy_pack_id
    return DpmPolicyPackCatalogResponse(
        enabled=resolution.enabled,
        total=len(items),
        selected_policy_pack_id=selected_policy_pack_id,
        selected_policy_pack_present=(
            selected_policy_pack_id is not None and selected_policy_pack_id in catalog
        ),
        selected_policy_pack_source=resolution.source,
        items=items,
    )


@router.get(
    "/rebalance/policies/catalog/{policy_pack_id}",
    response_model=DpmPolicyPackDefinition,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Policy Pack",
    description="Returns one policy-pack definition by identifier.",
)
def get_dpm_policy_pack(
    policy_pack_id: Annotated[
        str,
        Path(
            description="Policy-pack identifier.",
            examples=["dpm_standard_v1"],
        ),
    ],
) -> DpmPolicyPackDefinition:
    repository = _get_policy_pack_repository()
    policy_pack = repository.get_policy_pack(policy_pack_id=policy_pack_id)
    if policy_pack is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="DPM_POLICY_PACK_NOT_FOUND"
        )
    return policy_pack


@router.put(
    "/rebalance/policies/catalog/{policy_pack_id}",
    response_model=DpmPolicyPackMutationResponse,
    status_code=status.HTTP_200_OK,
    summary="Upsert lotus-manage Policy Pack",
    description="Creates or updates one policy-pack definition by identifier.",
)
def upsert_dpm_policy_pack(
    policy_pack_id: Annotated[
        str,
        Path(
            description="Policy-pack identifier.",
            examples=["dpm_standard_v2"],
        ),
    ],
    request: DpmPolicyPackUpsertRequest,
) -> DpmPolicyPackMutationResponse:
    _assert_policy_pack_admin_apis_enabled()
    repository = _get_policy_pack_repository()
    policy_pack = DpmPolicyPackDefinition(
        policy_pack_id=policy_pack_id,
        version=request.version,
        turnover_policy=request.turnover_policy,
        tax_policy=request.tax_policy,
        settlement_policy=request.settlement_policy,
        constraint_policy=request.constraint_policy,
        workflow_policy=request.workflow_policy,
        idempotency_policy=request.idempotency_policy,
    )
    repository.upsert_policy_pack(policy_pack)
    return DpmPolicyPackMutationResponse(item=policy_pack)


@router.delete(
    "/rebalance/policies/catalog/{policy_pack_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete lotus-manage Policy Pack",
    description="Deletes one policy-pack definition by identifier when it exists.",
)
def delete_dpm_policy_pack(
    policy_pack_id: Annotated[
        str,
        Path(
            description="Policy-pack identifier.",
            examples=["dpm_standard_v2"],
        ),
    ],
) -> None:
    _assert_policy_pack_admin_apis_enabled()
    repository = _get_policy_pack_repository()
    deleted = repository.delete_policy_pack(policy_pack_id=policy_pack_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="DPM_POLICY_PACK_NOT_FOUND"
        )
