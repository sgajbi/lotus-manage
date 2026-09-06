from src.api.services.wave_errors import DpmWaveValidationError
from src.api.services.wave_proof_pack_posture import proof_pack_posture_for_wave
from src.api.services.wave_report_context import portfolio_memory_context_for_report
from src.api.services.wave_supportability_payload import wave_supportability_payload
from src.core.mandate_repository import DpmMandateRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves import (
    DpmRebalanceWave,
    DpmWaveReportInput,
    DpmWaveReportInputBoundaryError,
    DpmWaveRepository,
    build_wave_report_input,
)


def build_report_input_for_wave(
    *,
    wave: DpmRebalanceWave,
    wave_repository: DpmWaveRepository,
    proof_pack_repository: DpmProofPackRepository | None = None,
    outcome_review_repository: DpmOutcomeReviewRepository | None = None,
    mandate_repository: DpmMandateRepository | None = None,
    tenant_id: str | None = None,
) -> DpmWaveReportInput:
    try:
        return build_wave_report_input(
            wave=wave,
            supportability=wave_supportability_payload(wave),
            proof_pack_posture=proof_pack_posture_for_wave(wave=wave),
            portfolio_memory_context=portfolio_memory_context_for_report(
                wave=wave,
                proof_pack_repository=proof_pack_repository,
                wave_repository=wave_repository,
                outcome_review_repository=outcome_review_repository,
                mandate_repository=mandate_repository,
                tenant_id=tenant_id,
            ),
        )
    except DpmWaveReportInputBoundaryError as exc:
        raise DpmWaveValidationError("DPM_WAVE_EXTERNAL_EXECUTION_BOUNDARY", str(exc)) from exc


__all__ = ["build_report_input_for_wave"]
