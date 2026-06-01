from __future__ import annotations

from src.api.routers.pm_operating_quality_http import (
    pm_quality_not_found_http_exception,
    pm_quality_validation_http_exception,
)
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
        raise pm_quality_validation_http_exception("PM_QUALITY_POLICY_REFERENCE_REQUIRED")
    policy = repository.get_policy(
        policy_id=request.policy_id,
        policy_version=request.policy_version,
    )
    if policy is None:
        raise pm_quality_not_found_http_exception(
            code="PM_QUALITY_POLICY_NOT_FOUND",
            identifier=request.policy_id,
            secondary_identifier=request.policy_version,
        )
    return policy
