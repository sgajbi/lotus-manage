from src.api.services.wave_creation import (
    create_created_wave_id,
    create_wave_request_hash,
    promote_preview_to_created_wave,
)
from src.api.services.wave_persistence import save_wave_or_raise
from src.api.services.wave_errors import DpmWaveValidationError
from src.api.services.wave_preview import build_preview_wave
from src.core.mandate_repository import DpmMandateRepository
from src.core.waves import DpmRebalanceWave, DpmWaveRepository


def create_persisted_wave(
    *,
    trigger_type: str,
    trigger_id: str,
    rationale: str,
    as_of_date: str,
    actor_id: str,
    correlation_id: str,
    portfolios: list[dict[str, object]],
    idempotency_key: str,
    tenant_id: str,
    mandate_repository: DpmMandateRepository,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    request_hash = create_wave_request_hash(
        tenant_id=tenant_id,
        trigger_type=trigger_type,
        trigger_id=trigger_id,
        rationale=rationale,
        as_of_date=as_of_date,
        actor_id=actor_id,
        portfolios=portfolios,
    )
    # Looking up by the caller-chosen key alone served whichever wave claimed
    # that key first, so a second tenant reusing the key was handed the first
    # tenant's wave as a replay (issue #648). The lookup is now tenant-scoped:
    # another tenant's mapping is not found rather than found and refused,
    # because refusing would disclose that some other tenant holds that key.
    existing = wave_repository.get_wave_idempotency_record(
        idempotency_key=idempotency_key,
        tenant_id=tenant_id,
    )
    if existing is not None:
        if existing.request_hash != request_hash:
            raise DpmWaveValidationError("WAVE_CREATE_CONFLICT", "DPM_WAVE_IDEMPOTENCY_CONFLICT")
        return existing.wave, True

    preview = build_preview_wave(
        tenant_id=tenant_id,
        trigger_type=trigger_type,
        trigger_id=trigger_id,
        rationale=rationale,
        as_of_date=as_of_date,
        actor_id=actor_id,
        correlation_id=correlation_id,
        portfolios=portfolios,
        mandate_repository=mandate_repository,
    )
    wave = promote_preview_to_created_wave(
        preview=preview,
        wave_id=create_created_wave_id(),
        actor_id=actor_id,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
    )
    try:
        save_wave_or_raise(
            wave_repository=wave_repository,
            wave=wave,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            tenant_id=tenant_id,
        )
    except DpmWaveValidationError as exc:
        if str(exc) not in {
            "DPM_WAVE_CORRELATION_CONFLICT",
            "DPM_WAVE_IDEMPOTENCY_CONFLICT",
        }:
            raise
        winner = wave_repository.get_wave_idempotency_record(
            idempotency_key=idempotency_key, tenant_id=tenant_id
        )
        if winner is None or winner.request_hash != request_hash:
            raise
        return winner.wave, True
    return wave, False


__all__ = ["create_persisted_wave"]
