from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import get_pm_quality_policy_repository
from src.api.routers.pm_operating_quality_models import DpmPmOperatingQualityPolicyListResponse
from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmQualityPolicyConflictError,
    DpmPmQualityPolicyRepository,
)


router = APIRouter()


@router.put(
    "/policies/{policy_id}/versions/{policy_version}",
    response_model=DpmPmOperatingQualityPolicy,
    status_code=status.HTTP_200_OK,
    summary="Persist PM operating quality policy version",
    description=(
        "What: Persist an immutable PM operating quality policy version for later score-run "
        "preview and creation.\n"
        "When: Use after a bank has approved a governed PM operating-quality policy and wants "
        "auditable policy reuse.\n"
        "How: The path id/version must match the policy body. Re-saving identical content is "
        "idempotent; changing an existing version is rejected. This route administers policy "
        "configuration only; it does not materialize PM books, rank PMs, decide compensation, "
        "perform conduct enforcement, or calculate source-owned risk/performance/tax facts."
    ),
)
def put_pm_operating_quality_policy_endpoint(
    policy_id: str,
    policy_version: str,
    policy: DpmPmOperatingQualityPolicy,
    repository: DpmPmQualityPolicyRepository = Depends(get_pm_quality_policy_repository),
) -> DpmPmOperatingQualityPolicy:
    if policy.policy_id != policy_id or policy.policy_version != policy_version:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="PM_QUALITY_POLICY_PATH_BODY_MISMATCH",
        )
    try:
        repository.save_policy(policy=policy)
    except DpmPmQualityPolicyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return policy


@router.get(
    "/policies",
    response_model=DpmPmOperatingQualityPolicyListResponse,
    status_code=status.HTTP_200_OK,
    summary="List persisted PM operating quality policies",
    description=(
        "What: Return a bounded page of persisted PM operating quality policy versions.\n"
        "When: Use for governance review, bank policy selection, and score-run preparation.\n"
        "How: Filter by policy id, enabled state, or as-of date. The response returns stored "
        "policy configuration only and does not compute PM scores."
    ),
)
def list_pm_operating_quality_policies_endpoint(
    policy_id: Annotated[str | None, Query(description="Filter by policy id.")] = None,
    enabled: Annotated[bool | None, Query(description="Filter by policy enabled flag.")] = None,
    as_of_date: Annotated[str | None, Query(description="Filter by policy as-of date.")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum rows to return.")] = 50,
    offset: Annotated[int, Query(ge=0, description="Rows to skip.")] = 0,
    repository: DpmPmQualityPolicyRepository = Depends(get_pm_quality_policy_repository),
) -> DpmPmOperatingQualityPolicyListResponse:
    policies = repository.list_policies(
        policy_id=policy_id,
        enabled=enabled,
        as_of_date=as_of_date,
        limit=limit,
        offset=offset,
    )
    return DpmPmOperatingQualityPolicyListResponse(
        policies=policies,
        count=len(policies),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/policies/{policy_id}/versions/{policy_version}",
    response_model=DpmPmOperatingQualityPolicy,
    status_code=status.HTTP_200_OK,
    summary="Get persisted PM operating quality policy version",
    description=(
        "What: Return one persisted PM operating quality policy version.\n"
        "When: Use for audit, supportability review, and score-run preparation.\n"
        "How: The endpoint returns immutable stored policy configuration and does not compute "
        "PM scores or source-owned facts."
    ),
)
def get_pm_operating_quality_policy_endpoint(
    policy_id: str,
    policy_version: str,
    repository: DpmPmQualityPolicyRepository = Depends(get_pm_quality_policy_repository),
) -> DpmPmOperatingQualityPolicy:
    policy = repository.get_policy(policy_id=policy_id, policy_version=policy_version)
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PM_QUALITY_POLICY_NOT_FOUND:{policy_id}:{policy_version}",
        )
    return policy
