from src.api.services import wave_create_command
from src.api.services.wave_create_command import create_persisted_wave
from src.api.services.wave_creation import create_wave_request_hash
from src.core.mandates import DpmMandateDigitalTwin
from src.core.waves import DpmRebalanceWave


class _MandateRepository:
    def get_latest_mandate_by_portfolio(
        self,
        *,
        portfolio_id: str,
    ) -> DpmMandateDigitalTwin | None:
        return None


class _WaveRepository:
    def __init__(self, existing: DpmRebalanceWave | None = None) -> None:
        self.existing = existing
        self.idempotency_lookups: list[str] = []
        self.saved_wave: DpmRebalanceWave | None = None
        self.idempotency_key: str | None = None
        self.request_hash: str | None = None

    def get_wave_by_idempotency(self, *, idempotency_key: str) -> DpmRebalanceWave | None:
        self.idempotency_lookups.append(idempotency_key)
        return self.existing

    def save_wave(
        self,
        *,
        wave: DpmRebalanceWave,
        idempotency_key: str | None,
        request_hash: str | None,
    ) -> None:
        self.saved_wave = wave
        self.idempotency_key = idempotency_key
        self.request_hash = request_hash


def _source_ref() -> dict[str, object]:
    return {
        "source_system": "lotus-core",
        "source_type": "PORTFOLIO_SNAPSHOT",
        "source_id": "snapshot_create_command",
        "source_version": "2026-06-01",
        "supportability_state": "READY",
    }


def _portfolios() -> list[dict[str, object]]:
    return [{"portfolio_id": "PB_SG_CREATE_COMMAND", "source_refs": [_source_ref()]}]


def test_create_persisted_wave_replays_existing_idempotent_wave() -> None:
    existing = DpmRebalanceWave.model_construct(wave_id="dwv_existing", state="CREATED")
    repository = _WaveRepository(existing=existing)

    wave, replayed = create_persisted_wave(
        trigger_type="EXPLICIT_PORTFOLIO_LIST",
        trigger_id="manual-create-command",
        rationale="Create command replay.",
        as_of_date="2026-06-01",
        actor_id="pm_001",
        correlation_id="corr-create-command",
        portfolios=_portfolios(),
        idempotency_key="idem-create-command",
        mandate_repository=_MandateRepository(),  # type: ignore[arg-type]
        wave_repository=repository,  # type: ignore[arg-type]
    )

    assert wave is existing
    assert replayed is True
    assert repository.idempotency_lookups == ["idem-create-command"]
    assert repository.saved_wave is None


def test_create_persisted_wave_promotes_preview_and_persists_request_hash(
    monkeypatch,
) -> None:
    repository = _WaveRepository()
    portfolios = _portfolios()
    monkeypatch.setattr(wave_create_command, "create_created_wave_id", lambda: "dwv_created")

    wave, replayed = create_persisted_wave(
        trigger_type="EXPLICIT_PORTFOLIO_LIST",
        trigger_id="manual-create-command",
        rationale="Create command persists.",
        as_of_date="2026-06-01",
        actor_id="pm_001",
        correlation_id="corr-create-command",
        portfolios=portfolios,
        idempotency_key="idem-create-command",
        mandate_repository=_MandateRepository(),  # type: ignore[arg-type]
        wave_repository=repository,  # type: ignore[arg-type]
    )

    assert wave is repository.saved_wave
    assert replayed is False
    assert wave.wave_id == "dwv_created"
    assert wave.state == "CREATED"
    assert repository.idempotency_key == "idem-create-command"
    assert repository.request_hash == create_wave_request_hash(
        trigger_type="EXPLICIT_PORTFOLIO_LIST",
        trigger_id="manual-create-command",
        rationale="Create command persists.",
        as_of_date="2026-06-01",
        actor_id="pm_001",
        portfolios=portfolios,
    )


def test_wave_create_command_exports_public_surface() -> None:
    assert wave_create_command.__all__ == ["create_persisted_wave"]
