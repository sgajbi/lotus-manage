from __future__ import annotations

from fastapi import HTTPException, status

from src.api.services.mandate_service import DpmMandateSourceIncompleteError
from src.core.dpm_source_context import DpmCorePortfolioManagerBookMembershipResponse
from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError


def monitoring_selector_required_http_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={
            "code": "DPM_MONITORING_SELECTOR_REQUIRED",
            "message": "Provide mandate_ids or portfolio_manager_id for PM-book discovery.",
        },
    )


def monitoring_pm_book_portfolio_types_required_http_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={
            "code": "DPM_MONITORING_PM_BOOK_PORTFOLIO_TYPES_REQUIRED",
            "message": "PM-book monitoring requires at least one portfolio type.",
        },
    )


def monitoring_core_resolver_unavailable_http_exception(
    exc: DpmCoreResolverUnavailableError,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"code": str(exc) or "DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE"},
    )


def monitoring_core_resolver_incomplete_http_exception(exc: DpmCoreResolverError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_424_FAILED_DEPENDENCY,
        detail={"code": str(exc) or "DPM_CORE_PM_BOOK_MEMBERSHIP_INCOMPLETE"},
    )


def monitoring_pm_book_membership_not_ready_http_exception(
    membership: DpmCorePortfolioManagerBookMembershipResponse,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_424_FAILED_DEPENDENCY,
        detail={
            "code": membership.supportability.reason,
            "message": "PM-book membership is not source-ready for monitoring.",
        },
    )


def monitoring_pm_book_membership_empty_http_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_424_FAILED_DEPENDENCY,
        detail={
            "code": "DPM_CORE_PM_BOOK_MEMBERSHIP_EMPTY",
            "message": "PM-book membership returned no mandates to monitor.",
        },
    )


def monitoring_pm_book_mandate_snapshot_incomplete_http_exception(
    exc: DpmMandateSourceIncompleteError,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_424_FAILED_DEPENDENCY,
        detail={"code": str(exc) or "DPM_PM_BOOK_MANDATE_SNAPSHOT_MISSING"},
    )
