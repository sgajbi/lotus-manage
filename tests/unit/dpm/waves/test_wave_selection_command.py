from src.api.services import wave_selection_command
from src.api.services.wave_selection_command import select_persisted_wave_item_alternative
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem


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


def _wave() -> DpmRebalanceWave:
    return DpmRebalanceWave.model_construct(
        wave_id="dwv_selection_command",
        state="SIMULATED",
        version=6,
        items=[
            DpmRebalanceWaveItem(
                wave_item_id="dwi_selection_command",
                portfolio_id="PB_SG_SELECTION_COMMAND",
                state="SIMULATED",
                alternative_set_id="cas_selection_command",
            )
        ],
    )


def test_select_persisted_wave_item_alternative_records_selection_and_persists(
    monkeypatch,
) -> None:
    wave = _wave()
    repository = _WaveRepository(wave)
    captured: dict[str, object] = {}
    transitioned = wave.model_copy(update={"version": 7}, deep=True)

    def _select_construction_alternative_for_wave(**kwargs: object) -> None:
        captured["selection"] = kwargs

    def _build_wave_with_selected_item_alternative(**kwargs: object) -> DpmRebalanceWave:
        captured["build"] = kwargs
        return transitioned

    monkeypatch.setattr(
        wave_selection_command,
        "select_construction_alternative_for_wave",
        _select_construction_alternative_for_wave,
    )
    monkeypatch.setattr(
        wave_selection_command,
        "build_wave_with_selected_item_alternative",
        _build_wave_with_selected_item_alternative,
    )

    selected = select_persisted_wave_item_alternative(
        wave_id=wave.wave_id,
        wave_item_id="dwi_selection_command",
        alternative_id="alt_selected",
        actor_id="pm_select",
        reason_code="CLIENT_PREFERENCE",
        comment="Client preference.",
        correlation_id="corr-select",
        generate_proof_pack=True,
        construction_repository=object(),  # type: ignore[arg-type]
        proof_pack_repository=object(),  # type: ignore[arg-type]
        mandate_repository=object(),  # type: ignore[arg-type]
        run_service=object(),  # type: ignore[arg-type]
        wave_repository=repository,  # type: ignore[arg-type]
        tenant_id="tenant-test",
    )

    assert selected is transitioned
    assert repository.updated_wave is transitioned
    assert repository.expected_version == 6
    assert captured["selection"]["alternative_set_id"] == "cas_selection_command"
    assert captured["selection"]["alternative_id"] == "alt_selected"
    assert captured["build"]["selected_item"] is wave.items[0]
    assert captured["build"]["generate_proof_pack"] is True


def test_wave_selection_command_exports_public_surface() -> None:
    assert wave_selection_command.__all__ == ["select_persisted_wave_item_alternative"]
