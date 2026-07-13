from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_pm_quality_policy_application_service
from src.api.routers.pm_operating_quality_http import (
    pm_quality_conflict_http_exception,
    pm_quality_service_http_exception,
)
from src.api.routers.pm_operating_quality_models import DpmPmOperatingQualityPolicyListResponse
from src.api.routers.pm_operating_quality_temporal_filters import pm_quality_as_of_date_filter
from src.api.routers.pm_operating_quality_trusted_identity import (
    PmQualityTrustedIdentity,
    pm_quality_trusted_identity_required,
)
from src.api.services.pm_operating_quality_service import (
    DpmPmOperatingQualityApplicationService,
    DpmPmOperatingQualityServiceError,
)
from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmQualityPolicyConflictError,
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
    application_service: DpmPmOperatingQualityApplicationService = Depends(
        get_pm_quality_policy_application_service
    ),
    identity: PmQualityTrustedIdentity = Depends(pm_quality_trusted_identity_required),
) -> DpmPmOperatingQualityPolicy:
    try:
        return application_service.save_policy(
            tenant_id=identity.tenant_id,
            policy_id=policy_id,
            policy_version=policy_version,
            policy=policy,
        )
    except DpmPmQualityPolicyConflictError as exc:
        raise pm_quality_conflict_http_exception(exc) from exc
    except DpmPmOperatingQualityServiceError as exc:
        raise pm_quality_service_http_exception(exc) from exc


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
    as_of_date: Annotated[str | None, Depends(pm_quality_as_of_date_filter)] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum rows to return.")] = 50,
    offset: Annotated[int, Query(ge=0, description="Rows to skip.")] = 0,
    application_service: DpmPmOperatingQualityApplicationService = Depends(
        get_pm_quality_policy_application_service
    ),
    identity: PmQualityTrustedIdentity = Depends(pm_quality_trusted_identity_required),
) -> DpmPmOperatingQualityPolicyListResponse:
    policies = application_service.list_policies(
        tenant_id=identity.tenant_id,
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
    application_service: DpmPmOperatingQualityApplicationService = Depends(
        get_pm_quality_policy_application_service
    ),
    identity: PmQualityTrustedIdentity = Depends(pm_quality_trusted_identity_required),
) -> DpmPmOperatingQualityPolicy:
    try:
        return application_service.get_policy(
            tenant_id=identity.tenant_id,
            policy_id=policy_id,
            policy_version=policy_version,
        )
    except DpmPmOperatingQualityServiceError as exc:
        raise pm_quality_service_http_exception(exc) from exc
