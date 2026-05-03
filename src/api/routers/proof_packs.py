from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from src.api.dependencies import get_construction_repository, get_proof_pack_repository
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.api.services import proof_pack_service
from src.core.construction.repository import ConstructionRepository
from src.core.proof_packs import render_proof_pack_markdown
from src.core.proof_packs.models import DpmPreTradeProofPack, DpmProofPackEvidenceRef
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.rebalance_runs.service import DpmRunSupportService


PROOF_PACK_EXAMPLE = {
    "proof_pack_id": "dpp_rr_001",
    "proof_pack_version": "1.0",
    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
    "mandate_id": "mandate_001",
    "source_type": "REBALANCE_RUN",
    "rebalance_run_id": "rr_001",
    "alternative_set_id": None,
    "selected_alternative_id": None,
    "as_of_date": "2026-05-03",
    "status": "DEGRADED",
    "content_hash": "sha256:example",
    "created_at": "2026-05-03T09:30:00+00:00",
    "created_by": "pm_001",
    "correlation_id": "corr-proof-pack-001",
}


class DpmProofPackGenerateRequest(BaseModel):
    source_type: Literal["REBALANCE_RUN", "SELECTED_ALTERNATIVE"] = Field(
        description="Source object used to generate the proof pack.",
        examples=["REBALANCE_RUN"],
    )
    rebalance_run_id: str | None = Field(
        default=None,
        description="Source rebalance run id required when source_type is `REBALANCE_RUN`.",
        examples=["rr_001"],
    )
    alternative_set_id: str | None = Field(
        default=None,
        description="Construction alternative set id required for selected-alternative proof.",
        examples=["cas_001"],
    )
    selected_alternative_id: str | None = Field(
        default=None,
        description="Selected alternative id required for selected-alternative proof.",
        examples=["alt_min_turnover"],
    )
    include_markdown: bool = Field(
        default=True,
        description="Whether the caller intends to retrieve deterministic Markdown.",
        examples=[True],
    )
    include_report_input: bool = Field(
        default=False,
        description="Reserved for Slice 7 report-input generation.",
        examples=[False],
    )
    include_ai_evidence_input: bool = Field(
        default=False,
        description="Reserved for Slice 7 AI-evidence input generation.",
        examples=[False],
    )
    actor_id: str = Field(
        description="Human or service actor generating the proof pack.",
        examples=["pm_001"],
    )
    reason: str | None = Field(
        default=None,
        description="Business rationale for generating the proof pack.",
        examples=["Rebalance back to model after drift review."],
    )
    mandate_id: str | None = Field(
        default=None,
        description="Mandate identifier when available.",
        examples=["mandate_001"],
    )


class DpmProofPackGenerateResponse(BaseModel):
    proof_pack: DpmPreTradeProofPack = Field(description="Generated durable proof pack.")
    markdown_url: str | None = Field(
        default=None,
        description="Relative URL for deterministic Markdown retrieval when requested.",
        examples=["/api/v1/rebalance/proof-packs/dpp_rr_001/summary.md"],
    )
    report_input_url: str | None = Field(
        default=None,
        description="Relative URL for report input retrieval when generated in later slices.",
        examples=["/api/v1/rebalance/proof-packs/dpp_rr_001/report-input"],
    )
    ai_evidence_input_url: str | None = Field(
        default=None,
        description="Relative URL for AI evidence retrieval when generated in later slices.",
        examples=["/api/v1/rebalance/proof-packs/dpp_rr_001/ai-evidence-input"],
    )


class DpmProofPackLookupResponse(BaseModel):
    proof_pack: DpmPreTradeProofPack = Field(description="Persisted proof pack.")


router = APIRouter(
    prefix="/rebalance/proof-packs",
    tags=["lotus-manage Proof Packs"],
)


