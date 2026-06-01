from src.api.services.wave_creation import (
    create_created_wave_id,
    create_wave_request_hash,
    promote_preview_to_created_wave,
)
from src.api.services.wave_persistence import save_wave_or_raise
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
    mandate_repository: DpmMandateRepository,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    request_hash = create_wave_request_hash(
        trigger_type=trigger_type,
        trigger_id=trigger_id,
        rationale=rationale,
        as_of_date=as_of_date,
        actor_id=actor_id,
        portfolios=portfolios,
    )
    existing = wave_repository.get_wave_by_idempotency(idempotency_key=idempotency_key)
    if existing is not None:
        return existing, True

    preview = build_preview_wave(
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
    save_wave_or_raise(
        wave_repository=wave_repository,
        wave=wave,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    return wave, False


__all__ = ["create_persisted_wave"]
