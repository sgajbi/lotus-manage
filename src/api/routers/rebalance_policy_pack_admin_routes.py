from __future__ import annotations

from typing import Annotated

from fastapi import HTTPException, Path, Request, status

from src.api.routers.rebalance_policy_pack_docs import (
    POLICY_CATALOG_DELETE_DESCRIPTION,
    POLICY_CATALOG_DELETE_RESPONSES,
    POLICY_CATALOG_UPSERT_DESCRIPTION,
    POLICY_CATALOG_UPSERT_RESPONSES,
)
from src.api.routers.rebalance_policy_packs import (
    _assert_policy_pack_admin_apis_enabled,
    _get_policy_pack_repository,
    _reject_unexpected_query_params,
    router,
)
from src.core.rebalance.policy_packs import (
    DpmPolicyPackDefinition,
    DpmPolicyPackMutationResponse,
    DpmPolicyPackUpsertRequest,
)


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
