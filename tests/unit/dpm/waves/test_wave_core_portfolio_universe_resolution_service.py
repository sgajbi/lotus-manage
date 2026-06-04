from __future__ import annotations

from datetime import date

import pytest

from src.api.services.wave_core_portfolio_universe_resolution import (
    _PortfolioUniverseResolutionRequest,
    _candidate_portfolio_payloads,
    _portfolio_universe_candidate_page_ref,
    _resolve_candidate_pages,
    _selection_basis_payload,
    resolve_core_dpm_portfolio_universe_candidates,
)
from src.api.services.wave_errors import (
    DpmWaveDependencyFailedError,
    DpmWaveDependencyUnavailableError,
)
from src.core.dpm_source_context import (
    DpmCorePortfolioUniverseCandidate,
    DpmCorePortfolioUniverseCandidateResponse,
    DpmCorePortfolioUniverseCandidateSelectionBasis,
    DpmCorePortfolioUniverseCandidateSupportability,
    DpmCorePortfolioUniversePageMetadata,
)
from src.infrastructure.core_sourcing import (
    DpmCoreResolverError,
    DpmCoreResolverUnavailableError,
)


def _candidate_row(
    *,
    portfolio_id: str,
    mandate_id: str,
    binding_version: int,
    source_record_id: str,
) -> dict[str, object]:
    return {
        "portfolio_id": portfolio_id,
        "mandate_id": mandate_id,
        "client_id": "CIF_SG_000184",
        "booking_center_code": "Singapore",
        "jurisdiction_code": "SG",
        "discretionary_authority_status": "active",
        "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
        "policy_pack_id": "POLICY_DPM_SG_BALANCED_V1",
        "mandate_objective": "Global balanced discretionary mandate.",
        "risk_profile": "balanced",
        "investment_horizon": "long_term",
        "effective_from": "2026-05-01",
        "effective_to": None,
        "binding_version": binding_version,
        "source_record_id": source_record_id,
    }


def _candidate_page(
    *,
    supportability_state: str = "READY",
    next_page_token: str | None = None,
    returned_candidate_count: int = 1,
    candidates: list[dict[str, object]] | None = None,
) -> DpmCorePortfolioUniverseCandidateResponse:
    resolved_candidates = (
        [DpmCorePortfolioUniverseCandidate.model_validate(candidate) for candidate in candidates]
        if candidates is not None
        else [
            DpmCorePortfolioUniverseCandidate.model_validate(
                _candidate_row(
                    portfolio_id="PB_SG_GLOBAL_BAL_001",
                    mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
                    binding_version=3,
                    source_record_id="mandate-binding-001",
                )
            )
        ]
    )
    if returned_candidate_count == 0:
        resolved_candidates = []
    return DpmCorePortfolioUniverseCandidateResponse(
        product_name="DpmPortfolioUniverseCandidate",
        product_version="v1",
        as_of_date=date(2026, 5, 10),
        tenant_id="default",
        candidates=resolved_candidates,
        page=DpmCorePortfolioUniversePageMetadata(
            page_size=1000,
            sort_key="portfolio_id:asc,mandate_id:asc",
            returned_component_count=returned_candidate_count,
            request_scope_fingerprint="sha256:dpm-portfolio-universe",
            next_page_token=next_page_token,
        ),
        supportability=DpmCorePortfolioUniverseCandidateSupportability(
            state=supportability_state,
            reason=(
                "DPM_PORTFOLIO_UNIVERSE_READY"
                if supportability_state == "READY"
                else "DPM_PORTFOLIO_UNIVERSE_EMPTY"
                if returned_candidate_count == 0
                else "DPM_PORTFOLIO_UNIVERSE_PAGE_PARTIAL"
            ),
            returned_candidate_count=returned_candidate_count,
            filters_applied=["as_of_date"],
            page_truncated=next_page_token is not None,
        ),
        selection_basis=DpmCorePortfolioUniverseCandidateSelectionBasis(
            basis_type="EFFECTIVE_DISCRETIONARY_MANDATE_BINDING",
            source_table="portfolio_mandate_bindings",
            included_when=[],
            downstream_boundary="Candidate membership is not execution authority.",
        ),
        lineage={},
        source_batch_fingerprint="sha256:portfolio-universe",
        snapshot_id="snapshot-001",
        data_quality_status="ACCEPTED",
        latest_evidence_timestamp="2026-05-10T09:00:00Z",
    )


