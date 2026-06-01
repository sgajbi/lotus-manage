from src.api.services.wave_creation import (
    create_created_wave_id,
    create_wave_request_hash,
    promote_preview_to_created_wave,
)
from src.api.services.wave_event_evidence import idempotency_key_hash, request_hash
from src.core.waves import (
    DpmRebalanceWave,
    DpmRebalanceWaveEvent,
    DpmWaveAggregateMetrics,
    DpmWaveTrigger,
)


def _preview_wave() -> DpmRebalanceWave:
    return DpmRebalanceWave(
        wave_id="dwv_preview_old",
        state="PREVIEWED",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-create",
            rationale="Create deterministic wave.",
        ),
        as_of_date="2026-05-03",
        created_by="pm_001",
        correlation_id="corr_create",
        items=[],
        aggregate_metrics=DpmWaveAggregateMetrics(
            item_count=0,
            state_counts={},
            ready_item_count=0,
            blocked_item_count=0,
            review_required_item_count=0,
            source_degraded_item_count=0,
        ),
        events=[
            DpmRebalanceWaveEvent(
                event_id="dwe_preview",
                wave_id="dwv_preview_old",
                from_state="DRAFT",
                to_state="PREVIEWED",
                event_type="STATE_TRANSITION",
                actor_id="pm_001",
                reason_code="WAVE_PREVIEWED",
                correlation_id="corr_create",
                metadata={"item_count": 0},
            )
        ],
    )


def test_create_wave_request_hash_uses_canonical_create_fields() -> None:
    portfolios = [{"portfolio_id": "PB_SG_CREATE"}]

    digest = create_wave_request_hash(
        trigger_type="EXPLICIT_PORTFOLIO_LIST",
        trigger_id="manual-create",
        rationale="Create deterministic wave.",
        as_of_date="2026-05-03",
        actor_id="pm_001",
        portfolios=portfolios,
    )

    assert digest == request_hash(
        {
            "trigger_type": "EXPLICIT_PORTFOLIO_LIST",
            "trigger_id": "manual-create",
            "rationale": "Create deterministic wave.",
            "as_of_date": "2026-05-03",
            "actor_id": "pm_001",
            "portfolios": portfolios,
        }
    )


def test_create_created_wave_id_uses_governed_wave_prefix(monkeypatch) -> None:
    class _Uuid:
        hex = "abcdef1234567890"

    from src.api.services import wave_creation

    monkeypatch.setattr(wave_creation.uuid, "uuid4", lambda: _Uuid())

    assert create_created_wave_id() == "dwv_abcdef123456"


def test_promote_preview_to_created_wave_rekeys_events_and_records_idempotency_hash() -> None:
    created = promote_preview_to_created_wave(
        preview=_preview_wave(),
        wave_id="dwv_created",
        actor_id="pm_001",
        correlation_id="corr_create",
        idempotency_key="idem-create",
    )

    assert created.wave_id == "dwv_created"
    assert created.state == "CREATED"
    assert [event.wave_id for event in created.events] == ["dwv_created", "dwv_created"]
    assert created.events[-1].from_state == "PREVIEWED"
    assert created.events[-1].to_state == "CREATED"
    assert created.events[-1].reason_code == "WAVE_CREATED"
    assert created.events[-1].metadata == {
        "idempotency_key_hash": idempotency_key_hash("idem-create")
    }


def test_wave_creation_exports_only_creation_helpers() -> None:
    from src.api.services import wave_creation

    assert wave_creation.__all__ == [
        "create_created_wave_id",
        "create_wave_request_hash",
        "promote_preview_to_created_wave",
    ]
