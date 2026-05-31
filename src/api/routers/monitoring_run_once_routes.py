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
from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import DpmMonitoringRun
from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError


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
        if not request.portfolio_manager_id:
            raise monitoring_selector_required_http_exception()
        portfolio_types = [
            portfolio_type.strip().upper()
            for portfolio_type in request.portfolio_types
            if portfolio_type.strip()
        ]
        if not portfolio_types:
            raise monitoring_pm_book_portfolio_types_required_http_exception()
        try:
            membership = monitoring_router.get_core_resolver_client().resolve_portfolio_manager_book_membership(
                portfolio_manager_id=request.portfolio_manager_id,
                as_of_date=request.as_of_date,
                tenant_id=request.tenant_id,
                booking_center_code=request.booking_center_code,
                portfolio_types=portfolio_types,
                include_inactive=False,
                correlation_id=None,
            )
        except DpmCoreResolverUnavailableError as exc:
            raise monitoring_core_resolver_unavailable_http_exception(exc) from exc
        except DpmCoreResolverError as exc:
            raise monitoring_core_resolver_incomplete_http_exception(exc) from exc
        if membership.supportability.state != "READY":
            raise monitoring_pm_book_membership_not_ready_http_exception(membership)
        if not membership.members:
            raise monitoring_pm_book_membership_empty_http_exception()
        try:
            mandate_ids = mandate_ids_from_pm_book_membership(
                repository=repository,
                membership=membership,
            )
        except DpmMandateSourceIncompleteError as exc:
            raise monitoring_pm_book_mandate_snapshot_incomplete_http_exception(exc) from exc
        source_filters = {
            "source_product": membership.product_name,
            "source_product_version": membership.product_version,
            "source_supportability_state": membership.supportability.state,
        }
        if membership.snapshot_id:
            source_filters["source_snapshot_id"] = membership.snapshot_id
        if membership.source_batch_fingerprint:
            source_filters["source_content_hash"] = membership.source_batch_fingerprint

    return read_mandate_with_not_found_http_mapping(
        lambda: run_mandate_monitoring_once(
            repository=repository,
            mandate_ids=mandate_ids,
            as_of_date=request.as_of_date,
            filters=_monitoring_run_filters(
                request=request,
                source_filters=source_filters,
            ),
        )
    )


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