@router.post(
    "",
    response_model=DpmProofPackGenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a pre-trade proof pack",
    description=(
        "Generates and persists an immutable RFC-0040 pre-trade proof pack from either a "
        "persisted rebalance run or a selected RFC-0039 construction alternative. The proof pack "
        "is source-backed and exposes degraded or blocked sections instead of inventing missing "
        "evidence. Required header: `Idempotency-Key`."
    ),
    responses={
        200: {
            "description": "Proof pack generated or replayed idempotently.",
            "content": {"application/json": {"example": {"proof_pack": PROOF_PACK_EXAMPLE}}},
        },
        404: {
            "description": "Source run, alternative set, selected alternative, or proof pack missing."
        },
        409: {"description": "Proof-pack identity or idempotency conflict."},
        422: {"description": "Request source fields are incomplete or contradictory."},
    },
)
def generate_proof_pack(
    request: DpmProofPackGenerateRequest,
    idempotency_key: Annotated[
        str,
        Header(
            description="Required idempotency token for proof-pack replay.",
            examples=["proof-pack-idem-001"],
        ),
    ],
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation identifier propagated to proof-pack lineage.",
            examples=["corr-proof-pack-001"],
        ),
    ] = None,
    run_service: DpmRunSupportService = Depends(get_dpm_run_support_service),
    construction_repository: ConstructionRepository = Depends(get_construction_repository),
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
) -> DpmProofPackGenerateResponse:
    try:
        if request.source_type == "REBALANCE_RUN":
            if not request.rebalance_run_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="DPM_PROOF_PACK_REBALANCE_RUN_ID_REQUIRED",
                )
            proof_pack = proof_pack_service.generate_proof_pack_from_run(
                rebalance_run_id=request.rebalance_run_id,
                actor_id=request.actor_id,
                reason=request.reason,
                correlation_id=x_correlation_id,
                mandate_id=request.mandate_id,
                idempotency_key=idempotency_key,
                run_service=run_service,
                proof_pack_repository=proof_pack_repository,
            )
        else:
            if not request.alternative_set_id or not request.selected_alternative_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="DPM_PROOF_PACK_SELECTED_ALTERNATIVE_SOURCE_REQUIRED",
                )
            proof_pack = proof_pack_service.generate_proof_pack_from_selected_alternative(
                alternative_set_id=request.alternative_set_id,
                selected_alternative_id=request.selected_alternative_id,
                actor_id=request.actor_id,
                reason=request.reason,
                correlation_id=x_correlation_id,
                mandate_id=request.mandate_id,
                idempotency_key=idempotency_key,
                construction_repository=construction_repository,
                run_service=run_service,
                proof_pack_repository=proof_pack_repository,
            )
        return _to_generate_response(
            proof_pack=proof_pack,
            include_markdown=request.include_markdown,
            include_report_input=request.include_report_input,
            include_ai_evidence_input=request.include_ai_evidence_input,
        )
    except HTTPException:
        raise
    except Exception as exc:
        http_exc = proof_pack_service.to_api_http_exception(exc)
        raise HTTPException(status_code=http_exc.status_code, detail=http_exc.detail) from exc


@router.get(
    "/{proof_pack_id}",
    response_model=DpmProofPackLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a pre-trade proof pack",
    description="Returns a persisted immutable RFC-0040 proof pack by identifier.",
    responses={
        200: {"description": "Persisted proof pack."},
        404: {"description": "Proof pack was not found."},
    },
)
def get_proof_pack(
    proof_pack_id: Annotated[
        str,
        Path(description="Proof-pack identifier.", examples=["dpp_rr_001"]),
    ],
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
) -> DpmProofPackLookupResponse:
    try:
        return DpmProofPackLookupResponse(
            proof_pack=proof_pack_service.get_proof_pack(
                proof_pack_id=proof_pack_id,
                proof_pack_repository=proof_pack_repository,
            )
        )
    except Exception as exc:
        http_exc = proof_pack_service.to_api_http_exception(exc)
        raise HTTPException(status_code=http_exc.status_code, detail=http_exc.detail) from exc


