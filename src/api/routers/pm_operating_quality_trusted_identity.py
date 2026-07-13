from __future__ import annotations

from dataclasses import dataclass

from fastapi import Body, Request

from src.api.enterprise_readiness import write_authorization_required
from src.api.routers.pm_operating_quality_http import (
    PmQualityProblemDetailsException,
    pm_quality_authorization_http_exception,
)
from src.api.routers.pm_operating_quality_models import (
    DpmPmOperatingQualityScorePreviewRequest,
    DpmPmQualityFairnessPreviewRequest,
    DpmPmQualityReviewActionRequest,
    DpmPmQualitySummaryInvocationRequest,
)


@dataclass(frozen=True)
class PmQualityTrustedIdentity:
    actor_id: str
    tenant_id: str
    role: str


def assert_pm_quality_actor_matches_trusted_identity(
    *,
    request: Request,
    actor_id: str,
    tenant_id: str | None = None,
) -> PmQualityTrustedIdentity | None:
    if not write_authorization_required(request.method):
        return None
    identity = _trusted_identity_from_request(request)
    if actor_id.strip() != identity.actor_id:
        raise _trusted_identity_problem("PM_QUALITY_TRUSTED_ACTOR_MISMATCH")
    if tenant_id is not None and tenant_id.strip() != identity.tenant_id:
        raise _trusted_identity_problem("PM_QUALITY_TRUSTED_TENANT_MISMATCH")
    return identity


def score_run_request_with_trusted_identity(
    http_request: Request,
    request: DpmPmOperatingQualityScorePreviewRequest = Body(...),
) -> DpmPmOperatingQualityScorePreviewRequest:
    assert_pm_quality_actor_matches_trusted_identity(
        request=http_request,
        actor_id=request.actor_id,
        tenant_id=(request.pm_book_scope.tenant_id if request.pm_book_scope is not None else None),
    )
    return request


def fairness_request_with_trusted_identity(
    http_request: Request,
    request: DpmPmQualityFairnessPreviewRequest = Body(...),
) -> DpmPmQualityFairnessPreviewRequest:
    assert_pm_quality_actor_matches_trusted_identity(
        request=http_request,
        actor_id=request.actor_id,
    )
    return request


def review_action_request_with_trusted_identity(
    http_request: Request,
    request: DpmPmQualityReviewActionRequest = Body(...),
) -> DpmPmQualityReviewActionRequest:
    assert_pm_quality_actor_matches_trusted_identity(
        request=http_request,
        actor_id=request.actor_id,
    )
    return request


def summary_invocation_request_with_trusted_identity(
    http_request: Request,
    request: DpmPmQualitySummaryInvocationRequest = Body(...),
) -> DpmPmQualitySummaryInvocationRequest:
    assert_pm_quality_actor_matches_trusted_identity(
        request=http_request,
        actor_id=request.requested_by,
    )
    return request


def _trusted_identity_from_request(request: Request) -> PmQualityTrustedIdentity:
    return PmQualityTrustedIdentity(
        actor_id=request.headers.get("X-Actor-Id", "").strip(),
        tenant_id=request.headers.get("X-Tenant-Id", "").strip(),
        role=request.headers.get("X-Role", "").strip(),
    )


def _trusted_identity_problem(reason_code: str) -> PmQualityProblemDetailsException:
    return pm_quality_authorization_http_exception(reason_code=reason_code)
