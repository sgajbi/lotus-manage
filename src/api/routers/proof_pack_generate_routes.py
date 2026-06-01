from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from src.api.dependencies import (
    get_construction_repository,
    get_mandate_repository,
    get_proof_pack_repository,
)
from src.api.routers.proof_pack_models import (
    PROOF_PACK_EXAMPLE,
    DpmProofPackGenerateRequest,
    DpmProofPackGenerateResponse,
)
from src.api.routers.proof_pack_http import proof_pack_http_exception
from src.api.routers.proof_packs import router
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.api.services import proof_pack_service
from src.core.construction.repository import ConstructionRepository
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs.models import DpmPreTradeProofPack
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.rebalance_runs.service import DpmRunSupportService


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
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
) -> DpmProofPackGenerateResponse:
    try:
        if request.source_type == "REBALANCE_RUN":
            if not request.rebalance_run_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
                mandate_repository=mandate_repository,
                proof_pack_repository=proof_pack_repository,
                direct_regime_stress_context=request.regime_stress_context,
            )
        else:
            if not request.alternative_set_id or not request.selected_alternative_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
                mandate_repository=mandate_repository,
                proof_pack_repository=proof_pack_repository,
                direct_regime_stress_context=request.regime_stress_context,
            )
        proof_pack = proof_pack_service.ensure_handoff_refs(
            proof_pack=proof_pack,
            proof_pack_repository=proof_pack_repository,
            include_report_input=request.include_report_input,
            include_ai_evidence_input=request.include_ai_evidence_input,
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
        http_exc = proof_pack_http_exception(exc)
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
