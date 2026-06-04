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
from src.core.outcomes import DpmOutcomeSourceRef
from src.core.pm_quality import (
    DpmPmQualityBookScopeEvidence,
    DpmPmQualityEvidenceItem,
)
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
    try:
        as_of_date = date.fromisoformat(request.as_of_date)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="INVALID_AS_OF_DATE",
        ) from exc
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
    except CoreResolverUnavailableError as exc:
        raise pm_quality_core_resolver_unavailable_http_exception(exc) from exc
    except CoreResolverError as exc:
        raise pm_quality_core_resolver_incomplete_http_exception(exc) from exc

    if membership.supportability.state != "READY":
        raise pm_quality_pm_book_membership_not_ready_http_exception(membership)
    if not membership.members:
        raise pm_quality_pm_book_membership_empty_http_exception()

    source_id = (
        membership.snapshot_id
        or membership.source_batch_fingerprint
        or f"pm_book:{membership.portfolio_manager_id}:{membership.as_of_date.isoformat()}"
    )
    book_ref = DpmOutcomeSourceRef(
        source_system="lotus-core",
        source_type="PortfolioManagerBookMembership",
        source_id=source_id,
        source_version=membership.product_version,
        content_hash=membership.source_batch_fingerprint,
    )
    member_refs = [
        DpmOutcomeSourceRef(
            source_system="lotus-core",
            source_type="PORTFOLIO_MANAGER_BOOK_MEMBER",
            source_id=member.source_record_id or member.portfolio_id,
            source_version=membership.as_of_date.isoformat(),
        )
        for member in membership.members[:100]
    ]
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
        source_refs=[book_ref, *member_refs],
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
