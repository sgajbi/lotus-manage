from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from src.api.services.wave_errors import (
    DpmWaveDependencyFailedError,
    DpmWaveDependencyUnavailableError,
)
from src.api.services.core_resolver_service import (
    CoreResolverError,
    CoreResolverUnavailableError,
)
from src.core.dpm_source_context import (
    DpmCorePortfolioUniverseCandidate,
    DpmCorePortfolioUniverseCandidateResponse,
)
from src.core.waves import DpmWaveSourceRef

CoreResolverFactory = Callable[[], Any]

MAX_CORE_DPM_PORTFOLIO_UNIVERSE_PAGES = 10
_SHA256_IDENTITY_PATTERN = re.compile(r"^sha256:[0-9a-fA-F]{64}$")


@dataclass(frozen=True)
class _PortfolioUniverseResolutionRequest:
    as_of_date: date
    tenant_id: str | None
    booking_center_code: str | None
    model_portfolio_ids: list[str]
    include_inactive_mandates: bool
    campaign_candidate_page_size: int
    correlation_id: str


@dataclass(frozen=True)
class _CandidateSourceRow:
    candidate: DpmCorePortfolioUniverseCandidate
    universe_ref: dict[str, object]
    selection_basis: dict[str, object] | None


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
    ).model_dump(mode="json", exclude_none=True)


def _portfolio_universe_candidate_page_ref(
    *, page: DpmCorePortfolioUniverseCandidateResponse
) -> dict[str, object]:
    content_hash = _portfolio_universe_candidate_content_hash(page)
    return DpmWaveSourceRef(
        source_system="lotus-core",
        source_type="DpmPortfolioUniverseCandidate",
        source_id=page.snapshot_id or page.page.request_scope_fingerprint,
        source_version=page.product_version,
        supportability_state=page.supportability.state,
        content_hash=content_hash,
        source_batch_fingerprint=_clean_optional_text(page.source_batch_fingerprint),
    ).model_dump(mode="json", exclude_none=True)


def _portfolio_universe_candidate_content_hash(
    page: DpmCorePortfolioUniverseCandidateResponse,
) -> str:
    content_hash = _clean_optional_text(page.content_hash)
    source_digest = _clean_optional_text(page.source_digest)
    if content_hash is not None and source_digest is not None and content_hash != source_digest:
        raise DpmWaveDependencyFailedError(
            code="DPM_CORE_PORTFOLIO_UNIVERSE_CONTENT_IDENTITY_CONFLICT",
            message=(
                "Core DPM portfolio-universe candidates returned conflicting content_hash and "
                "source_digest identities."
            ),
        )

    resolved_hash = content_hash or source_digest
    if resolved_hash is None:
        raise DpmWaveDependencyFailedError(
            code="DPM_CORE_PORTFOLIO_UNIVERSE_CONTENT_HASH_REQUIRED",
            message=(
                "Core DPM portfolio-universe candidates must publish a canonical content_hash "
                "or source_digest before Manage can publish campaign membership as READY."
            ),
        )
    if not _is_sha256_identity(resolved_hash):
        raise DpmWaveDependencyFailedError(
            code="DPM_CORE_PORTFOLIO_UNIVERSE_CONTENT_HASH_INVALID",
            message=(
                "Core DPM portfolio-universe candidates returned a malformed canonical content "
                "identity."
            ),
        )
    return resolved_hash


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _is_sha256_identity(value: str) -> bool:
    return _SHA256_IDENTITY_PATTERN.fullmatch(value) is not None


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
    request = _PortfolioUniverseResolutionRequest(
        as_of_date=as_of_date,
        tenant_id=tenant_id,
        booking_center_code=booking_center_code,
        model_portfolio_ids=model_portfolio_ids,
        include_inactive_mandates=include_inactive_mandates,
        campaign_candidate_page_size=campaign_candidate_page_size,
        correlation_id=correlation_id,
    )
    resolver = core_resolver_factory()
    try:
        candidate_pages = _resolve_candidate_pages(resolver=resolver, request=request)
    except CoreResolverUnavailableError as exc:
        raise DpmWaveDependencyUnavailableError(
            code=str(exc) or "DPM_CORE_PORTFOLIO_UNIVERSE_UNAVAILABLE"
        ) from exc
    except CoreResolverError as exc:
        raise DpmWaveDependencyFailedError(
            code=str(exc) or "DPM_CORE_PORTFOLIO_UNIVERSE_INCOMPLETE"
        ) from exc

    return _portfolio_payloads_from_candidate_pages(candidate_pages)


