from fastapi import Depends, HTTPException, status

from src.api.dependencies import (
    get_mandate_repository,
    get_outcome_review_repository,
    get_proof_pack_repository,
    get_wave_repository,
)
from src.api.routers import outcome_reviews as shared
from src.api.services.outcome_review_service import (
    DpmOutcomeReviewNotFoundError,
    get_ai_evidence_input,
    get_report_input,
)
from src.core.mandate_repository import DpmMandateRepository
from src.core.outcomes import DpmOutcomeAiEvidenceInput, DpmOutcomeReportInput
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves.repository import DpmWaveRepository


@shared.router.get(
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


@shared.router.get(
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
