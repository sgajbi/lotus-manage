from __future__ import annotations

from collections.abc import Callable
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
from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError


CoreResolverFactory = Callable[[], Any]


def resolve_pm_book_portfolios(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
    core_resolver_factory: CoreResolverFactory,
) -> list[dict[str, object]]:
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
    try:
        membership = core_resolver_factory().resolve_portfolio_manager_book_membership(
            portfolio_manager_id=portfolio_manager_id,
            as_of_date=as_of_date,
            tenant_id=request.tenant_id,
            booking_center_code=request.booking_center_code,
            portfolio_types=portfolio_types,
            include_inactive=False,
            correlation_id=correlation_id,
        )
    except DpmCoreResolverUnavailableError as exc:
        raise upstream_unavailable_http_exception(
            exc,
            default_code="DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE",
        ) from exc
    except DpmCoreResolverError as exc:
        raise upstream_dependency_failed_http_exception(
            exc,
            default_code="DPM_CORE_PM_BOOK_MEMBERSHIP_INCOMPLETE",
        ) from exc
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
    return build_pm_book_resolved_portfolios(membership)


def resolve_cio_model_change_portfolios(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
    core_resolver_factory: CoreResolverFactory,
) -> list[dict[str, object]]:
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
    as_of_date = parse_wave_as_of_date(request.as_of_date)
    try:
        cohort = core_resolver_factory().resolve_cio_model_change_affected_cohort(
            model_portfolio_id=model_portfolio_id,
            as_of_date=as_of_date,
            tenant_id=request.tenant_id,
            booking_center_code=request.booking_center_code,
            include_inactive_mandates=False,
            correlation_id=correlation_id,
        )
    except DpmCoreResolverUnavailableError as exc:
        raise upstream_unavailable_http_exception(
            exc,
            default_code="DPM_CORE_CIO_MODEL_CHANGE_COHORT_UNAVAILABLE",
        ) from exc
    except DpmCoreResolverError as exc:
        raise upstream_dependency_failed_http_exception(
            exc,
            default_code="DPM_CORE_CIO_MODEL_CHANGE_COHORT_INCOMPLETE",
        ) from exc
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
    return build_cio_model_change_resolved_portfolios(cohort)
