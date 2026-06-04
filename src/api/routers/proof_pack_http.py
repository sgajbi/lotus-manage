from __future__ import annotations

from fastapi import HTTPException, status

from src.api.services.proof_pack_service import (
    DpmProofPackAiEvidenceInputNotGeneratedError,
    DpmProofPackReportInputNotGeneratedError,
)
from src.core.proof_packs import ProofPackSourceValidationError
from src.core.proof_packs.repository import DpmProofPackConflictError
from src.core.rebalance_runs.service import DpmRunNotFoundError

PROOF_PACK_ROUTE_ERRORS = (
    DpmProofPackConflictError,
    DpmRunNotFoundError,
    ProofPackSourceValidationError,
    DpmProofPackReportInputNotGeneratedError,
    DpmProofPackAiEvidenceInputNotGeneratedError,
)


def proof_pack_http_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, DpmProofPackConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, DpmRunNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ProofPackSourceValidationError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(
        exc,
        (
            DpmProofPackReportInputNotGeneratedError,
            DpmProofPackAiEvidenceInputNotGeneratedError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=type(exc).__name__,
    )