class _UniverseResolver:
    def __init__(self, pages: list[DpmCorePortfolioUniverseCandidateResponse]) -> None:
        self.pages = pages
        self.calls: list[dict[str, object]] = []

    def resolve_dpm_portfolio_universe_candidates(
        self,
        **kwargs: object,
    ) -> DpmCorePortfolioUniverseCandidateResponse:
        self.calls.append(kwargs)
        index = min(len(self.calls) - 1, len(self.pages) - 1)
        return self.pages[index]


def _resolve(
    *,
    pages: list[DpmCorePortfolioUniverseCandidateResponse],
    campaign_candidate_page_size: int = 1000,
) -> tuple[list[dict[str, object]], _UniverseResolver]:
    resolver = _UniverseResolver(pages)
    candidates = resolve_core_dpm_portfolio_universe_candidates(
        as_of_date=date(2026, 5, 10),
        tenant_id="default",
        booking_center_code="Singapore",
        model_portfolio_ids=["MODEL_PB_SG_GLOBAL_BAL_DPM"],
        include_inactive_mandates=False,
        campaign_candidate_page_size=campaign_candidate_page_size,
        correlation_id="corr-universe-001",
        core_resolver_factory=lambda: resolver,
    )
    return candidates, resolver


def test_resolve_core_dpm_portfolio_universe_candidates_paginates_and_attaches_selection_basis() -> (
    None
):
    page_0 = _candidate_page(next_page_token="page-2", returned_candidate_count=1)
    page_1 = _candidate_page(
        next_page_token=None,
        returned_candidate_count=1,
        candidates=[
            _candidate_row(
                portfolio_id="PB_SG_GLOBAL_BAL_002",
                mandate_id="MANDATE_PB_SG_GLOBAL_BAL_002",
                binding_version=4,
                source_record_id="mandate-binding-002",
            )
        ],
    )

    candidates, resolver = _resolve(pages=[page_0, page_1], campaign_candidate_page_size=1)

    assert len(candidates) == 2
    assert resolver.calls[0]["page_token"] is None
    assert resolver.calls[1]["page_token"] == "page-2"
    assert candidates[0]["source_refs"][0]["source_type"] == "DpmPortfolioUniverseCandidate"
    assert candidates[0]["source_refs"][1]["source_type"] == "DPM_PORTFOLIO_UNIVERSE_CANDIDATE"


def test_resolve_candidate_pages_passes_bounded_page_tokens() -> None:
    page_0 = _candidate_page(next_page_token="page-2", returned_candidate_count=1)
    page_1 = _candidate_page(
        next_page_token=None,
        returned_candidate_count=1,
        candidates=[
            _candidate_row(
                portfolio_id="PB_SG_GLOBAL_BAL_002",
                mandate_id="MANDATE_PB_SG_GLOBAL_BAL_002",
                binding_version=4,
                source_record_id="mandate-binding-002",
            )
        ],
    )
    resolver = _UniverseResolver([page_0, page_1])

    pages = _resolve_candidate_pages(
        resolver=resolver,
        request=_PortfolioUniverseResolutionRequest(
            as_of_date=date(2026, 5, 10),
            tenant_id="default",
            booking_center_code="Singapore",
            model_portfolio_ids=["MODEL_PB_SG_GLOBAL_BAL_DPM"],
            include_inactive_mandates=False,
            campaign_candidate_page_size=1,
            correlation_id="corr-universe-001",
        ),
    )

    assert pages == [page_0, page_1]
    assert resolver.calls[0]["page_token"] is None
    assert resolver.calls[1]["page_token"] == "page-2"
    assert resolver.calls[1]["page_size"] == 1


