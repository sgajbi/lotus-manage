from __future__ import annotations

from dataclasses import dataclass

from src.api.routers.wave_cio_model_change_projection import (
    build_cio_model_change_resolved_portfolios,
)


@dataclass(frozen=True)
class Supportability:
    state: str = "READY"


@dataclass(frozen=True)
class Mandate:
    portfolio_id: str = "PB_SG_GLOBAL_BAL_001"
    mandate_id: str = "MANDATE_PB_SG_GLOBAL_BAL_001"
    source_record_id: str | None = "mandate-binding-001"
    binding_version: object = 3


@dataclass(frozen=True)
class Cohort:
    snapshot_id: str | None = "cio-model-change-snapshot-20260519"
    source_batch_fingerprint: str | None = "sha256:cio-model-change"
    model_change_event_id: str = "cio_model_change:MODEL_PB_SG_GLOBAL_BAL_DPM:2026.05"
    product_version: str = "v1"
    supportability: Supportability = Supportability()
    model_portfolio_version: str = "2026.05"
    affected_mandates: list[Mandate] | None = None

    def __post_init__(self) -> None:
        if self.affected_mandates is None:
            object.__setattr__(self, "affected_mandates", [Mandate()])


def test_build_cio_model_change_resolved_portfolios_preserves_snapshot_lineage() -> None:
    assert build_cio_model_change_resolved_portfolios(Cohort()) == [
        {
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
            "source_refs": [
                {
                    "source_system": "lotus-core",
                    "source_type": "CioModelChangeAffectedCohort",
                    "source_id": "cio-model-change-snapshot-20260519",
                    "source_version": "v1",
                    "supportability_state": "READY",
                    "content_hash": "sha256:cio-model-change",
                },
                {
                    "source_system": "lotus-core",
                    "source_type": "CIO_MODEL_CHANGE_EVENT",
                    "source_id": "cio_model_change:MODEL_PB_SG_GLOBAL_BAL_DPM:2026.05",
                    "source_version": "2026.05",
                    "supportability_state": "READY",
                    "content_hash": "sha256:cio-model-change",
                },
                {
                    "source_system": "lotus-core",
                    "source_type": "CIO_MODEL_CHANGE_AFFECTED_MANDATE",
                    "source_id": "mandate-binding-001",
                    "source_version": "3",
                    "supportability_state": "READY",
                },
            ],
        }
    ]


def test_build_cio_model_change_resolved_portfolios_falls_back_to_batch_fingerprint() -> None:
    portfolios = build_cio_model_change_resolved_portfolios(Cohort(snapshot_id=None))

    assert portfolios[0]["source_refs"][0]["source_id"] == "sha256:cio-model-change"


def test_build_cio_model_change_resolved_portfolios_falls_back_to_event_id() -> None:
    portfolios = build_cio_model_change_resolved_portfolios(
        Cohort(snapshot_id=None, source_batch_fingerprint=None)
    )

    assert (
        portfolios[0]["source_refs"][0]["source_id"]
        == "cio_model_change:MODEL_PB_SG_GLOBAL_BAL_DPM:2026.05"
    )
    assert portfolios[0]["source_refs"][0]["content_hash"] is None
    assert portfolios[0]["source_refs"][1]["content_hash"] is None


def test_build_cio_model_change_resolved_portfolios_falls_back_mandate_ref_to_mandate_id() -> None:
    portfolios = build_cio_model_change_resolved_portfolios(
        Cohort(affected_mandates=[Mandate(source_record_id=None, binding_version="4")])
    )

    assert portfolios[0]["source_refs"][2]["source_id"] == "MANDATE_PB_SG_GLOBAL_BAL_001"
    assert portfolios[0]["source_refs"][2]["source_version"] == "4"
