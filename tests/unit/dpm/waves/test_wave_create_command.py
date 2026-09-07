from src.api.services import wave_create_command
from src.api.services.wave_create_command import create_persisted_wave
from src.api.services.wave_creation import create_wave_request_hash
from src.core.mandates import DpmMandateDigitalTwin
from src.core.waves import DpmRebalanceWave
from src.core.waves.repository import wave_idempotency_mapping_key
from src.infrastructure.waves import InMemoryDpmWaveRepository


class _MandateRepository:
    def get_latest_mandate_by_portfolio(
        self,
        *,
        portfolio_id: str,
        tenant_id: str,
    ) -> DpmMandateDigitalTwin | None:
        return None


class _WaveRepository:
    def __init__(self, existing: DpmRebalanceWave | None = None) -> None:
        self.existing = existing
        self.idempotency_lookups: list[str] = []
        self.idempotency_tenants: list[str] = []
        self.saved_wave: DpmRebalanceWave | None = None
        self.idempotency_key: str | None = None
        self.request_hash: str | None = None

    def get_wave_by_idempotency(
        self, *, idempotency_key: str, tenant_id: str
    ) -> DpmRebalanceWave | None:
        self.idempotency_lookups.append(idempotency_key)
        self.idempotency_tenants.append(tenant_id)
        return self.existing

    def save_wave(
        self,
        *,
        wave: DpmRebalanceWave,
        idempotency_key: str | None,
        request_hash: str | None,
        tenant_id: str,
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


def _request_for(*, tenant_id: str) -> dict[str, object]:
    """The same create request under a stated tenant.

    Everything except the tenant is held constant, so a difference in outcome
    can only come from the tenant - the divergence the fix is about.
    """

    return {
        "trigger_type": "EXPLICIT_PORTFOLIO_LIST",
        "trigger_id": "manual-create-command",
        "rationale": "Create command tenant isolation.",
        "as_of_date": "2026-06-01",
        "actor_id": "pm_001",
        "correlation_id": "corr-create-command",
        "portfolios": _portfolios(),
        "tenant_id": tenant_id,
    }


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
        tenant_id="tenant-test",
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
        tenant_id="tenant-test",
    )

    assert wave is repository.saved_wave
    assert replayed is False
    assert wave.wave_id == "dwv_created"
    assert wave.state == "CREATED"
    assert repository.idempotency_key == "idem-create-command"
    assert repository.request_hash == create_wave_request_hash(
        tenant_id="tenant-test",
        trigger_type="EXPLICIT_PORTFOLIO_LIST",
        trigger_id="manual-create-command",
        rationale="Create command persists.",
        as_of_date="2026-06-01",
        actor_id="pm_001",
        portfolios=portfolios,
    )


def test_wave_create_command_exports_public_surface() -> None:
    assert wave_create_command.__all__ == ["create_persisted_wave"]


def test_one_tenant_cannot_replay_another_tenants_wave_through_a_shared_key() -> None:
    """Idempotency keys are caller-chosen, so two tenants can present the same one.

    The create path looked a wave up by that key alone and returned whatever it
    found, so the second tenant received the FIRST tenant's wave - another
    client's portfolios, returned as its own and indistinguishable from a
    legitimate replay (issue #648).

    Adding the tenant to create_wave_request_hash did not close this, which is
    the part worth pinning: the hash was written on save and never compared on
    the lookup path, so the tenant it carried never entered the replay
    decision. This exercises the real repository rather than a fake, because a
    fake that returns its configured wave regardless of tenant cannot fail.
    """

    repository = InMemoryDpmWaveRepository()
    shared_key = "idem-shared-by-two-tenants"

    first, first_replayed = create_persisted_wave(
        **_request_for(tenant_id="tenant-a"),
        idempotency_key=shared_key,
        mandate_repository=_MandateRepository(),
        wave_repository=repository,
    )
    second, second_replayed = create_persisted_wave(
        **_request_for(tenant_id="tenant-b"),
        idempotency_key=shared_key,
        mandate_repository=_MandateRepository(),
        wave_repository=repository,
    )

    assert first_replayed is False
    assert second_replayed is False
    assert second.wave_id != first.wave_id

    # Convergence half: a genuine retry within one tenant still replays, so the
    # fix refuses cross-tenant reuse without breaking idempotency itself.
    replay, replayed = create_persisted_wave(
        **_request_for(tenant_id="tenant-a"),
        idempotency_key=shared_key,
        mandate_repository=_MandateRepository(),
        wave_repository=repository,
    )
    assert replayed is True
    assert replay.wave_id == first.wave_id


def test_the_stored_mapping_key_is_injective_across_tenant_and_key() -> None:
    """Joining tenant and key would let one pair forge another's mapping.

    Both components are caller-influenced, so a separator either may contain
    makes the encoding ambiguous - ('a', 'b:c') and ('a:b', 'c') would collide
    and one tenant would replay the other's wave through the collision.
    """

    assert wave_idempotency_mapping_key(
        tenant_id="a", idempotency_key="b_c"
    ) != wave_idempotency_mapping_key(tenant_id="a_b", idempotency_key="c")
    assert wave_idempotency_mapping_key(
        tenant_id="tenant-a", idempotency_key="k"
    ) != wave_idempotency_mapping_key(tenant_id="tenant-b", idempotency_key="k")
    # Divergence needs a convergence half: the derivation must be stable, or
    # every retry would look like a different tenant.
    assert wave_idempotency_mapping_key(
        tenant_id="tenant-a", idempotency_key="k"
    ) == wave_idempotency_mapping_key(tenant_id="tenant-a", idempotency_key="k")
