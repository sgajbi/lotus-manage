from __future__ import annotations

import importlib

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import (
    get_mandate_repository,
    get_outcome_review_repository,
    get_proof_pack_repository,
    get_wave_repository,
)
from src.api.routers.outcome_review_models import (
    DpmOutcomeReviewListAppliedFilters,
    DpmOutcomeReviewListResponse,
    DpmOutcomeReviewLookupResponse,
)
from src.api.services.outcome_review_service import (
    DpmOutcomeReviewNotFoundError,
    get_ai_evidence_input,
    get_report_input,
    search_outcome_reviews,
)
from src.core.outcomes import (
    DpmOutcomeAiEvidenceInput,
    DpmOutcomeReportInput,
    OutcomeReviewState,
)
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves.repository import DpmWaveRepository

router = APIRouter(
    prefix="/rebalance/outcome-reviews",
    tags=["lotus-manage Outcome Reviews"],
)


importlib.import_module("src.api.routers.outcome_review_preview_routes")
importlib.import_module("src.api.routers.outcome_review_create_routes")


@router.get(
    "",
    response_model=DpmOutcomeReviewListResponse,
    summary="Search post-trade outcome reviews",
    description=(
        "What: Search persisted RFC-0042 outcome reviews using bounded metadata filters.\n"
        "When: Use for PM, CIO, operations, report, or AI consumers that need outcome-review "
        "memory without recomputing source truth.\n"
        "How: Apply portfolio, mandate, wave, run, state, source-owner, source-type, limit, and "
        "offset filters. The response returns immutable review records and source-lineage facets "
        "from manage persistence without querying source-owner stores."
    ),
)
def list_outcome_reviews_endpoint(
    portfolio_id: str | None = Query(default=None, description="Optional portfolio id filter."),
    mandate_id: str | None = Query(default=None, description="Optional mandate id filter."),
    wave_id: str | None = Query(default=None, description="Optional wave id filter."),
    rebalance_run_id: str | None = Query(
        default=None, description="Optional rebalance run id filter."
    ),
    state: OutcomeReviewState | None = Query(
        default=None,
        description="Optional review state filter.",
        examples=["READY"],
    ),
    source_system: str | None = Query(
        default=None,
        description=(
            "Optional source-owner system filter over persisted outcome-review source lineage. "
            "Leading and trailing whitespace is normalized before matching."
        ),
        examples=["lotus-risk"],
    ),
    source_type: str | None = Query(
        default=None,
        description=(
            "Optional source-type filter over persisted outcome-review source lineage. Leading "
            "and trailing whitespace is normalized before matching."
        ),
        examples=["RiskMetricsReport:v1"],
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum reviews to return."),
    offset: int = Query(default=0, ge=0, description="Zero-based page offset."),
    source_scan_limit: int = Query(
        default=500,
        ge=1,
        le=1000,
        description="Maximum persisted outcome-review rows to scan before source-lineage filtering.",
    ),
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmOutcomeReviewListResponse:
    (
        items,
        total,
        source_owner_counts,
        source_type_counts,
        normalized_source_system,
        normalized_source_type,
    ) = search_outcome_reviews(
        repository=repository,
        portfolio_id=portfolio_id,
        mandate_id=mandate_id,
        wave_id=wave_id,
        rebalance_run_id=rebalance_run_id,
        state=state,
        limit=limit,
        offset=offset,
        source_system=source_system,
        source_type=source_type,
        source_scan_limit=source_scan_limit,
    )
    return DpmOutcomeReviewListResponse(
        items=items,
        total=total,
        applied_filters=DpmOutcomeReviewListAppliedFilters(
            portfolio_id=portfolio_id,
            mandate_id=mandate_id,
            wave_id=wave_id,
            rebalance_run_id=rebalance_run_id,
            state=state,
            source_system=normalized_source_system,
            source_type=normalized_source_type,
        ),
        source_owner_counts=source_owner_counts,
        source_type_counts=source_type_counts,
    )


@router.get(
    "/{outcome_review_id}",
    response_model=DpmOutcomeReviewLookupResponse,
    summary="Get post-trade outcome review",
    description=(
        "What: Retrieve one immutable RFC-0042 outcome review by id.\n"
        "When: Use after create, search, run lookup, or wave lookup to inspect persisted "
        "expected-versus-realized evidence.\n"
        "How: Provide the manage-owned outcome review id. The endpoint returns stored review "
        "truth and does not refresh sources or recalculate source-owner values."
    ),
)
def get_outcome_review_endpoint(
    outcome_review_id: str,
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmOutcomeReviewLookupResponse:
    review = repository.get_outcome_review(outcome_review_id=outcome_review_id)
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OUTCOME_REVIEW_NOT_FOUND"
        )
    return DpmOutcomeReviewLookupResponse(outcome_review=review)


importlib.import_module("src.api.routers.outcome_review_refresh_routes")
importlib.import_module("src.api.routers.outcome_review_supportability_routes")


@router.get(
    "/{outcome_review_id}/report-input",
    response_model=DpmOutcomeReportInput,
    summary="Get outcome-review report input",
    description=(
        "What: Return deterministic report-ready facts for a persisted RFC-0042 outcome review.\n"
        "When: Use when `lotus-report`, `lotus-render`, or `lotus-archive` needs bounded outcome "
        "evidence without recomputing review truth.\n"
        "How: The response is derived from the immutable review, source hashes, dimension results, "
        "and supportability. `lotus-manage` does not generate rendered reports or archive records."
    ),
)
def get_outcome_review_report_input_endpoint(
    outcome_review_id: str,
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmOutcomeReportInput:
    try:
        return get_report_input(
            outcome_review_id=outcome_review_id,
            repository=repository,
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            mandate_repository=mandate_repository,
        )
    except DpmOutcomeReviewNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OUTCOME_REVIEW_NOT_FOUND"
        ) from exc


@router.get(
    "/{outcome_review_id}/ai-evidence-input",
    response_model=DpmOutcomeAiEvidenceInput,
    summary="Get outcome-review AI evidence input",
    description=(
        "What: Return bounded AI evidence for RFC-0043 and `lotus-ai` workflows.\n"
        "When: Use when AI assistance needs provenance-rich outcome facts without raw source "
        "payloads, investment authority, or client-contact authority.\n"
        "How: The response includes permitted use, forbidden actions, source refs, dimension facts, "
        "and a canonical content hash. `lotus-manage` does not generate AI prompts, PM memos, "
        "recommendations, approvals, or execution instructions."
    ),
)
def get_outcome_review_ai_evidence_input_endpoint(
    outcome_review_id: str,
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmOutcomeAiEvidenceInput:
    try:
        return get_ai_evidence_input(
            outcome_review_id=outcome_review_id,
            repository=repository,
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            mandate_repository=mandate_repository,
        )
    except DpmOutcomeReviewNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OUTCOME_REVIEW_NOT_FOUND"
        ) from exc


run_lookup_router = APIRouter(prefix="/rebalance/runs", tags=["lotus-manage Outcome Reviews"])
wave_lookup_router = APIRouter(prefix="/rebalance/waves", tags=["lotus-manage Outcome Reviews"])


@run_lookup_router.get(
    "/{rebalance_run_id}/outcome-review",
    response_model=DpmOutcomeReviewLookupResponse,
    summary="Get outcome review by rebalance run",
    description=(
        "What: Return the first persisted outcome review for a rebalance run when one exists.\n"
        "When: Use to connect RFC-0039/RFC-0040/RFC-0041 run evidence to the RFC-0042 outcome "
        "review that closed the loop.\n"
        "How: Provide the rebalance run id. The endpoint searches persisted manage outcome-review "
        "truth and returns 404 when no review has been created."
    ),
)
def get_outcome_review_by_run_endpoint(
    rebalance_run_id: str,
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmOutcomeReviewLookupResponse:
    items = repository.list_outcome_reviews(rebalance_run_id=rebalance_run_id, limit=1)
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OUTCOME_REVIEW_NOT_FOUND"
        )
    return DpmOutcomeReviewLookupResponse(outcome_review=items[0])


@wave_lookup_router.get(
    "/{wave_id}/outcome-reviews",
    response_model=DpmOutcomeReviewListResponse,
    summary="List outcome reviews by rebalance wave",
    description=(
        "What: Return persisted outcome reviews associated with a rebalance wave.\n"
        "When: Use after RFC-0041 wave approval, staging, or handoff to inspect post-trade "
        "reviews for affected portfolios.\n"
        "How: Provide the manage-owned wave id plus optional pagination. The endpoint lists "
        "stored review records without deriving wave state locally."
    ),
)
def list_outcome_reviews_by_wave_endpoint(
    wave_id: str,
    limit: int = Query(default=50, ge=1, le=200, description="Maximum reviews to return."),
    offset: int = Query(default=0, ge=0, description="Zero-based page offset."),
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmOutcomeReviewListResponse:
    (
        items,
        total,
        source_owner_counts,
        source_type_counts,
        _,
        _,
    ) = search_outcome_reviews(
        repository=repository,
        wave_id=wave_id,
        limit=limit,
        offset=offset,
    )
    return DpmOutcomeReviewListResponse(
        items=items,
        total=total,
        applied_filters=DpmOutcomeReviewListAppliedFilters(wave_id=wave_id),
        source_owner_counts=source_owner_counts,
        source_type_counts=source_type_counts,
    )
