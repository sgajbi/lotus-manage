from __future__ import annotations

from dataclasses import dataclass

from fastapi import Body, Request

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


@dataclass(frozen=True)
class PmQualityTrustedScoreRunRequest:
    request: DpmPmOperatingQualityScorePreviewRequest
    identity: PmQualityTrustedIdentity


@dataclass(frozen=True)
class PmQualityTrustedFairnessRequest:
    request: DpmPmQualityFairnessPreviewRequest
    identity: PmQualityTrustedIdentity


@dataclass(frozen=True)
class PmQualityTrustedReviewActionRequest:
    request: DpmPmQualityReviewActionRequest
    identity: PmQualityTrustedIdentity


@dataclass(frozen=True)
class PmQualityTrustedSummaryInvocationRequest:
    request: DpmPmQualitySummaryInvocationRequest
    identity: PmQualityTrustedIdentity


def pm_quality_trusted_identity_required(request: Request) -> PmQualityTrustedIdentity:
    identity = _trusted_identity_from_request(request)
    if not identity.actor_id:
        raise _trusted_identity_problem("PM_QUALITY_TRUSTED_ACTOR_REQUIRED")
    if not identity.tenant_id:
        raise _trusted_identity_problem("PM_QUALITY_TRUSTED_TENANT_REQUIRED")
    if not identity.role:
        raise _trusted_identity_problem("PM_QUALITY_TRUSTED_ROLE_REQUIRED")
    return identity


def assert_pm_quality_actor_matches_trusted_identity(
    *,
    request: Request,
    actor_id: str,
    tenant_id: str | None = None,
) -> PmQualityTrustedIdentity:
    identity = pm_quality_trusted_identity_required(request)
    if actor_id.strip() != identity.actor_id:
        raise _trusted_identity_problem("PM_QUALITY_TRUSTED_ACTOR_MISMATCH")
    if tenant_id is not None and tenant_id.strip() != identity.tenant_id:
        raise _trusted_identity_problem("PM_QUALITY_TRUSTED_TENANT_MISMATCH")
    return identity


def score_run_request_with_trusted_identity(
    http_request: Request,
    request: DpmPmOperatingQualityScorePreviewRequest = Body(...),
) -> PmQualityTrustedScoreRunRequest:
    identity = assert_pm_quality_actor_matches_trusted_identity(
        request=http_request,
        actor_id=request.actor_id,
        tenant_id=(request.pm_book_scope.tenant_id if request.pm_book_scope is not None else None),
    )
    return PmQualityTrustedScoreRunRequest(request=request, identity=identity)


def fairness_request_with_trusted_identity(
    http_request: Request,
    request: DpmPmQualityFairnessPreviewRequest = Body(...),
) -> PmQualityTrustedFairnessRequest:
    identity = assert_pm_quality_actor_matches_trusted_identity(
        request=http_request,
        actor_id=request.actor_id,
    )
    return PmQualityTrustedFairnessRequest(request=request, identity=identity)


def review_action_request_with_trusted_identity(
    http_request: Request,
    request: DpmPmQualityReviewActionRequest = Body(...),
) -> PmQualityTrustedReviewActionRequest:
    identity = assert_pm_quality_actor_matches_trusted_identity(
        request=http_request,
        actor_id=request.actor_id,
    )
    return PmQualityTrustedReviewActionRequest(request=request, identity=identity)


def summary_invocation_request_with_trusted_identity(
    http_request: Request,
    request: DpmPmQualitySummaryInvocationRequest = Body(...),
) -> PmQualityTrustedSummaryInvocationRequest:
    identity = assert_pm_quality_actor_matches_trusted_identity(
        request=http_request,
        actor_id=request.requested_by,
    )
    return PmQualityTrustedSummaryInvocationRequest(request=request, identity=identity)


def _trusted_identity_from_request(request: Request) -> PmQualityTrustedIdentity:
    return PmQualityTrustedIdentity(
        actor_id=request.headers.get("X-Actor-Id", "").strip(),
        tenant_id=request.headers.get("X-Tenant-Id", "").strip(),
        role=request.headers.get("X-Role", "").strip(),
    )


def _trusted_identity_problem(reason_code: str) -> PmQualityProblemDetailsException:
    return pm_quality_authorization_http_exception(reason_code=reason_code)
