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
    tenant_id: str,
) -> dict[str, object]:
    wave = get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository, tenant_id=tenant_id)
    return wave_supportability_payload(wave)


def wave_detail_for_id(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
    tenant_id: str,
) -> dict[str, object]:
    wave = get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository, tenant_id=tenant_id)
    return wave_detail_payload(wave)


def wave_items_for_id(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
    tenant_id: str,
) -> dict[str, object]:
    wave = get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository, tenant_id=tenant_id)
    return wave_items_payload(wave)


def wave_proof_pack_posture_for_id(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
    tenant_id: str,
) -> dict[str, object]:
    wave = get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository, tenant_id=tenant_id)
    return proof_pack_posture_for_wave(wave=wave)


def wave_report_input_for_id(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
    tenant_id: str,
    proof_pack_repository: DpmProofPackRepository | None = None,
    outcome_review_repository: DpmOutcomeReviewRepository | None = None,
    mandate_repository: DpmMandateRepository | None = None,
) -> DpmWaveReportInput:
    # The tenant was previously optional here with a None default. A fenced
    # read cannot have an optional tenant: the default would silently mean
    # "unscoped", which is the state issue #677 removes. It is now the
    # required parameter above.
    wave = get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository, tenant_id=tenant_id)
    return build_report_input_for_wave(
        wave=wave,
        wave_repository=wave_repository,
        tenant_id=tenant_id,
        proof_pack_repository=proof_pack_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
    )


__all__ = [
    "wave_detail_for_id",
    "wave_items_for_id",
    "wave_proof_pack_posture_for_id",
    "wave_report_input_for_id",
    "wave_supportability_for_id",
]
