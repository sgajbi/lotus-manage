from src.api.services.wave_source_check import build_source_checked_wave
from src.core.mandates import DpmMandateDigitalTwin, DpmMandateHealthSnapshot
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem, DpmWaveAggregateMetrics


class _MandateRepository:
    def get_latest_mandate(
        self,
        *,
        mandate_id: str,
        tenant_id: str,
    ) -> DpmMandateDigitalTwin | None:
        return None

    def get_latest_mandate_by_portfolio(
        self,
        *,
        portfolio_id: str,
        tenant_id: str,
    ) -> DpmMandateDigitalTwin | None:
        return None

    def get_latest_health_snapshot(
        self,
        *,
        mandate_id: str,
        tenant_id: str,
    ) -> DpmMandateHealthSnapshot | None:
        return None


def _wave() -> DpmRebalanceWave:
    return DpmRebalanceWave.model_construct(
        wave_id="dwv_source_check",
        state="CREATED",
        as_of_date="2026-05-03",
        version=2,
        items=[
            DpmRebalanceWaveItem(
                wave_item_id="dwi_source_check",
                portfolio_id="PB_SG_SOURCE_CHECK",
                state="CANDIDATE",
            )
        ],
        aggregate_metrics=DpmWaveAggregateMetrics(
            item_count=1,
            state_counts={"CANDIDATE": 1},
            ready_item_count=1,
            blocked_item_count=0,
            review_required_item_count=0,
            source_degraded_item_count=0,
        ),
        events=[],
    )


def test_build_source_checked_wave_classifies_items_and_records_rollup_evidence() -> None:
    checked = build_source_checked_wave(
        wave=_wave(),
        actor_id="pm_001",
        correlation_id="corr_source_check",
        mandate_repository=_MandateRepository(),  # type: ignore[arg-type]
        tenant_id="tenant-test",
    )

    assert checked.state == "SOURCE_CHECKED"
    assert checked.items[0].state == "SOURCE_BLOCKED"
    assert checked.items[0].reason_codes == ["MANDATE_DIGITAL_TWIN_MISSING"]
    assert checked.aggregate_metrics.blocked_item_count == 1
    assert checked.events[-1].reason_code == "WAVE_SOURCE_CHECKED"
    assert checked.events[-1].metadata["blocked_item_count"] == 1
    assert checked.events[-1].metadata["state_counts"] == {"SOURCE_BLOCKED": 1}


def test_wave_source_check_exports_only_source_check_builder() -> None:
    from src.api.services import wave_source_check

    assert wave_source_check.__all__ == ["build_source_checked_wave"]