@router.get(
    "/{proof_pack_id}/summary.md",
    response_class=PlainTextResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a pre-trade proof-pack Markdown summary",
    description="Returns deterministic human-readable Markdown for a persisted proof pack.",
    responses={
        200: {"description": "Deterministic proof-pack Markdown."},
        404: {"description": "Proof pack was not found."},
    },
)
def get_proof_pack_markdown(
    proof_pack_id: Annotated[
        str,
        Path(description="Proof-pack identifier.", examples=["dpp_rr_001"]),
    ],
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
) -> str:
    try:
        proof_pack = proof_pack_service.get_proof_pack(
            proof_pack_id=proof_pack_id,
            proof_pack_repository=proof_pack_repository,
        )
        return render_proof_pack_markdown(proof_pack)
    except Exception as exc:
        http_exc = proof_pack_service.to_api_http_exception(exc)
        raise HTTPException(status_code=http_exc.status_code, detail=http_exc.detail) from exc


@router.get(
    "/{proof_pack_id}/report-input",
    response_model=DpmProofPackEvidenceRef,
    status_code=status.HTTP_200_OK,
    summary="Get proof-pack report input",
    description=(
        "Returns the generated `DpmProofPackReportInput` evidence reference for a persisted proof "
        "pack. Until the Slice 7 adapter generates that reference, the endpoint returns a "
        "governed failed-dependency response."
    ),
    responses={
        200: {"description": "Generated report-input evidence reference."},
        424: {"description": "Report input has not been generated for this proof pack."},
        404: {"description": "Proof pack was not found."},
    },
)
def get_proof_pack_report_input(
    proof_pack_id: Annotated[
        str,
        Path(description="Proof-pack identifier.", examples=["dpp_rr_001"]),
    ],
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
) -> DpmProofPackEvidenceRef:
    try:
        return proof_pack_service.get_report_input_ref(
            proof_pack_id=proof_pack_id,
            proof_pack_repository=proof_pack_repository,
        )
    except Exception as exc:
        http_exc = proof_pack_service.to_api_http_exception(exc)
        raise HTTPException(status_code=http_exc.status_code, detail=http_exc.detail) from exc


@router.get(
    "/{proof_pack_id}/ai-evidence-input",
    response_model=DpmProofPackEvidenceRef,
    status_code=status.HTTP_200_OK,
    summary="Get proof-pack AI evidence input",
    description=(
        "Returns the generated `DpmProofPackAiEvidenceInput` evidence reference for a persisted "
        "proof pack. Until the Slice 7 adapter generates that reference, the endpoint returns a "
        "governed failed-dependency response."
    ),
    responses={
        200: {"description": "Generated AI-evidence input reference."},
        424: {"description": "AI evidence input has not been generated for this proof pack."},
        404: {"description": "Proof pack was not found."},
    },
)
def get_proof_pack_ai_evidence_input(
    proof_pack_id: Annotated[
        str,
        Path(description="Proof-pack identifier.", examples=["dpp_rr_001"]),
    ],
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
) -> DpmProofPackEvidenceRef:
    try:
        return proof_pack_service.get_ai_evidence_ref(
            proof_pack_id=proof_pack_id,
            proof_pack_repository=proof_pack_repository,
        )
    except Exception as exc:
        http_exc = proof_pack_service.to_api_http_exception(exc)
        raise HTTPException(status_code=http_exc.status_code, detail=http_exc.detail) from exc


def _to_generate_response(
    *,
    proof_pack: DpmPreTradeProofPack,
    include_markdown: bool,
    include_report_input: bool,
    include_ai_evidence_input: bool,
) -> DpmProofPackGenerateResponse:
    base = f"/api/v1/rebalance/proof-packs/{proof_pack.proof_pack_id}"
    return DpmProofPackGenerateResponse(
        proof_pack=proof_pack,
        markdown_url=f"{base}/summary.md" if include_markdown else None,
        report_input_url=f"{base}/report-input" if include_report_input else None,
        ai_evidence_input_url=f"{base}/ai-evidence-input" if include_ai_evidence_input else None,
    )
