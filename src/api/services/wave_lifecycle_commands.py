from src.api.services.wave_approval_transition import build_approved_wave
from src.api.services.wave_cancel_transition import build_cancelled_wave
from src.api.services.wave_handoff_transition import build_handoff_ready_wave
from src.api.services.wave_stage_transition import build_staged_wave
from src.api.services.wave_transition_execution import (
    persist_transitioned_wave,
    prepare_wave_transition,
)
from src.core.waves import DpmRebalanceWave, DpmWaveRepository


def approve_persisted_wave(
    *,
    wave_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    prepared = prepare_wave_transition(
        wave_id=wave_id,
        wave_repository=wave_repository,
        replay_states={"APPROVED", "APPROVED_WITH_EXCEPTIONS"},
        allowed_states={"SIMULATED", "PARTIALLY_SIMULATED", "REVIEW_REQUIRED"},
        error_code="DPM_WAVE_APPROVAL_INVALID_STATE",
        action_phrase="be approved",
    )
    if prepared.replayed:
        return prepared.wave, True

    approved = build_approved_wave(
        wave=prepared.wave,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
    )
    persist_transitioned_wave(
        wave_repository=wave_repository,
        source_wave=prepared.wave,
        transitioned_wave=approved,
    )
    return approved, False


def stage_persisted_wave(
    *,
    wave_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    prepared = prepare_wave_transition(
        wave_id=wave_id,
        wave_repository=wave_repository,
        replay_states={"STAGED", "HANDOFF_READY"},
        allowed_states={"APPROVED", "APPROVED_WITH_EXCEPTIONS"},
        error_code="DPM_WAVE_STAGE_INVALID_STATE",
        action_phrase="be staged",
    )
    if prepared.replayed:
        return prepared.wave, True

    staged = build_staged_wave(
        wave=prepared.wave,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
    )
    persist_transitioned_wave(
        wave_repository=wave_repository,
        source_wave=prepared.wave,
        transitioned_wave=staged,
    )
    return staged, False


def handoff_persisted_wave(
    *,
    wave_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    prepared = prepare_wave_transition(
        wave_id=wave_id,
        wave_repository=wave_repository,
        replay_states={"HANDOFF_READY"},
        allowed_states={"STAGED"},
        error_code="DPM_WAVE_HANDOFF_INVALID_STATE",
        action_phrase="create handoff evidence",
    )
    if prepared.replayed:
        return prepared.wave, True

    handoff_ready = build_handoff_ready_wave(
        wave=prepared.wave,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
    )
    persist_transitioned_wave(
        wave_repository=wave_repository,
        source_wave=prepared.wave,
        transitioned_wave=handoff_ready,
    )
    return handoff_ready, False


def cancel_persisted_wave(
    *,
    wave_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    prepared = prepare_wave_transition(
        wave_id=wave_id,
        wave_repository=wave_repository,
        replay_states={"CANCELLED"},
        allowed_states=None,
        error_code="DPM_WAVE_CANCEL_INVALID_STATE",
        action_phrase="be cancelled",
    )
    if prepared.replayed:
        return prepared.wave, True

    cancelled = build_cancelled_wave(
        wave=prepared.wave,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
    )
    persist_transitioned_wave(
        wave_repository=wave_repository,
        source_wave=prepared.wave,
        transitioned_wave=cancelled,
    )
    return cancelled, False


__all__ = [
    "approve_persisted_wave",
    "cancel_persisted_wave",
    "handoff_persisted_wave",
    "stage_persisted_wave",
]
