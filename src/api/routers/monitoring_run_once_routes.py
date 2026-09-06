from __future__ import annotations

from fastapi import Depends

from src.api.dependencies import get_mandate_repository
from src.api.routers import monitoring as monitoring_router
from src.api.routers.mandate_http import read_mandate_with_not_found_http_mapping
from src.api.routers.monitoring_http import (
    monitoring_core_resolver_incomplete_http_exception,
    monitoring_core_resolver_unavailable_http_exception,
    monitoring_pm_book_mandate_snapshot_incomplete_http_exception,
    monitoring_pm_book_membership_empty_http_exception,
    monitoring_pm_book_membership_not_ready_http_exception,
    monitoring_pm_book_portfolio_types_required_http_exception,
    monitoring_selector_required_http_exception,
)
from src.api.routers.monitoring_models import DpmMonitoringRunOnceRequest
from src.api.services.mandate_service import (
    DpmMandateSourceIncompleteError,
    mandate_ids_from_pm_book_membership,
    run_mandate_monitoring_once,
)
from src.api.services.core_resolver_service import (
    CoreResolverError,
    CoreResolverUnavailableError,
)
from src.core.dpm_source_context import DpmCorePortfolioManagerBookMembershipResponse
from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import DpmMonitoringRun


@monitoring_router.router.post(
    "/monitoring/run-once",
    response_model=DpmMonitoringRun,
    summary="Run discretionary mandate monitoring once",
    description=(
        "Use this endpoint to evaluate a bounded set of existing mandate digital twins and persist "
        "a monitoring run, health snapshots, and derived exceptions. Callers may provide explicit "
        "mandate ids or omit them and provide a portfolio-manager selector so Manage resolves the "
        "PM-book cohort from lotus-core `PortfolioManagerBookMembership:v1`."
    ),
    responses={
        200: {"description": "Monitoring run completed and persisted."},
        404: {"description": "At least one requested mandate id was not found."},
    },
)
async def run_once(
    request: DpmMonitoringRunOnceRequest,
    repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmMonitoringRun:
    mandate_ids = list(request.mandate_ids)
    source_filters: dict[str, str] = {}
    if not mandate_ids:
        mandate_ids, source_filters = _mandate_ids_from_pm_book_selector(
            request=request,
            repository=repository,
        )

    return read_mandate_with_not_found_http_mapping(
        lambda: run_mandate_monitoring_once(
            repository=repository,
            tenant_id=request.tenant_id,
            mandate_ids=mandate_ids,
            as_of_date=request.as_of_date,
            filters=_monitoring_run_filters(
                request=request,
                source_filters=source_filters,
            ),
        )
    )


def _portfolio_types_from_request(request: DpmMonitoringRunOnceRequest) -> list[str]:
    return [
        portfolio_type.strip().upper()
        for portfolio_type in request.portfolio_types
        if portfolio_type.strip()
    ]


def _resolve_pm_book_membership(
    *,
    request: DpmMonitoringRunOnceRequest,
    portfolio_types: list[str],
) -> DpmCorePortfolioManagerBookMembershipResponse:
    try:
        return (
            monitoring_router.get_core_resolver_client().resolve_portfolio_manager_book_membership(
                portfolio_manager_id=request.portfolio_manager_id or "",
                as_of_date=request.as_of_date,
                tenant_id=request.tenant_id,
                booking_center_code=request.booking_center_code,
                portfolio_types=portfolio_types,
                include_inactive=False,
                correlation_id=None,
            )
        )
    except CoreResolverUnavailableError as exc:
        raise monitoring_core_resolver_unavailable_http_exception(exc) from exc
    except CoreResolverError as exc:
        raise monitoring_core_resolver_incomplete_http_exception(exc) from exc


def _pm_book_source_filters(
    membership: DpmCorePortfolioManagerBookMembershipResponse,
) -> dict[str, str]:
    source_filters = {
        "source_product": membership.product_name,
        "source_product_version": membership.product_version,
        "source_supportability_state": membership.supportability.state,
    }
    if membership.snapshot_id:
        source_filters["source_snapshot_id"] = membership.snapshot_id
    if membership.source_batch_fingerprint:
        source_filters["source_content_hash"] = membership.source_batch_fingerprint
    return source_filters


def _mandate_ids_from_pm_book_selector(
    *,
    request: DpmMonitoringRunOnceRequest,
    repository: DpmMandateRepository,
) -> tuple[list[str], dict[str, str]]:
    portfolio_types = _validated_pm_book_selector(request)
    membership = _resolve_pm_book_membership(request=request, portfolio_types=portfolio_types)
    _validate_pm_book_membership_ready(membership)
    mandate_ids = _mandate_ids_from_pm_book_membership(
        repository=repository,
        membership=membership,
        tenant_id=request.tenant_id,
    )
    return mandate_ids, _pm_book_source_filters(membership)


def _validated_pm_book_selector(request: DpmMonitoringRunOnceRequest) -> list[str]:
    if not request.portfolio_manager_id:
        raise monitoring_selector_required_http_exception()
    portfolio_types = _portfolio_types_from_request(request)
    if not portfolio_types:
        raise monitoring_pm_book_portfolio_types_required_http_exception()
    return portfolio_types


def _validate_pm_book_membership_ready(
    membership: DpmCorePortfolioManagerBookMembershipResponse,
) -> None:
    if membership.supportability.state != "READY":
        raise monitoring_pm_book_membership_not_ready_http_exception(membership)
    if not membership.members:
        raise monitoring_pm_book_membership_empty_http_exception()


def _mandate_ids_from_pm_book_membership(
    *,
    repository: DpmMandateRepository,
    membership: DpmCorePortfolioManagerBookMembershipResponse,
    tenant_id: str,
) -> list[str]:
    try:
        return mandate_ids_from_pm_book_membership(
            repository=repository,
            membership=membership,
            tenant_id=tenant_id,
        )
    except DpmMandateSourceIncompleteError as exc:
        raise monitoring_pm_book_mandate_snapshot_incomplete_http_exception(exc) from exc


def _monitoring_run_filters(
    *,
    request: DpmMonitoringRunOnceRequest,
    source_filters: dict[str, str],
) -> dict[str, str]:
    return {
        key: value
        for key, value in {
            "tenant_id": request.tenant_id,
            "portfolio_manager_id": request.portfolio_manager_id,
            "book_id": request.book_id,
            "booking_center_code": request.booking_center_code,
            "requested_by": request.requested_by,
            **source_filters,
        }.items()
        if value is not None
    }
