from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.api.routers.wave_date_validation import parse_wave_as_of_date
from src.api.routers.wave_request_models import DpmWavePortfolioInput, DpmWavePreviewRequest
from src.api.routers.wave_source_dependency_http import (
    source_dependency_failed_http_exception,
    upstream_dependency_failed_http_exception,
    upstream_unavailable_http_exception,
)
from src.api.routers.wave_source_refs import (
    dpm_portfolio_universe_candidate_ref,
    dpm_portfolio_universe_ref,
)
from src.api.services import wave_service
from src.core.waves import DpmWaveSourceRef
from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError

MAX_CORE_DPM_PORTFOLIO_UNIVERSE_PAGES = 10


def resolve_core_dpm_portfolio_universe_candidates(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
    core_resolver_factory: Callable[[], Any],
) -> list[DpmWavePortfolioInput]:
    if request.portfolios:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_CORE_UNIVERSE_REJECTS_CALLER_PORTFOLIOS",
            "Core DPM portfolio-universe discovery supplies the candidate portfolio set.",
        )
    as_of_date = parse_wave_as_of_date(request.as_of_date)
    resolver = core_resolver_factory()
    candidate_pages: list[Any] = []
    next_page_token: str | None = None
    seen_page_tokens: set[str] = set()
    try:
        for _ in range(MAX_CORE_DPM_PORTFOLIO_UNIVERSE_PAGES):
            candidate_page = resolver.resolve_dpm_portfolio_universe_candidates(
                as_of_date=as_of_date,
                tenant_id=request.tenant_id,
                booking_center_code=request.booking_center_code,
                model_portfolio_ids=request.model_portfolio_ids,
                include_inactive_mandates=request.include_inactive_mandates,
                page_size=request.campaign_candidate_page_size,
                page_token=next_page_token,
                correlation_id=correlation_id,
            )
            candidate_pages.append(candidate_page)
            if candidate_page.supportability.state != "READY":
                break
            next_page_token = candidate_page.page.next_page_token
            if not next_page_token:
                break
            if next_page_token in seen_page_tokens:
                raise DpmCoreResolverError("DPM_CORE_PORTFOLIO_UNIVERSE_NON_TERMINATING")
            seen_page_tokens.add(next_page_token)
        else:
            raise DpmCoreResolverError("DPM_CORE_PORTFOLIO_UNIVERSE_NON_TERMINATING")
    except DpmCoreResolverUnavailableError as exc:
        raise upstream_unavailable_http_exception(
            exc,
            default_code="DPM_CORE_PORTFOLIO_UNIVERSE_UNAVAILABLE",
        ) from exc
    except DpmCoreResolverError as exc:
        raise upstream_dependency_failed_http_exception(
            exc,
            default_code="DPM_CORE_PORTFOLIO_UNIVERSE_INCOMPLETE",
        ) from exc

    candidate_page = candidate_pages[-1]
    if candidate_page.supportability.state != "READY":
        raise source_dependency_failed_http_exception(
            code=candidate_page.supportability.reason,
            message="Core DPM portfolio-universe candidates are not source-ready.",
        )
    if next_page_token or candidate_page.supportability.page_truncated:
        raise source_dependency_failed_http_exception(
            code="DPM_CORE_PORTFOLIO_UNIVERSE_PAGE_PARTIAL",
            message=(
                "Core DPM portfolio-universe candidates could not be exhausted within the "
                "bounded Manage consumer guard; refine filters before creating a campaign wave."
            ),
        )
    candidates = [candidate for page in candidate_pages for candidate in page.candidates]
    if not candidates:
        raise source_dependency_failed_http_exception(
            code="DPM_CORE_PORTFOLIO_UNIVERSE_EMPTY",
            message="Core DPM portfolio-universe discovery returned no candidate portfolios.",
        )
    candidate_keys: set[tuple[str, str | None, str | None]] = set()
    for candidate in candidates:
        candidate_key = (
            candidate.portfolio_id,
            candidate.mandate_id,
            candidate.source_record_id,
        )
        if candidate_key in candidate_keys:
            raise source_dependency_failed_http_exception(
                code="DPM_CORE_PORTFOLIO_UNIVERSE_DUPLICATE_CANDIDATE",
                message="Core DPM portfolio-universe discovery returned duplicate candidate rows.",
            )
        candidate_keys.add(candidate_key)

    first_page = candidate_pages[0]
    selection_basis = (
        first_page.selection_basis.model_dump(mode="json")
        if first_page.selection_basis is not None
        else None
    )
    universe_ref = dpm_portfolio_universe_ref(
        source_id=first_page.snapshot_id or first_page.page.request_scope_fingerprint,
        product_version=first_page.product_version,
        supportability_state=first_page.supportability.state,
        content_hash=first_page.source_batch_fingerprint,
    )
    return [
        DpmWavePortfolioInput(
            portfolio_id=candidate.portfolio_id,
            mandate_id=candidate.mandate_id,
            portfolio_type="DISCRETIONARY",
            source_refs=[
                DpmWaveSourceRef.model_validate(universe_ref),
                DpmWaveSourceRef.model_validate(
                    dpm_portfolio_universe_candidate_ref(
                        source_record_id=candidate.source_record_id,
                        portfolio_id=candidate.portfolio_id,
                        mandate_id=candidate.mandate_id,
                        binding_version=candidate.binding_version,
                        selection_basis=selection_basis,
                    )
                ),
            ],
        )
        for candidate in candidates
    ]
