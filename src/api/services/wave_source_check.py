from src.api.services.wave_aggregate_metrics import aggregate_wave_items
from src.api.services.wave_event_evidence import build_wave_event
from src.api.services.wave_source_readiness import classify_item_source_readiness
from src.core.mandate_repository import DpmMandateRepository
from src.core.waves import DpmRebalanceWave, apply_wave_transition


def build_source_checked_wave(
    *,
    wave: DpmRebalanceWave,
    actor_id: str,
    correlation_id: str,
    mandate_repository: DpmMandateRepository,
    tenant_id: str,
) -> DpmRebalanceWave:
    classified_items = [
        classify_item_source_readiness(
            item=item,
            wave_as_of_date=wave.as_of_date,
            mandate_repository=mandate_repository,
            tenant_id=tenant_id,
        )
        for item in wave.items
    ]
    candidate = wave.model_copy(
        update={
            "items": classified_items,
            "aggregate_metrics": aggregate_wave_items(classified_items),
        },
        deep=True,
    )
    return apply_wave_transition(
        wave=candidate,
        to_state="SOURCE_CHECKED",
        event=build_wave_event(
            wave_id=wave.wave_id,
            from_state="CREATED",
            to_state="SOURCE_CHECKED",
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_SOURCE_CHECKED",
            metadata={
                "state_counts": candidate.aggregate_metrics.state_counts,
                "ready_item_count": candidate.aggregate_metrics.ready_item_count,
                "blocked_item_count": candidate.aggregate_metrics.blocked_item_count,
                "review_required_item_count": (
                    candidate.aggregate_metrics.review_required_item_count
                ),
                "source_degraded_item_count": (
                    candidate.aggregate_metrics.source_degraded_item_count
                ),
            },
        ),
    )


__all__ = ["build_source_checked_wave"]
