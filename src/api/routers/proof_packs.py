from __future__ import annotations

import importlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import PlainTextResponse

from src.api.dependencies import (
    get_mandate_repository,
    get_outcome_review_repository,
    get_proof_pack_repository,
    get_wave_repository,
)
from src.api.routers.proof_pack_models import (
    DpmProofPackLookupResponse,
)
from src.api.services import proof_pack_service
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs import render_proof_pack_markdown
from src.core.proof_packs.handoffs import DpmProofPackAiEvidenceInput, DpmProofPackReportInput
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.waves.repository import DpmWaveRepository


router = APIRouter(
    prefix="/rebalance/proof-packs",
    tags=["lotus-manage Proof Packs"],
)


importlib.import_module("src.api.routers.proof_pack_generate_routes")


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
    response_model=DpmProofPackReportInput,
    status_code=status.HTTP_200_OK,
    summary="Get proof-pack report input",
    description="Returns deterministic `DpmProofPackReportInput` for a persisted proof pack.",
    responses={
        200: {"description": "Generated report-input payload."},
        404: {"description": "Proof pack was not found."},
    },
)
def get_proof_pack_report_input(
    proof_pack_id: Annotated[
        str,
        Path(description="Proof-pack identifier.", examples=["dpp_rr_001"]),
    ],
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    outcome_review_repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmProofPackReportInput:
    try:
        return proof_pack_service.get_report_input(
            proof_pack_id=proof_pack_id,
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=outcome_review_repository,
            mandate_repository=mandate_repository,
        )
    except Exception as exc:
        http_exc = proof_pack_service.to_api_http_exception(exc)
        raise HTTPException(status_code=http_exc.status_code, detail=http_exc.detail) from exc


@router.get(
    "/{proof_pack_id}/ai-evidence-input",
    response_model=DpmProofPackAiEvidenceInput,
    status_code=status.HTTP_200_OK,
    summary="Get proof-pack AI evidence input",
    description="Returns deterministic `DpmProofPackAiEvidenceInput` for a persisted proof pack.",
    responses={
        200: {"description": "Generated AI-evidence input payload."},
        404: {"description": "Proof pack was not found."},
    },
)
def get_proof_pack_ai_evidence_input(
    proof_pack_id: Annotated[
        str,
        Path(description="Proof-pack identifier.", examples=["dpp_rr_001"]),
    ],
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    outcome_review_repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmProofPackAiEvidenceInput:
    try:
        return proof_pack_service.get_ai_evidence_input(
            proof_pack_id=proof_pack_id,
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=outcome_review_repository,
            mandate_repository=mandate_repository,
        )
    except Exception as exc:
        http_exc = proof_pack_service.to_api_http_exception(exc)
        raise HTTPException(status_code=http_exc.status_code, detail=http_exc.detail) from exc
