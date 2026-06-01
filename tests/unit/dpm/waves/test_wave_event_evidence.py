import re

from src.api.services.wave_event_evidence import (
    build_wave_event,
    idempotency_key_hash,
    request_hash,
)


def test_build_wave_event_sets_audit_fields_and_metadata() -> None:
    event = build_wave_event(
        wave_id="dwv_event",
        from_state="DRAFT",
        to_state="PREVIEWED",
        actor_id="pm_001",
        correlation_id="corr-event",
        reason_code="WAVE_PREVIEWED",
        metadata={"item_count": 2},
    )

    assert re.fullmatch(r"dwe_[0-9a-f]{12}", event.event_id)
    assert event.wave_id == "dwv_event"
    assert event.from_state == "DRAFT"
    assert event.to_state == "PREVIEWED"
    assert event.event_type == "STATE_TRANSITION"
    assert event.actor_id == "pm_001"
    assert event.reason_code == "WAVE_PREVIEWED"
    assert event.correlation_id == "corr-event"
    assert event.metadata == {"item_count": 2}


def test_build_wave_event_accepts_custom_event_type() -> None:
    event = build_wave_event(
        wave_id="dwv_event",
        from_state="SIMULATED",
        to_state="SIMULATED",
        actor_id="pm_001",
        correlation_id="corr-event",
        reason_code="ALTERNATIVE_SELECTED",
        metadata={"wave_item_id": "dwi_001"},
        event_type="ITEM_SELECTION",
    )

    assert event.event_type == "ITEM_SELECTION"
    assert event.metadata == {"wave_item_id": "dwi_001"}


def test_request_hash_is_stable_for_key_order() -> None:
    assert request_hash({"b": 2, "a": 1}) == request_hash({"a": 1, "b": 2})
    assert request_hash({"a": 1}).startswith("sha256:")


def test_idempotency_key_hash_is_stable_without_hash_prefix() -> None:
    assert idempotency_key_hash("wave-key") == idempotency_key_hash("wave-key")
    assert not idempotency_key_hash("wave-key").startswith("sha256:")


def test_wave_event_evidence_exports_only_event_helpers() -> None:
    from src.api.services import wave_event_evidence

    assert wave_event_evidence.__all__ == [
        "build_wave_event",
        "idempotency_key_hash",
        "request_hash",
    ]