def _resolve_candidate_pages(
    *,
    resolver: Any,
    request: _PortfolioUniverseResolutionRequest,
) -> list[DpmCorePortfolioUniverseCandidateResponse]:
    candidate_pages: list[DpmCorePortfolioUniverseCandidateResponse] = []
    next_page_token: str | None = None
    seen_page_tokens: set[str] = set()

    for _ in range(MAX_CORE_DPM_PORTFOLIO_UNIVERSE_PAGES):
        candidate_page = resolver.resolve_dpm_portfolio_universe_candidates(
            as_of_date=request.as_of_date,
            tenant_id=request.tenant_id,
            booking_center_code=request.booking_center_code,
            model_portfolio_ids=request.model_portfolio_ids,
            include_inactive_mandates=request.include_inactive_mandates,
            page_size=request.campaign_candidate_page_size,
            page_token=next_page_token,
            correlation_id=request.correlation_id,
        )
        candidate_pages.append(candidate_page)
        if candidate_page.supportability.state != "READY":
            break
        next_page_token = candidate_page.page.next_page_token
        if not next_page_token:
            break
        if next_page_token in seen_page_tokens:
            raise CoreResolverError("DPM_CORE_PORTFOLIO_UNIVERSE_NON_TERMINATING")
        seen_page_tokens.add(next_page_token)
    else:
        raise CoreResolverError("DPM_CORE_PORTFOLIO_UNIVERSE_NON_TERMINATING")

    return candidate_pages


def _portfolio_payloads_from_candidate_pages(
    candidate_pages: list[DpmCorePortfolioUniverseCandidateResponse],
) -> list[dict[str, object]]:
    candidate_page = candidate_pages[-1]
    if candidate_page.supportability.state != "READY":
        raise DpmWaveDependencyFailedError(
            code=candidate_page.supportability.reason,
            message="Core DPM portfolio-universe candidates are not source-ready.",
        )
    if candidate_page.page.next_page_token or candidate_page.supportability.page_truncated:
        raise DpmWaveDependencyFailedError(
            code="DPM_CORE_PORTFOLIO_UNIVERSE_PAGE_PARTIAL",
            message=(
                "Core DPM portfolio-universe candidates could not be exhausted within the "
                "bounded Manage consumer guard; refine filters before creating a campaign wave."
            ),
        )

    candidate_rows = _candidate_source_rows(candidate_pages)
    if not candidate_rows:
        raise DpmWaveDependencyFailedError(
            code="DPM_CORE_PORTFOLIO_UNIVERSE_EMPTY",
            message="Core DPM portfolio-universe discovery returned no candidate portfolios.",
        )
    return _candidate_portfolio_payloads(candidate_rows=candidate_rows)


def _candidate_source_rows(
    candidate_pages: list[DpmCorePortfolioUniverseCandidateResponse],
) -> list[_CandidateSourceRow]:
    rows: list[_CandidateSourceRow] = []
    for page in candidate_pages:
        universe_ref = _portfolio_universe_candidate_page_ref(page=page)
        selection_basis = _selection_basis_payload(page)
        rows.extend(
            _CandidateSourceRow(
                candidate=candidate,
                universe_ref=universe_ref,
                selection_basis=selection_basis,
            )
            for candidate in page.candidates
        )
    return rows


def _candidate_key(
    candidate: DpmCorePortfolioUniverseCandidate,
) -> tuple[str, str | None, str | None]:
    return (
        candidate.portfolio_id,
        candidate.mandate_id,
        candidate.source_record_id,
    )


def _candidate_portfolio_payloads(
    *,
    candidate_rows: list[_CandidateSourceRow],
) -> list[dict[str, object]]:
    candidate_keys: set[tuple[str, str | None, str | None]] = set()
    portfolios: list[dict[str, object]] = []

    for row in candidate_rows:
        candidate = row.candidate
        candidate_key = _candidate_key(candidate)
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
                "portfolio_type": "DISCRETIONARY",
                "source_refs": [
                    row.universe_ref,
                    _portfolio_universe_candidate_ref(
                        candidate=candidate,
                        selection_basis=row.selection_basis,
                    ),
                ],
            }
        )
    return portfolios


__all__ = [
    "resolve_core_dpm_portfolio_universe_candidates",
    "MAX_CORE_DPM_PORTFOLIO_UNIVERSE_PAGES",
]
