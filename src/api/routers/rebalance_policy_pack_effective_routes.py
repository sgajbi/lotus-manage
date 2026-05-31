from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Header, Request, status

from src.api.routers.rebalance_policy_pack_docs import (
    POLICY_RESOLUTION_DESCRIPTION,
    POLICY_RESOLUTION_RESPONSES,
)
from src.api.routers.rebalance_policy_packs import (
    _record_policy_pack_api_resolution,
    _reject_unexpected_query_params,
    resolve_dpm_policy_pack,
    router,
)
from src.core.rebalance.policy_packs import DpmEffectivePolicyPackResolution


@router.get(
    "/rebalance/policies/effective",
    response_model=DpmEffectivePolicyPackResolution,
    status_code=status.HTTP_200_OK,
    summary="Resolve Effective lotus-manage Policy Pack",
    description=POLICY_RESOLUTION_DESCRIPTION,
    responses=POLICY_RESOLUTION_RESPONSES,
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
    resolution = resolve_dpm_policy_pack(
        request_policy_pack_id=x_policy_pack_id,
        tenant_default_policy_pack_id=x_tenant_policy_pack_id,
        tenant_id=x_tenant_id,
    )
    _record_policy_pack_api_resolution(resolution)
    return resolution
