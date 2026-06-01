import re

import pytest

from src.api.services.wave_errors import DpmWaveValidationError
from src.api.services.wave_preview import build_preview_wave
from src.core.mandates import DpmMandateDigitalTwin


class _MandateRepository:
    def get_latest_mandate_by_portfolio(
        self,
        *,
        portfolio_id: str,
    ) -> DpmMandateDigitalTwin | None:
        return None


def _source_ref() -> dict[str, object]:
    return {
        "source_system": "lotus-core",
        "source_type": "PORTFOLIO_SNAPSHOT",
        "source_id": "snapshot_preview",
        "source_version": "2026-05-03",
        "supportability_state": "READY",
    }


def test_build_preview_wave_constructs_previewed_wave_with_source_lineage() -> None:
    wave = build_preview_wave(
        trigger_type="EXPLICIT_PORTFOLIO_LIST",
        trigger_id="manual-preview",
        rationale="Preview source-backed portfolio.",
        as_of_date="2026-05-03",
        actor_id="pm_001",
        correlation_id="corr_preview",
        portfolios=[{"portfolio_id": "PB_SG_PREVIEW", "source_refs": [_source_ref()]}],
        mandate_repository=_MandateRepository(),  # type: ignore[arg-type]
    )

    assert re.fullmatch(r"dwv_preview_[0-9a-f]{12}", wave.wave_id)
    assert wave.state == "PREVIEWED"
    assert wave.trigger.trigger_type == "EXPLICIT_PORTFOLIO_LIST"
    assert wave.trigger.source_refs[0].source_type == "PORTFOLIO_SNAPSHOT"
    assert len(wave.items) == 1
    assert wave.items[0].portfolio_id == "PB_SG_PREVIEW"
    assert wave.aggregate_metrics.item_count == 1
    assert wave.events[-1].reason_code == "WAVE_PREVIEWED"
    assert wave.events[-1].metadata == {"item_count": 1}


def test_build_preview_wave_raises_governed_error_for_empty_source_set() -> None:
    with pytest.raises(DpmWaveValidationError) as exc_info:
        build_preview_wave(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-preview",
            rationale="Preview empty set.",
            as_of_date="2026-05-03",
            actor_id="pm_001",
            correlation_id="corr_preview",
            portfolios=[],
            mandate_repository=_MandateRepository(),  # type: ignore[arg-type]
        )

    assert exc_info.value.code == "AFFECTED_PORTFOLIO_SET_EMPTY"


def test_wave_preview_exports_only_preview_builder() -> None:
    from src.api.services import wave_preview

    assert wave_preview.__all__ == ["build_preview_wave"]
