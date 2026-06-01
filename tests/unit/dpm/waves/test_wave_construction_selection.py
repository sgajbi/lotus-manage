import pytest

from src.api.services import wave_construction_selection
from src.api.services.wave_construction_selection import select_construction_alternative_for_wave
from src.api.services.wave_errors import DpmWaveLookupError


class _ConstructionService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.error: Exception | None = None

    def select_construction_alternative(self, **kwargs: object) -> None:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error


def test_select_construction_alternative_for_wave_delegates_selection(monkeypatch) -> None:
    service = _ConstructionService()
    monkeypatch.setattr(wave_construction_selection, "construction_service", service)

    select_construction_alternative_for_wave(
        repository="repository",
        alternative_set_id="alt_set_001",
        alternative_id="alt_balanced",
        actor_id="pm_001",
        reason_code="PM_SELECTED",
        comment="selected for mandate",
        correlation_id="corr_wave_select",
    )

    assert service.calls == [
        {
            "repository": "repository",
            "alternative_set_id": "alt_set_001",
            "alternative_id": "alt_balanced",
            "actor_id": "pm_001",
            "reason_code": "PM_SELECTED",
            "comment": "selected for mandate",
            "correlation_id": "corr_wave_select",
        }
    ]


def test_select_construction_alternative_for_wave_maps_selection_failures(
    monkeypatch,
) -> None:
    service = _ConstructionService()
    service.error = LookupError("alternative missing")
    monkeypatch.setattr(wave_construction_selection, "construction_service", service)

    with pytest.raises(DpmWaveLookupError) as exc_info:
        select_construction_alternative_for_wave(
            repository="repository",
            alternative_set_id="alt_set_001",
            alternative_id="missing_alt",
            actor_id="pm_001",
            reason_code="PM_SELECTED",
            comment=None,
            correlation_id="corr_wave_select",
        )

    assert exc_info.value.code == "DPM_CONSTRUCTION_ALTERNATIVE_NOT_FOUND"
    assert exc_info.value.message == "alternative missing"


def test_wave_construction_selection_exports_public_surface() -> None:
    assert wave_construction_selection.__all__ == ["select_construction_alternative_for_wave"]
