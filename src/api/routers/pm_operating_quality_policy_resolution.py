from __future__ import annotations

from fastapi import HTTPException, status

from src.api.routers.pm_operating_quality_models import (
    DpmPmOperatingQualityScorePreviewRequest,
)
from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmQualityPolicyRepository,
)


def resolve_policy(
    *,
    request: DpmPmOperatingQualityScorePreviewRequest,
    repository: DpmPmQualityPolicyRepository,
) -> DpmPmOperatingQualityPolicy:
    if request.policy is not None:
        return request.policy
    if request.policy_id is None or request.policy_version is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="PM_QUALITY_POLICY_REFERENCE_REQUIRED",
        )
    policy = repository.get_policy(
        policy_id=request.policy_id,
        policy_version=request.policy_version,
    )
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PM_QUALITY_POLICY_NOT_FOUND:{request.policy_id}:{request.policy_version}",
        )
    return policy
