from src.api.services.wave_detail_projection import wave_detail_payload, wave_items_payload
from src.api.services.wave_lookup import get_wave_or_raise
from src.api.services.wave_proof_pack_posture import proof_pack_posture_for_wave
from src.api.services.wave_report_input import build_report_input_for_wave
from src.api.services.wave_supportability_payload import wave_supportability_payload
from src.core.mandate_repository import DpmMandateRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves import DpmWaveReportInput, DpmWaveRepository


def wave_supportability_for_id(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> dict[str, object]:
    wave = get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    return wave_supportability_payload(wave)


def wave_detail_for_id(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> dict[str, object]:
    wave = get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    return wave_detail_payload(wave)


def wave_items_for_id(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> dict[str, object]:
    wave = get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    return wave_items_payload(wave)


def wave_proof_pack_posture_for_id(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> dict[str, object]:
    wave = get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    return proof_pack_posture_for_wave(wave=wave)


def wave_report_input_for_id(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
    proof_pack_repository: DpmProofPackRepository | None = None,
    outcome_review_repository: DpmOutcomeReviewRepository | None = None,
    mandate_repository: DpmMandateRepository | None = None,
    tenant_id: str | None = None,
) -> DpmWaveReportInput:
    wave = get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    return build_report_input_for_wave(
        wave=wave,
        wave_repository=wave_repository,
        proof_pack_repository=proof_pack_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
        tenant_id=tenant_id,
    )


__all__ = [
    "wave_detail_for_id",
    "wave_items_for_id",
    "wave_proof_pack_posture_for_id",
    "wave_report_input_for_id",
    "wave_supportability_for_id",
]
