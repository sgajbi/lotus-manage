from src.api.services import wave_preparation_commands
from src.api.services.wave_preparation_commands import (
    simulate_persisted_wave,
    source_check_persisted_wave,
)
from src.core.mandates import DpmMandateDigitalTwin, DpmMandateHealthSnapshot
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem, DpmWaveAggregateMetrics


class _MandateRepository:
    def get_latest_mandate(
        self,
        *,
        mandate_id: str,
    ) -> DpmMandateDigitalTwin | None:
        return None

    def get_latest_mandate_by_portfolio(
        self,
        *,
        portfolio_id: str,
    ) -> DpmMandateDigitalTwin | None:
        return None

    def get_latest_health_snapshot(
        self,
        *,
        mandate_id: str,
    ) -> DpmMandateHealthSnapshot | None:
        return None


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


def _wave(*, state: str, item_state: str, version: int = 4) -> DpmRebalanceWave:
    item = DpmRebalanceWaveItem(
        wave_item_id=f"dwi_{item_state.lower()}",
        portfolio_id=f"PB_SG_{item_state}",
        state=item_state,
    )
    return DpmRebalanceWave.model_construct(
        wave_id=f"dwv_{state.lower()}",
        state=state,
        as_of_date="2026-06-01",
        version=version,
        items=[item],
        aggregate_metrics=DpmWaveAggregateMetrics(
            item_count=1,
            state_counts={item_state: 1},
            ready_item_count=1,
            blocked_item_count=0,
            review_required_item_count=0,
            source_degraded_item_count=0,
        ),
        events=[],
    )


def test_source_check_persisted_wave_classifies_and_persists_transition() -> None:
    wave = _wave(state="CREATED", item_state="CANDIDATE")
    repository = _WaveRepository(wave)

    checked, replayed = source_check_persisted_wave(
        wave_id=wave.wave_id,
        actor_id="pm_source",
        correlation_id="corr-source",
        mandate_repository=_MandateRepository(),  # type: ignore[arg-type]
        wave_repository=repository,  # type: ignore[arg-type]
    )

    assert replayed is False
    assert checked.state == "SOURCE_CHECKED"
    assert checked.items[0].state == "SOURCE_BLOCKED"
    assert repository.updated_wave is checked
    assert repository.expected_version == 4


def test_simulate_persisted_wave_blocks_missing_inputs_and_persists_transition() -> None:
    wave = _wave(state="SOURCE_CHECKED", item_state="SOURCE_READY")
    repository = _WaveRepository(wave)

    simulated, replayed = simulate_persisted_wave(
        wave_id=wave.wave_id,
        actor_id="pm_simulate",
        correlation_id="corr-simulate",
        item_inputs={},
        methods=None,
        construction_repository=object(),  # type: ignore[arg-type]
        run_service=object(),  # type: ignore[arg-type]
        wave_repository=repository,  # type: ignore[arg-type]
    )

    assert replayed is False
    assert simulated.state == "SIMULATION_FAILED"
    assert simulated.items[0].state == "SIMULATION_BLOCKED"
    assert repository.updated_wave is simulated
    assert repository.expected_version == 4


def test_simulate_persisted_wave_replays_completed_simulation() -> None:
    wave = _wave(state="SIMULATION_FAILED", item_state="SIMULATION_BLOCKED")
    repository = _WaveRepository(wave)

    simulated, replayed = simulate_persisted_wave(
        wave_id=wave.wave_id,
        actor_id="pm_simulate",
        correlation_id="corr-simulate",
        item_inputs={},
        methods=None,
        construction_repository=object(),  # type: ignore[arg-type]
        run_service=object(),  # type: ignore[arg-type]
        wave_repository=repository,  # type: ignore[arg-type]
    )

    assert simulated is wave
    assert replayed is True
    assert repository.updated_wave is None


def test_wave_preparation_commands_export_public_surface() -> None:
    assert wave_preparation_commands.__all__ == [
        "simulate_persisted_wave",
        "source_check_persisted_wave",
    ]
