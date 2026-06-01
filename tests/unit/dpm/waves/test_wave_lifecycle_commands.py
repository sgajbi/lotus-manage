from datetime import datetime, timezone

from src.api.services import wave_lifecycle_commands
from src.api.services.wave_aggregate_metrics import aggregate_wave_items
from src.api.services.wave_lifecycle_commands import (
    approve_persisted_wave,
    cancel_persisted_wave,
    handoff_persisted_wave,
    stage_persisted_wave,
)
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem, DpmWaveTrigger


class _WaveRepository:
    def __init__(self, wave: DpmRebalanceWave) -> None:
        self.wave = wave
        self.updated_wave: DpmRebalanceWave | None = None
        self.expected_version: int | None = None

    def get_wave(self, *, wave_id: str) -> DpmRebalanceWave | None:
        if wave_id == self.wave.wave_id:
            return self.wave
        return None

    def update_wave(self, *, wave: DpmRebalanceWave, expected_version: int) -> None:
        self.updated_wave = wave
        self.expected_version = expected_version


def _item(*, state: str) -> DpmRebalanceWaveItem:
    return DpmRebalanceWaveItem(
        wave_item_id=f"dwi_{state.lower()}",
        portfolio_id=f"PB_SG_{state}",
        state=state,
    )


def _wave(*, wave_id: str, state: str, item_state: str) -> DpmRebalanceWave:
    items = [_item(state=item_state)]
    return DpmRebalanceWave(
        wave_id=wave_id,
        state=state,
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id=f"manual-{wave_id}",
            rationale="Execute governed wave lifecycle command.",
        ),
        as_of_date="2026-06-01",
        created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        created_by="pm_001",
        correlation_id=f"corr-{wave_id}",
        items=items,
        aggregate_metrics=aggregate_wave_items(items),
        version=7,
    )


def test_approve_persisted_wave_builds_and_persists_approved_transition() -> None:
    wave = _wave(wave_id="dwv_lifecycle_approve", state="SIMULATED", item_state="SELECTED")
    repository = _WaveRepository(wave)

    approved, replayed = approve_persisted_wave(
        wave_id=wave.wave_id,
        actor_id="pm_approve",
        reason_code="APPROVED_BY_PM",
        comment=None,
        correlation_id="corr-approve",
        wave_repository=repository,  # type: ignore[arg-type]
    )

    assert replayed is False
    assert approved.state == "APPROVED"
    assert repository.updated_wave is approved
    assert repository.expected_version == 7


def test_stage_handoff_and_cancel_persisted_wave_commands_update_expected_version() -> None:
    stage_source = _wave(wave_id="dwv_lifecycle_stage", state="APPROVED", item_state="APPROVED")
    stage_repository = _WaveRepository(stage_source)

    staged, stage_replayed = stage_persisted_wave(
        wave_id=stage_source.wave_id,
        actor_id="ops_stage",
        reason_code="READY_FOR_HANDOFF",
        comment=None,
        correlation_id="corr-stage",
        wave_repository=stage_repository,  # type: ignore[arg-type]
    )

    handoff_repository = _WaveRepository(staged)
    handoff_ready, handoff_replayed = handoff_persisted_wave(
        wave_id=staged.wave_id,
        actor_id="ops_handoff",
        reason_code="READY_FOR_OPERATIONS",
        comment=None,
        correlation_id="corr-handoff",
        wave_repository=handoff_repository,  # type: ignore[arg-type]
    )

    cancel_source = _wave(wave_id="dwv_lifecycle_cancel", state="STAGED", item_state="STAGED")
    cancel_repository = _WaveRepository(cancel_source)
    cancelled, cancel_replayed = cancel_persisted_wave(
        wave_id=cancel_source.wave_id,
        actor_id="pm_cancel",
        reason_code="CLIENT_CANCELLED",
        comment=None,
        correlation_id="corr-cancel",
        wave_repository=cancel_repository,  # type: ignore[arg-type]
    )

    assert stage_replayed is False
    assert staged.state == "STAGED"
    assert stage_repository.expected_version == 7
    assert handoff_replayed is False
    assert handoff_ready.state == "HANDOFF_READY"
    assert handoff_repository.expected_version == staged.version
    assert cancel_replayed is False
    assert cancelled.state == "CANCELLED"
    assert cancel_repository.expected_version == 7


def test_cancel_persisted_wave_replays_existing_cancelled_wave() -> None:
    wave = _wave(wave_id="dwv_lifecycle_cancel_replay", state="CANCELLED", item_state="EXCLUDED")
    repository = _WaveRepository(wave)

    cancelled, replayed = cancel_persisted_wave(
        wave_id=wave.wave_id,
        actor_id="pm_cancel",
        reason_code="CLIENT_CANCELLED",
        comment=None,
        correlation_id="corr-cancel",
        wave_repository=repository,  # type: ignore[arg-type]
    )

    assert cancelled is wave
    assert replayed is True
    assert repository.updated_wave is None


def test_wave_lifecycle_commands_export_public_surface() -> None:
    assert wave_lifecycle_commands.__all__ == [
        "approve_persisted_wave",
        "cancel_persisted_wave",
        "handoff_persisted_wave",
        "stage_persisted_wave",
    ]
