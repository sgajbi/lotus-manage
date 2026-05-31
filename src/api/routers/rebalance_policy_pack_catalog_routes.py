from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Header, HTTPException, Path, Request, status

from src.api.routers.rebalance_policy_pack_docs import (
    POLICY_CATALOG_DESCRIPTION,
    POLICY_CATALOG_ITEM_DESCRIPTION,
    POLICY_CATALOG_ITEM_RESPONSES,
    POLICY_CATALOG_RESPONSES,
)
from src.api.routers.rebalance_policy_packs import (
    _get_policy_pack_repository,
    _record_policy_pack_api_resolution,
    _reject_unexpected_query_params,
    load_dpm_policy_pack_catalog,
    resolve_dpm_policy_pack,
    router,
)
from src.core.rebalance.policy_packs import (
    DpmPolicyPackCatalogResponse,
    DpmPolicyPackDefinition,
)


@router.get(
    "/rebalance/policies/catalog",
    response_model=DpmPolicyPackCatalogResponse,
    status_code=status.HTTP_200_OK,
    summary="List lotus-manage Policy Pack Catalog",
    description=POLICY_CATALOG_DESCRIPTION,
    responses=POLICY_CATALOG_RESPONSES,
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
    _record_policy_pack_api_resolution(resolution)
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
    description=POLICY_CATALOG_ITEM_DESCRIPTION,
    responses=POLICY_CATALOG_ITEM_RESPONSES,
)
def get_dpm_policy_pack(
    request: Request,
    policy_pack_id: Annotated[
        str,
        Path(
            description="Policy-pack identifier.",
            examples=["dpm_standard_v1"],
        ),
    ],
) -> DpmPolicyPackDefinition:
    _reject_unexpected_query_params(request, allowed_params=set())
    repository = _get_policy_pack_repository()
    policy_pack = repository.get_policy_pack(policy_pack_id=policy_pack_id)
    if policy_pack is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="DPM_POLICY_PACK_NOT_FOUND"
        )
    return policy_pack
