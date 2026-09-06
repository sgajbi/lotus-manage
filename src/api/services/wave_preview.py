from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import cast

from src.api.services.wave_aggregate_metrics import aggregate_wave_items
from src.api.services.wave_event_evidence import build_wave_event
from src.api.services.wave_item_builder import build_wave_item
from src.api.services.wave_portfolio_sources import trigger_source_refs
from src.api.services.wave_trigger_validation import validate_trigger_or_raise
from src.core.mandate_repository import DpmMandateRepository
from src.core.waves import (
    DpmRebalanceWave,
    DpmWaveTrigger,
    WaveTriggerType,
    apply_wave_transition,
)


def build_preview_wave(
    *,
    trigger_type: str,
    trigger_id: str,
    rationale: str,
    as_of_date: str,
    actor_id: str,
    correlation_id: str,
    portfolios: list[dict[str, object]],
    mandate_repository: DpmMandateRepository,
    tenant_id: str,
) -> DpmRebalanceWave:
    validate_trigger_or_raise(trigger_type, portfolios=portfolios)
    validated_trigger_type = cast(WaveTriggerType, trigger_type)
    items = [
        build_wave_item(
            index=index,
            portfolio=portfolio,
            mandate_repository=mandate_repository,
            tenant_id=tenant_id,
        )
        for index, portfolio in enumerate(portfolios, start=1)
    ]
    wave = DpmRebalanceWave(
        wave_id=f"dwv_preview_{uuid.uuid4().hex[:12]}",
        state="DRAFT",
        trigger=DpmWaveTrigger(
            trigger_type=validated_trigger_type,
            trigger_id=trigger_id,
            rationale=rationale,
            source_refs=trigger_source_refs(portfolios),
        ),
        as_of_date=as_of_date,
        created_at=datetime.now(timezone.utc),
        created_by=actor_id,
        correlation_id=correlation_id,
        items=items,
        aggregate_metrics=aggregate_wave_items(items),
    )
    return apply_wave_transition(
        wave=wave,
        to_state="PREVIEWED",
        event=build_wave_event(
            wave_id=wave.wave_id,
            from_state="DRAFT",
            to_state="PREVIEWED",
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_PREVIEWED",
            metadata={"item_count": len(items)},
        ),
    )


__all__ = ["build_preview_wave"]
