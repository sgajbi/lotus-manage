from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from src.api.services.wave_errors import (
    DpmWaveDependencyFailedError,
    DpmWaveDependencyUnavailableError,
)
from src.core.dpm_source_context import (
    DpmCorePortfolioUniverseCandidate,
    DpmCorePortfolioUniverseCandidateResponse,
)
from src.core.waves import DpmWaveSourceRef
from src.infrastructure.core_sourcing import (
    DpmCoreResolverError,
    DpmCoreResolverUnavailableError,
)

CoreResolverFactory = Callable[[], Any]

MAX_CORE_DPM_PORTFOLIO_UNIVERSE_PAGES = 10


def _selection_basis_payload(
    page: DpmCorePortfolioUniverseCandidateResponse,
) -> dict[str, object] | None:
    if page.selection_basis is None:
        return None
    return page.selection_basis.model_dump(mode="json")


def _portfolio_universe_candidate_ref(
    *,
    candidate: DpmCorePortfolioUniverseCandidate,
    selection_basis: dict[str, object] | None,
) -> dict[str, object]:
    return DpmWaveSourceRef(
        source_system="lotus-core",
        source_type="DPM_PORTFOLIO_UNIVERSE_CANDIDATE",
        source_id=candidate.source_record_id or f"{candidate.portfolio_id}:{candidate.mandate_id}",
        source_version=str(candidate.binding_version),
        supportability_state="READY",
        selection_basis=selection_basis,
    ).model_dump(mode="json")


def _portfolio_universe_candidate_page_ref(
    *, page: DpmCorePortfolioUniverseCandidateResponse
) -> dict[str, object]:
    return DpmWaveSourceRef(
        source_system="lotus-core",
        source_type="DpmPortfolioUniverseCandidate",
        source_id=page.snapshot_id or page.page.request_scope_fingerprint,
        source_version=page.product_version,
        supportability_state=page.supportability.state,
        content_hash=page.source_batch_fingerprint,
    ).model_dump(mode="json")


def resolve_core_dpm_portfolio_universe_candidates(
    *,
    as_of_date: date,
    tenant_id: str | None,
    booking_center_code: str | None,
    model_portfolio_ids: list[str],
    include_inactive_mandates: bool,
    campaign_candidate_page_size: int,
    correlation_id: str,
    core_resolver_factory: CoreResolverFactory,
) -> list[dict[str, object]]:
    resolver = core_resolver_factory()
    candidate_pages: list[DpmCorePortfolioUniverseCandidateResponse] = []
    next_page_token: str | None = None
    seen_page_tokens: set[str] = set()

    try:
        for _ in range(MAX_CORE_DPM_PORTFOLIO_UNIVERSE_PAGES):
            candidate_page = resolver.resolve_dpm_portfolio_universe_candidates(
                as_of_date=as_of_date,
                tenant_id=tenant_id,
                booking_center_code=booking_center_code,
                model_portfolio_ids=model_portfolio_ids,
                include_inactive_mandates=include_inactive_mandates,
                page_size=campaign_candidate_page_size,
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
        raise DpmWaveDependencyUnavailableError(
            code=str(exc) or "DPM_CORE_PORTFOLIO_UNIVERSE_UNAVAILABLE"
        ) from exc
    except DpmCoreResolverError as exc:
        raise DpmWaveDependencyFailedError(
            code=str(exc) or "DPM_CORE_PORTFOLIO_UNIVERSE_INCOMPLETE"
        ) from exc

    candidate_page = candidate_pages[-1]
    if candidate_page.supportability.state != "READY":
        raise DpmWaveDependencyFailedError(
            code=candidate_page.supportability.reason,
            message="Core DPM portfolio-universe candidates are not source-ready.",
        )
    if next_page_token or candidate_page.supportability.page_truncated:
        raise DpmWaveDependencyFailedError(
            code="DPM_CORE_PORTFOLIO_UNIVERSE_PAGE_PARTIAL",
            message=(
                "Core DPM portfolio-universe candidates could not be exhausted within the "
                "bounded Manage consumer guard; refine filters before creating a campaign wave."
            ),
        )

    candidates = [candidate for page in candidate_pages for candidate in page.candidates]
    if not candidates:
        raise DpmWaveDependencyFailedError(
            code="DPM_CORE_PORTFOLIO_UNIVERSE_EMPTY",
            message="Core DPM portfolio-universe discovery returned no candidate portfolios.",
        )
    candidate_keys: set[tuple[str, str | None, str | None]] = set()
    first_page = candidate_pages[0]
    selection_basis = _selection_basis_payload(first_page)
    universe_ref = _portfolio_universe_candidate_page_ref(page=first_page)
    portfolios: list[dict[str, object]] = []

    for candidate in candidates:
        candidate_key = (
            candidate.portfolio_id,
            candidate.mandate_id,
            candidate.source_record_id,
        )
        if candidate_key in candidate_keys:
            raise DpmWaveDependencyFailedError(
                code="DPM_CORE_PORTFOLIO_UNIVERSE_DUPLICATE_CANDIDATE",
                message="Core DPM portfolio-universe discovery returned duplicate candidate rows.",
            )
        candidate_keys.add(candidate_key)
        portfolios.append(
            {
                "portfolio_id": candidate.portfolio_id,
                "mandate_id": candidate.mandate_id,
                "source_refs": [
                    universe_ref,
                    _portfolio_universe_candidate_ref(
                        candidate=candidate, selection_basis=selection_basis
                    ),
                ],
            }
        )
    return portfolios


__all__ = [
    "resolve_core_dpm_portfolio_universe_candidates",
    "MAX_CORE_DPM_PORTFOLIO_UNIVERSE_PAGES",
]