def test_candidate_portfolio_payloads_preserve_page_and_candidate_source_refs() -> None:
    page = _candidate_page()
    candidate = page.candidates[0]

    payloads = _candidate_portfolio_payloads(
        candidates=[candidate],
        universe_ref=_portfolio_universe_candidate_page_ref(page=page),
        selection_basis=_selection_basis_payload(page),
    )

    assert len(payloads) == 1
    assert payloads[0]["portfolio_id"] == "PB_SG_GLOBAL_BAL_001"
    assert payloads[0]["mandate_id"] == "MANDATE_PB_SG_GLOBAL_BAL_001"
    assert payloads[0]["portfolio_type"] == "DISCRETIONARY"

    page_ref, candidate_ref = payloads[0]["source_refs"]
    assert page_ref == {
        "source_system": "lotus-core",
        "source_type": "DpmPortfolioUniverseCandidate",
        "source_id": "snapshot-001",
        "source_version": "v1",
        "content_hash": "sha256:portfolio-universe",
        "supportability_state": "READY",
    }
    assert candidate_ref["source_type"] == "DPM_PORTFOLIO_UNIVERSE_CANDIDATE"
    assert candidate_ref["source_id"] == "mandate-binding-001"
    assert candidate_ref["source_version"] == "3"
    assert candidate_ref["selection_basis"] == {
        "basis_type": "EFFECTIVE_DISCRETIONARY_MANDATE_BINDING",
        "source_table": "portfolio_mandate_bindings",
        "included_when": [],
        "downstream_boundary": "Candidate membership is not execution authority.",
    }


def test_resolve_core_dpm_portfolio_universe_candidates_rejects_duplicate_candidates() -> None:
    page = _candidate_page(
        next_page_token=None,
        returned_candidate_count=2,
        candidates=[
            _candidate_row(
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                mandate_id="MANDATE_001",
                binding_version=3,
                source_record_id="mandate-binding-001",
            ),
            _candidate_row(
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                mandate_id="MANDATE_001",
                binding_version=3,
                source_record_id="mandate-binding-001",
            ),
        ],
    )

    with pytest.raises(DpmWaveDependencyFailedError) as exc_info:
        _resolve(pages=[page])

    assert exc_info.value.code == "DPM_CORE_PORTFOLIO_UNIVERSE_DUPLICATE_CANDIDATE"


def test_resolve_core_dpm_portfolio_universe_candidates_rejects_non_terminating_page_tokens() -> (
    None
):
    first_page = _candidate_page(next_page_token="page-2", returned_candidate_count=1)
    second_page = _candidate_page(
        next_page_token="page-2",
        returned_candidate_count=1,
        candidates=[
            _candidate_row(
                portfolio_id="PB_SG_GLOBAL_BAL_002",
                mandate_id="MANDATE_002",
                binding_version=4,
                source_record_id="mandate-binding-002",
            )
        ],
    )

    with pytest.raises(DpmWaveDependencyFailedError) as exc_info:
        _resolve(pages=[first_page, second_page])

    assert exc_info.value.code == "DPM_CORE_PORTFOLIO_UNIVERSE_NON_TERMINATING"


def test_resolve_core_dpm_portfolio_universe_candidates_maps_unavailable_dependency() -> None:
    with pytest.raises(DpmWaveDependencyUnavailableError) as exc_info:
        resolve_core_dpm_portfolio_universe_candidates(
            as_of_date=date(2026, 5, 10),
            tenant_id="default",
            booking_center_code="Singapore",
            model_portfolio_ids=[],
            include_inactive_mandates=False,
            campaign_candidate_page_size=1000,
            correlation_id="corr-universe-unavailable",
            core_resolver_factory=lambda: _UnavailableCoreResolver(),
        )

    assert exc_info.value.code == "UNAVAILABLE"


class _UnavailableCoreResolver:
    def resolve_dpm_portfolio_universe_candidates(self, **_kwargs: object) -> None:
        raise DpmCoreResolverUnavailableError("UNAVAILABLE")


def test_resolve_core_dpm_portfolio_universe_candidates_maps_incomplete_dependency() -> None:
    with pytest.raises(DpmWaveDependencyFailedError) as exc_info:
        resolve_core_dpm_portfolio_universe_candidates(
            as_of_date=date(2026, 5, 10),
            tenant_id="default",
            booking_center_code="Singapore",
            model_portfolio_ids=[],
            include_inactive_mandates=False,
            campaign_candidate_page_size=1000,
            correlation_id="corr-universe-incomplete",
            core_resolver_factory=lambda: _IncompleteCoreResolver(),
        )

    assert exc_info.value.code == "INCOMPLETE"


class _IncompleteCoreResolver:
    def resolve_dpm_portfolio_universe_candidates(self, **_kwargs: object) -> None:
        raise DpmCoreResolverError("INCOMPLETE")
