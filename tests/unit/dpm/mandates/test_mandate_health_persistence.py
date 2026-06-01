from src.api.services import mandate_health_persistence, mandate_service
from src.api.services.mandate_health_persistence import persist_mandate_health_evidence
from src.core.mandates import DpmMandateHealthInput
from tests.unit.dpm.mandates.test_mandate_health_result import _twin
from src.api.services.mandate_health_result import calculate_mandate_health_result


class _CapturingMandateRepository:
    def __init__(self) -> None:
        self.saved_twins: list[object] = []
        self.saved_snapshots: list[object] = []
        self.saved_exceptions: list[object] = []

    def save_mandate_snapshot(self, twin: object) -> None:
        self.saved_twins.append(twin)

    def save_health_snapshot(self, snapshot: object) -> None:
        self.saved_snapshots.append(snapshot)

    def save_monitoring_exception(self, exception: object) -> None:
        self.saved_exceptions.append(exception)


def test_persist_mandate_health_evidence_saves_optional_twin_snapshot_and_exceptions() -> None:
    repository = _CapturingMandateRepository()
    twin = _twin()
    health_result = calculate_mandate_health_result(DpmMandateHealthInput(twin=twin))

    persist_mandate_health_evidence(
        repository=repository,  # type: ignore[arg-type]
        twin=twin,
        health_snapshot=health_result.snapshot,
        monitoring_exceptions=health_result.monitoring_exceptions,
    )

    assert repository.saved_twins == [twin]
    assert repository.saved_snapshots == [health_result.snapshot]
    assert repository.saved_exceptions == health_result.monitoring_exceptions


def test_persist_mandate_health_evidence_supports_health_only_monitoring_results() -> None:
    repository = _CapturingMandateRepository()
    twin = _twin()
    health_result = calculate_mandate_health_result(DpmMandateHealthInput(twin=twin))

    persist_mandate_health_evidence(
        repository=repository,  # type: ignore[arg-type]
        health_snapshot=health_result.snapshot,
        monitoring_exceptions=health_result.monitoring_exceptions,
    )

    assert repository.saved_twins == []
    assert repository.saved_snapshots == [health_result.snapshot]
    assert repository.saved_exceptions == health_result.monitoring_exceptions


def test_mandate_service_preserves_health_persistence_private_alias() -> None:
    assert mandate_service._persist_mandate_health_evidence is persist_mandate_health_evidence


def test_mandate_health_persistence_exports_public_surface() -> None:
    assert mandate_health_persistence.__all__ == ["persist_mandate_health_evidence"]
