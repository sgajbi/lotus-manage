from datetime import datetime, timezone

from src.api.services.wave_search import search_wave_summaries
from src.core.waves import (
    DpmRebalanceWave,
    DpmRebalanceWaveEvent,
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveTrigger,
)


class _WaveRepository:
    def __init__(self, waves: list[DpmRebalanceWave]) -> None:
        self.waves = waves
        self.filters: dict[str, object] = {}

    def list_waves(
        self,
        *,
        state: str | None,
        trigger_type: str | None,
        as_of_date: str | None,
        limit: int,
        offset: int,
    ) -> list[DpmRebalanceWave]:
        self.filters = {
            "state": state,
            "trigger_type": trigger_type,
            "as_of_date": as_of_date,
            "limit": limit,
            "offset": offset,
        }
        return self.waves


def _wave(
    *,
    wave_id: str,
    item_state: str,
    event_reason: str = "WAVE_CREATED",
) -> DpmRebalanceWave:
    return DpmRebalanceWave.model_construct(
        wave_id=wave_id,
        state="SOURCE_CHECKED",
        trigger=DpmWaveTrigger.model_construct(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-review",
        ),
        as_of_date="2026-05-03",
        created_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
        created_by="pm_001",
        items=[
            DpmRebalanceWaveItem(
                wave_item_id=f"{wave_id}_item",
                portfolio_id="PB_SG_SEARCH",
                state=item_state,
            )
        ],
        aggregate_metrics=DpmWaveAggregateMetrics(
            item_count=1,
            state_counts={item_state: 1},
            ready_item_count=1 if item_state == "SOURCE_READY" else 0,
            blocked_item_count=1 if item_state == "SOURCE_BLOCKED" else 0,
            review_required_item_count=0,
            source_degraded_item_count=0,
        ),
        events=[
            DpmRebalanceWaveEvent.model_construct(
                event_type="STATE_TRANSITION",
                reason_code=event_reason,
            )
        ],
    )


def test_search_wave_summaries_projects_summary_fields_and_repository_filters() -> None:
    repository = _WaveRepository([_wave(wave_id="dwv_ready", item_state="SOURCE_READY")])

    summaries = search_wave_summaries(
        wave_repository=repository,  # type: ignore[arg-type]
        state="SOURCE_CHECKED",
        trigger_type="EXPLICIT_PORTFOLIO_LIST",
        as_of_date="2026-05-03",
        limit=10,
        offset=5,
    )

    assert repository.filters == {
        "state": "SOURCE_CHECKED",
        "trigger_type": "EXPLICIT_PORTFOLIO_LIST",
        "as_of_date": "2026-05-03",
        "limit": 10,
        "offset": 5,
    }
    assert summaries[0]["wave_id"] == "dwv_ready"
    assert summaries[0]["supportability_state"] == "ready"
    assert summaries[0]["supportability_reason"] == "wave_supportability_ready"
    assert summaries[0]["latest_event_reason_code"] == "WAVE_CREATED"


def test_search_wave_summaries_filters_by_supportability_state() -> None:
    summaries = search_wave_summaries(
        wave_repository=_WaveRepository(
            [
                _wave(wave_id="dwv_ready", item_state="SOURCE_READY"),
                _wave(wave_id="dwv_blocked", item_state="SOURCE_BLOCKED"),
            ]
        ),  # type: ignore[arg-type]
        supportability_state="blocked",
    )

    assert [summary["wave_id"] for summary in summaries] == ["dwv_blocked"]
    assert summaries[0]["supportability_state"] == "blocked"


def test_wave_search_exports_only_search_builder() -> None:
    from src.api.services import wave_search

    assert wave_search.__all__ == ["search_wave_summaries"]
