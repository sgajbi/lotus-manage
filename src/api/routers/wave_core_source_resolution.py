from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from src.api.routers.wave_cio_model_change_projection import (
    build_cio_model_change_resolved_portfolios,
)
from src.api.routers.wave_date_validation import parse_wave_as_of_date
from src.api.routers.wave_pm_book_projection import build_pm_book_resolved_portfolios
from src.api.routers.wave_portfolio_type_validation import (
    normalize_required_portfolio_types,
)
from src.api.routers.wave_request_models import DpmWavePreviewRequest
from src.api.routers.wave_required_text_validation import normalize_required_text
from src.api.routers.wave_source_dependency_http import (
    source_dependency_failed_http_exception,
    upstream_dependency_failed_http_exception,
    upstream_unavailable_http_exception,
)
from src.api.services import wave_service
from src.api.services.core_resolver_service import (
    CoreResolverError,
    CoreResolverUnavailableError,
)


CoreResolverFactory = Callable[[], Any]


@dataclass(frozen=True)
class _PmBookMembershipRequest:
    portfolio_manager_id: str
    as_of_date: date
    tenant_id: str | None
    booking_center_code: str | None
    portfolio_types: list[str]


@dataclass(frozen=True)
class _CioModelChangeCohortRequest:
    model_portfolio_id: str
    as_of_date: date
    tenant_id: str | None
    booking_center_code: str | None


def resolve_pm_book_portfolios(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
    core_resolver_factory: CoreResolverFactory,
) -> list[dict[str, object]]:
    membership_request = _pm_book_membership_request_for_wave(request)
    membership = _resolve_pm_book_membership(
        core_resolver_factory=core_resolver_factory,
        membership_request=membership_request,
        correlation_id=correlation_id,
    )
    _require_pm_book_membership_ready(membership)
    return build_pm_book_resolved_portfolios(membership)


def _pm_book_membership_request_for_wave(
    request: DpmWavePreviewRequest,
) -> _PmBookMembershipRequest:
    if request.portfolios:
        raise wave_service.DpmWaveValidationError(
            "PM_BOOK_REVIEW_REJECTS_CALLER_PORTFOLIOS",
            "PM_BOOK_REVIEW resolves the affected portfolio set from lotus-core.",
        )
    portfolio_manager_id = normalize_required_text(
        request.portfolio_manager_id,
        required_code="PM_BOOK_REVIEW_PORTFOLIO_MANAGER_REQUIRED",
        required_message="PM_BOOK_REVIEW requires portfolio_manager_id.",
    )
    as_of_date = parse_wave_as_of_date(request.as_of_date)
    portfolio_types = normalize_required_portfolio_types(
        request.portfolio_types,
        required_code="PM_BOOK_REVIEW_PORTFOLIO_TYPES_REQUIRED",
        required_message="PM_BOOK_REVIEW requires at least one portfolio type.",
    )
    return _PmBookMembershipRequest(
        portfolio_manager_id=portfolio_manager_id,
        as_of_date=as_of_date,
        tenant_id=request.tenant_id,
        booking_center_code=request.booking_center_code,
        portfolio_types=portfolio_types,
    )


def _resolve_pm_book_membership(
    *,
    core_resolver_factory: CoreResolverFactory,
    membership_request: _PmBookMembershipRequest,
    correlation_id: str,
) -> Any:
    try:
        return core_resolver_factory().resolve_portfolio_manager_book_membership(
            portfolio_manager_id=membership_request.portfolio_manager_id,
            as_of_date=membership_request.as_of_date,
            tenant_id=membership_request.tenant_id,
            booking_center_code=membership_request.booking_center_code,
            portfolio_types=membership_request.portfolio_types,
            include_inactive=False,
            correlation_id=correlation_id,
        )
    except CoreResolverUnavailableError as exc:
        raise upstream_unavailable_http_exception(
            exc,
            default_code="DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE",
        ) from exc
    except CoreResolverError as exc:
        raise upstream_dependency_failed_http_exception(
            exc,
            default_code="DPM_CORE_PM_BOOK_MEMBERSHIP_INCOMPLETE",
        ) from exc


def _require_pm_book_membership_ready(membership: Any) -> None:
    if membership.supportability.state != "READY":
        raise source_dependency_failed_http_exception(
            code=membership.supportability.reason,
            message="PM-book membership is not source-ready.",
        )
    if not membership.members:
        raise source_dependency_failed_http_exception(
            code="DPM_CORE_PM_BOOK_MEMBERSHIP_EMPTY",
            message="PM-book membership returned no affected portfolios.",
        )


def resolve_cio_model_change_portfolios(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
    core_resolver_factory: CoreResolverFactory,
) -> list[dict[str, object]]:
    cohort_request = _cio_model_change_cohort_request_for_wave(request)
    cohort = _resolve_cio_model_change_cohort(
        core_resolver_factory=core_resolver_factory,
        cohort_request=cohort_request,
        correlation_id=correlation_id,
    )
    _require_cio_model_change_cohort_ready(cohort)
    return build_cio_model_change_resolved_portfolios(cohort)


def _cio_model_change_cohort_request_for_wave(
    request: DpmWavePreviewRequest,
) -> _CioModelChangeCohortRequest:
    if request.portfolios:
        raise wave_service.DpmWaveValidationError(
            "CIO_MODEL_CHANGE_REJECTS_CALLER_PORTFOLIOS",
            "CIO_MODEL_CHANGE resolves the affected portfolio set from lotus-core.",
        )
    model_portfolio_id = normalize_required_text(
        request.model_portfolio_id,
        required_code="CIO_MODEL_CHANGE_MODEL_PORTFOLIO_REQUIRED",
        required_message="CIO_MODEL_CHANGE requires model_portfolio_id.",
    )
    return _CioModelChangeCohortRequest(
        model_portfolio_id=model_portfolio_id,
        as_of_date=parse_wave_as_of_date(request.as_of_date),
        tenant_id=request.tenant_id,
        booking_center_code=request.booking_center_code,
    )


def _resolve_cio_model_change_cohort(
    *,
    core_resolver_factory: CoreResolverFactory,
    cohort_request: _CioModelChangeCohortRequest,
    correlation_id: str,
) -> Any:
    try:
        return core_resolver_factory().resolve_cio_model_change_affected_cohort(
            model_portfolio_id=cohort_request.model_portfolio_id,
            as_of_date=cohort_request.as_of_date,
            tenant_id=cohort_request.tenant_id,
            booking_center_code=cohort_request.booking_center_code,
            include_inactive_mandates=False,
            correlation_id=correlation_id,
        )
    except CoreResolverUnavailableError as exc:
        raise upstream_unavailable_http_exception(
            exc,
            default_code="DPM_CORE_CIO_MODEL_CHANGE_COHORT_UNAVAILABLE",
        ) from exc
    except CoreResolverError as exc:
        raise upstream_dependency_failed_http_exception(
            exc,
            default_code="DPM_CORE_CIO_MODEL_CHANGE_COHORT_INCOMPLETE",
        ) from exc


def _require_cio_model_change_cohort_ready(cohort: Any) -> None:
    if cohort.supportability.state != "READY":
        raise source_dependency_failed_http_exception(
            code=cohort.supportability.reason,
            message="CIO model-change affected cohort is not source-ready.",
        )
    if not cohort.affected_mandates:
        raise source_dependency_failed_http_exception(
            code="DPM_CORE_CIO_MODEL_CHANGE_COHORT_EMPTY",
            message="CIO model-change affected cohort returned no portfolios.",
        )
