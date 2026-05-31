from src.core.portfolio_memory.wave_projection import wave_events
from src.core.waves.models import DpmWaveHandoffRef
from tests.unit.dpm.api.test_portfolio_memory_api import PORTFOLIO_ID, _wave


def test_wave_created_event_projects_matching_item_context_and_source_refs() -> None:
    wave = _wave()

    event = wave_events(wave=wave, portfolio_id=PORTFOLIO_ID)[0]

    assert event.event_type == "WAVE_CREATED"
    assert event.source_type == "DPM_REBALANCE_WAVE"
    assert event.source_id == wave.wave_id
    assert event.supportability_state == "READY"
    assert event.reason_codes == ["WAVE_ITEM_HANDOFF_READY"]
    assert event.source_refs[0].source_system == "lotus-core"
    assert event.metadata["trigger_type"] == "PM_BOOK_REVIEW"
    assert event.metadata["matching_item_count"] == 1


def test_wave_state_event_preserves_transition_metadata() -> None:
    wave = _wave()

    state_event = [
        event
        for event in wave_events(wave=wave, portfolio_id=PORTFOLIO_ID)
        if event.event_type == "WAVE_EVENT"
    ][0]

    assert state_event.source_type == "STATE_TRANSITION"
    assert state_event.status == "HANDOFF_READY"
    assert state_event.metadata["from_state"] == "STAGED"
    assert state_event.metadata["to_state"] == "HANDOFF_READY"
    assert state_event.metadata["correlation_id"] == "corr-wave-handoff"


def test_wave_handoff_event_preserves_no_external_execution_boundary() -> None:
    wave = _wave().model_copy(
        update={
            "handoff_refs": [
                *_wave().handoff_refs,
                DpmWaveHandoffRef(
                    handoff_ref_id="dwh_unrelated",
                    wave_id="dwv_001",
                    item_ids=["dwi_other"],
                    actor_id="ops_001",
                    reason_code="READY_FOR_OPERATIONS_REVIEW",
                    correlation_id="corr-handoff-unrelated",
                    external_execution_claimed=False,
                    content_hash="sha256:handoff-unrelated",
                    created_at=_wave().handoff_refs[0].created_at,
                ),
            ]
        }
    )

    handoff_events = [
        event
        for event in wave_events(wave=wave, portfolio_id=PORTFOLIO_ID)
        if event.event_type == "WAVE_HANDOFF_READY"
    ]

    assert len(handoff_events) == 1
    assert handoff_events[0].source_id == "dwh_001"
    assert handoff_events[0].artifact_refs[0].content_hash == "sha256:handoff-memory"
    assert handoff_events[0].metadata["external_execution_claimed"] is False
