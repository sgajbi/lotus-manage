"""Wave source-event projection helpers for portfolio memory."""

from src.core.portfolio_memory.models import (
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemorySourceRef,
)
from src.core.portfolio_memory.source_refs import wave_source_refs
from src.core.portfolio_memory.supportability import source_supportability_state
from src.core.waves.models import (
    DpmRebalanceWave,
    DpmRebalanceWaveEvent,
    DpmRebalanceWaveItem,
    DpmWaveHandoffRef,
)


def wave_events(*, wave: DpmRebalanceWave, portfolio_id: str) -> list[DpmPortfolioMemoryEvent]:
    matching_items = [item for item in wave.items if item.portfolio_id == portfolio_id]
    item_ids = {item.wave_item_id for item in matching_items}
    refs = wave_source_refs(wave=wave, items=matching_items)
    events = [_wave_created_event(wave=wave, matching_items=matching_items, refs=refs)]
    events.extend(_wave_state_events(wave=wave, refs=refs))
    for handoff in wave.handoff_refs:
        if item_ids and not item_ids.intersection(handoff.item_ids):
            continue
        events.append(_handoff_event(wave=wave, handoff=handoff, refs=refs))
    return events


def _wave_created_event(
    *,
    wave: DpmRebalanceWave,
    matching_items: list[DpmRebalanceWaveItem],
    refs: list[DpmPortfolioMemorySourceRef],
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:wave:{wave.wave_id}:created",
        event_type="WAVE_CREATED",
        event_time=wave.created_at.isoformat(),
        actor=wave.created_by,
        source_system="lotus-manage",
        source_type="DPM_REBALANCE_WAVE",
        source_id=wave.wave_id,
        status=wave.state,
        supportability_state=source_supportability_state(wave.state),
        summary=f"Rebalance wave {wave.wave_id} created for trigger {wave.trigger.trigger_type}.",
        reason_codes=sorted({reason for item in matching_items for reason in item.reason_codes}),
        source_refs=refs,
        content_hash=None,
        metadata={
            "trigger_type": wave.trigger.trigger_type,
            "trigger_id": wave.trigger.trigger_id,
            "as_of_date": wave.as_of_date,
            "matching_item_count": len(matching_items),
        },
    )


def _wave_state_events(
    *,
    wave: DpmRebalanceWave,
    refs: list[DpmPortfolioMemorySourceRef],
) -> list[DpmPortfolioMemoryEvent]:
    return [
        DpmPortfolioMemoryEvent(
            event_id=f"memory:wave:{wave.wave_id}:event:{event.event_id}",
            event_type="WAVE_EVENT",
            event_time=event.created_at.isoformat(),
            actor=event.actor_id,
            source_system="lotus-manage",
            source_type=event.event_type,
            source_id=event.event_id,
            status=event.to_state,
            supportability_state=source_supportability_state(event.to_state),
            summary=f"Wave event {event.event_type} moved wave to {event.to_state}.",
            reason_codes=[event.reason_code],
            source_refs=refs,
            content_hash=None,
            metadata=wave_event_metadata(event),
        )
        for event in wave.events
    ]


def _handoff_event(
    *,
    wave: DpmRebalanceWave,
    handoff: DpmWaveHandoffRef,
    refs: list[DpmPortfolioMemorySourceRef],
) -> DpmPortfolioMemoryEvent:
    return DpmPortfolioMemoryEvent(
        event_id=f"memory:wave:{wave.wave_id}:handoff:{handoff.handoff_ref_id}",
        event_type="WAVE_HANDOFF_READY",
        event_time=handoff.created_at.isoformat(),
        actor=handoff.actor_id,
        source_system="lotus-manage",
        source_type="DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF",
        source_id=handoff.handoff_ref_id,
        status=wave.state,
        supportability_state=source_supportability_state(wave.state),
        summary="Internal operations handoff evidence recorded without external execution claim.",
        reason_codes=[handoff.reason_code],
        source_refs=refs,
        artifact_refs=[
            DpmPortfolioMemorySourceRef(
                source_system="lotus-manage",
                source_type="DPM_WAVE_INTERNAL_OPERATIONS_HANDOFF",
                source_id=handoff.handoff_ref_id,
                content_hash=handoff.content_hash,
            )
        ],
        content_hash=handoff.content_hash,
        metadata={
            "wave_id": wave.wave_id,
            "item_count": len(handoff.item_ids),
            "external_execution_claimed": handoff.external_execution_claimed,
        },
    )


def wave_event_metadata(event: DpmRebalanceWaveEvent) -> dict[str, object]:
    metadata = dict(event.metadata)
    metadata["from_state"] = event.from_state
    metadata["to_state"] = event.to_state
    metadata["correlation_id"] = event.correlation_id
    return metadata
