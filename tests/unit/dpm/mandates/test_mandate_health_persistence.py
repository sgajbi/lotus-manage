import pytest

from src.api.services import mandate_health_persistence
from src.api.services.mandate_health_persistence import persist_mandate_health_evidence
from src.core.mandates import MANDATE_LIMIT_PROVENANCE_AMBIGUOUS, DpmMandateHealthInput
from tests.unit.dpm.mandates.test_mandate_health_result import _twin
from src.api.services.mandate_health_result import calculate_mandate_health_result


class _CapturingMandateRepository:
    def __init__(self) -> None:
        self.saved_twins: list[object] = []
        self.saved_snapshots: list[object] = []
        self.saved_exceptions: list[object] = []
        self.saved_producer_kinds: list[str] = []

    def save_mandate_snapshot(
        self,
        twin: object,
        *,
        tenant_id: str,
        producer_kind: str = "CALLER_SUPPLIED",
    ) -> None:
        self.saved_twins.append(twin)
        self.saved_producer_kinds.append(producer_kind)

    def save_health_snapshot(self, snapshot: object, *, tenant_id: str) -> None:
        self.saved_snapshots.append(snapshot)

    def save_monitoring_exception(self, exception: object, *, tenant_id: str) -> None:
        self.saved_exceptions.append(exception)


def test_persist_mandate_health_evidence_saves_optional_twin_snapshot_and_exceptions() -> None:
    repository = _CapturingMandateRepository()
    twin = _twin()
    health_result = calculate_mandate_health_result(
        DpmMandateHealthInput(twin=twin), tenant_id="tenant-test"
    )

    persist_mandate_health_evidence(
        repository=repository,  # type: ignore[arg-type]
        twin=twin,
        health_snapshot=health_result.snapshot,
        monitoring_exceptions=health_result.monitoring_exceptions,
        tenant_id="tenant-test",
    )

    assert repository.saved_twins == [twin]
    assert repository.saved_producer_kinds == ["CALLER_SUPPLIED"]
    assert repository.saved_snapshots == [health_result.snapshot]
    assert repository.saved_exceptions == health_result.monitoring_exceptions


def test_persist_mandate_health_evidence_supports_health_only_monitoring_results() -> None:
    repository = _CapturingMandateRepository()
    twin = _twin()
    health_result = calculate_mandate_health_result(
        DpmMandateHealthInput(twin=twin), tenant_id="tenant-test"
    )

    persist_mandate_health_evidence(
        repository=repository,  # type: ignore[arg-type]
        health_snapshot=health_result.snapshot,
        monitoring_exceptions=health_result.monitoring_exceptions,
        tenant_id="tenant-test",
    )

    assert repository.saved_twins == []
    assert repository.saved_snapshots == [health_result.snapshot]
    assert repository.saved_exceptions == health_result.monitoring_exceptions


def test_persist_mandate_health_evidence_records_core_compiler_provenance() -> None:
    repository = _CapturingMandateRepository()
    twin = _twin()
    health_result = calculate_mandate_health_result(
        DpmMandateHealthInput(twin=twin), tenant_id="tenant-test"
    )

    persist_mandate_health_evidence(
        repository=repository,  # type: ignore[arg-type]
        twin=twin,
        health_snapshot=health_result.snapshot,
        monitoring_exceptions=[],
        tenant_id="tenant-test",
        mandate_producer_kind="CORE_COMPILED",
    )

    assert repository.saved_producer_kinds == ["CORE_COMPILED"]


def test_unverified_caller_projection_cannot_persist_health_or_overwrite_limits() -> None:
    repository = _CapturingMandateRepository()
    twin = _twin().model_copy(update={"field_gap_codes": [MANDATE_LIMIT_PROVENANCE_AMBIGUOUS]})
    health_result = calculate_mandate_health_result(
        DpmMandateHealthInput(twin=twin), tenant_id="tenant-test"
    )

    with pytest.raises(ValueError, match="DPM_MANDATE_AMBIGUOUS_SNAPSHOT_NOT_VERIFIED"):
        persist_mandate_health_evidence(
            repository=repository,  # type: ignore[arg-type]
            twin=twin,
            health_snapshot=health_result.snapshot,
            monitoring_exceptions=health_result.monitoring_exceptions,
            tenant_id="tenant-test",
        )

    assert repository.saved_twins == []
    assert repository.saved_snapshots == []
    assert repository.saved_exceptions == []


def test_verified_caller_projection_recalculates_without_overwriting_limits() -> None:
    repository = _CapturingMandateRepository()
    twin = _twin().model_copy(update={"field_gap_codes": [MANDATE_LIMIT_PROVENANCE_AMBIGUOUS]})
    health_result = calculate_mandate_health_result(
        DpmMandateHealthInput(twin=twin), tenant_id="tenant-test"
    )

    persist_mandate_health_evidence(
        repository=repository,  # type: ignore[arg-type]
        twin=twin,
        health_snapshot=health_result.snapshot,
        monitoring_exceptions=health_result.monitoring_exceptions,
        tenant_id="tenant-test",
        verified_retained_projection=True,
    )

    assert repository.saved_twins == []
    assert repository.saved_snapshots == [health_result.snapshot]


def test_mandate_health_persistence_exports_public_surface() -> None:
    assert mandate_health_persistence.__all__ == ["persist_mandate_health_evidence"]
