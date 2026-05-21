from __future__ import annotations

from src.api.routers.wave_http_errors import (
    wave_lookup_http_exception,
    wave_validation_http_exception,
)
from src.api.services import wave_service
from src.core.mandate_repository import DpmMandateRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves import DpmWaveReportInput, DpmWaveRepository


def get_wave_report_input_response(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
    proof_pack_repository: DpmProofPackRepository,
    outcome_review_repository: DpmOutcomeReviewRepository,
    mandate_repository: DpmMandateRepository,
) -> DpmWaveReportInput:
    try:
        return wave_service.get_report_input(
            wave_id=wave_id,
            wave_repository=wave_repository,
            proof_pack_repository=proof_pack_repository,
            outcome_review_repository=outcome_review_repository,
            mandate_repository=mandate_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise wave_lookup_http_exception(exc) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise wave_validation_http_exception(exc) from exc
