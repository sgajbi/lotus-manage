from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from fastapi import HTTPException, status

from src.api.routers.pm_operating_quality_http import (
    pm_quality_core_resolver_incomplete_http_exception,
    pm_quality_core_resolver_unavailable_http_exception,
    pm_quality_pm_book_membership_empty_http_exception,
    pm_quality_pm_book_membership_not_ready_http_exception,
)
from src.api.routers.pm_operating_quality_models import (
    DpmPmOperatingQualityPmBookScopeRequest,
    DpmPmOperatingQualityScorePreviewRequest,
)
from src.core.dpm_source_context import DpmCorePortfolioManagerBookMembershipResponse
from src.core.outcomes import DpmOutcomeSourceRef
from src.core.pm_quality import (
    DpmPmQualityBookScopeEvidence,
    DpmPmQualityEvidenceItem,
)
from src.core.pm_quality.book_scope_refs import pm_book_member_source_refs
from src.core.pm_quality.temporal import canonical_pm_quality_business_date
from src.api.services.core_resolver_service import (
    CoreResolverError,
    CoreResolverUnavailableError,
)


def resolve_pm_book_scope_evidence(
    *,
    request: DpmPmOperatingQualityScorePreviewRequest,
    scope: DpmPmOperatingQualityPmBookScopeRequest,
    correlation_id: str,
    core_resolver_factory: Callable[[], Any],
) -> DpmPmQualityBookScopeEvidence:
    as_of_date = _parse_pm_book_scope_preview_as_of_date(request.as_of_date)
    membership = _resolve_pm_book_membership_for_preview(
        request=request,
        scope=scope,
        as_of_date=as_of_date,
        correlation_id=correlation_id,
        core_resolver_factory=core_resolver_factory,
    )
    _validate_pm_book_membership_for_preview(membership)
    return _pm_book_scope_evidence_from_membership(membership)


def _parse_pm_book_scope_preview_as_of_date(as_of_date: str) -> date:
    try:
        return date.fromisoformat(
            canonical_pm_quality_business_date(as_of_date, field_name="as_of_date")
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="INVALID_AS_OF_DATE",
        ) from exc


def _resolve_pm_book_membership_for_preview(
    *,
    request: DpmPmOperatingQualityScorePreviewRequest,
    scope: DpmPmOperatingQualityPmBookScopeRequest,
    as_of_date: date,
    correlation_id: str,
    core_resolver_factory: Callable[[], Any],
) -> DpmCorePortfolioManagerBookMembershipResponse:
    try:
        membership = core_resolver_factory().resolve_portfolio_manager_book_membership(
            portfolio_manager_id=request.pm_id,
            as_of_date=as_of_date,
            tenant_id=scope.tenant_id,
            booking_center_code=scope.booking_center_code,
            portfolio_types=scope.portfolio_types,
            include_inactive=scope.include_inactive,
            correlation_id=correlation_id,
        )
        return DpmCorePortfolioManagerBookMembershipResponse.model_validate(membership)
    except CoreResolverUnavailableError as exc:
        raise pm_quality_core_resolver_unavailable_http_exception(exc) from exc
    except CoreResolverError as exc:
        raise pm_quality_core_resolver_incomplete_http_exception(exc) from exc


def _validate_pm_book_membership_for_preview(
    membership: DpmCorePortfolioManagerBookMembershipResponse,
) -> None:
    if membership.supportability.state != "READY":
        raise pm_quality_pm_book_membership_not_ready_http_exception(membership)
    if not membership.members:
        raise pm_quality_pm_book_membership_empty_http_exception()


def _pm_book_scope_source_id(
    membership: DpmCorePortfolioManagerBookMembershipResponse,
) -> str:
    return (
        membership.snapshot_id
        or membership.source_batch_fingerprint
        or f"pm_book:{membership.portfolio_manager_id}:{membership.as_of_date.isoformat()}"
    )


def _pm_book_scope_source_ref(
    membership: DpmCorePortfolioManagerBookMembershipResponse,
    *,
    source_id: str,
) -> DpmOutcomeSourceRef:
    return DpmOutcomeSourceRef(
        source_system="lotus-core",
        source_type="PortfolioManagerBookMembership",
        source_id=source_id,
        source_version=membership.product_version,
        content_hash=membership.source_batch_fingerprint,
    )


def _pm_book_member_source_refs(
    membership: DpmCorePortfolioManagerBookMembershipResponse,
) -> list[DpmOutcomeSourceRef]:
    return pm_book_member_source_refs(membership)


def _pm_book_scope_evidence_from_membership(
    membership: DpmCorePortfolioManagerBookMembershipResponse,
) -> DpmPmQualityBookScopeEvidence:
    source_id = _pm_book_scope_source_id(membership)
    return DpmPmQualityBookScopeEvidence(
        source_id=source_id,
        product_version=membership.product_version,
        supportability_state=membership.supportability.state,
        returned_portfolio_count=len(membership.members),
        member_portfolio_ids=[member.portfolio_id for member in membership.members[:100]],
        filters_applied=membership.supportability.filters_applied,
        reason_codes=[
            "PM_BOOK_SCOPE_MATERIALIZED",
            membership.supportability.reason,
        ],
        source_refs=[
            _pm_book_scope_source_ref(membership, source_id=source_id),
            *_pm_book_member_source_refs(membership),
        ],
    )


def book_scope_signal(
    book_scope_evidence: DpmPmQualityBookScopeEvidence,
) -> DpmPmQualityEvidenceItem:
    return DpmPmQualityEvidenceItem(
        indicator="SOURCE_QUALITY",
        evidence_state="READY",
        score=None,
        source_system=book_scope_evidence.source_system,
        source_type=book_scope_evidence.source_type,
        source_id=book_scope_evidence.source_id,
        reason_codes=book_scope_evidence.reason_codes,
        source_refs=book_scope_evidence.source_refs,
    )
