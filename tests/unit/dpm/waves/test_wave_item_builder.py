import re
from datetime import date

from src.api.services.wave_item_builder import build_wave_item
from src.core.mandates import (
    DpmMandateConstraintSet,
    DpmMandateDigitalTwin,
    DpmMandateReviewPolicy,
)


class _MandateRepository:
    def __init__(self, twin: DpmMandateDigitalTwin | None = None) -> None:
        self._twin = twin

    def get_latest_mandate_by_portfolio(
        self,
        *,
        portfolio_id: str,
        tenant_id: str,
    ) -> DpmMandateDigitalTwin | None:
        if self._twin is not None and self._twin.portfolio_id == portfolio_id:
            return self._twin
        return None


def _source_ref() -> dict[str, object]:
    return {
        "source_system": "lotus-core",
        "source_type": "PORTFOLIO_SNAPSHOT",
        "source_id": "snapshot_001",
        "source_version": "2026-05-03",
        "supportability_state": "READY",
    }


def _twin() -> DpmMandateDigitalTwin:
    return DpmMandateDigitalTwin(
        mandate_id="MANDATE_PB_SG_ITEM",
        portfolio_id="PB_SG_ITEM",
        mandate_version="v7",
        as_of_date=date(2026, 5, 3),
        base_currency="SGD",
        reference_currency="SGD",
        risk_profile="BALANCED",
        investment_objective="Capital preservation and income",
        time_horizon="MEDIUM_TERM",
        model_portfolio_id="MODEL_SG_BALANCED",
        constraints=DpmMandateConstraintSet(),
        review_policy=DpmMandateReviewPolicy(),
    )


def test_build_wave_item_uses_source_refs_and_portfolio_diagnostics() -> None:
    item = build_wave_item(
        index=3,
        portfolio={
            "portfolio_id": " PB_SG_ITEM ",
            "mandate_id": " MANDATE_FROM_PAYLOAD ",
            "source_refs": [_source_ref()],
            "diagnostics": {"source_detail": "ready", 1: "ignored"},
        },
        mandate_repository=_MandateRepository(),
        tenant_id="tenant-test",
    )

    assert re.fullmatch(r"dwi_003_[0-9a-f]{8}", item.wave_item_id)
    assert item.portfolio_id == "PB_SG_ITEM"
    assert item.mandate_id == "MANDATE_FROM_PAYLOAD"
    assert item.state == "CANDIDATE"
    assert item.reason_codes == ["AFFECTED_PORTFOLIO_SOURCE_READY"]
    assert [ref.source_type for ref in item.source_refs] == ["PORTFOLIO_SNAPSHOT"]
    assert item.diagnostics == {
        "source_posture": "candidate_evidence_available",
        "source_detail": "ready",
    }


def test_build_wave_item_adds_latest_mandate_source_ref() -> None:
    item = build_wave_item(
        index=1,
        portfolio={"portfolio_id": "PB_SG_ITEM", "source_refs": []},
        mandate_repository=_MandateRepository(_twin()),
        tenant_id="tenant-test",
    )

    assert item.mandate_id == "MANDATE_PB_SG_ITEM"
    assert item.state == "CANDIDATE"
    assert item.source_refs[0].source_system == "lotus-manage"
    assert item.source_refs[0].source_type == "MANDATE_DIGITAL_TWIN"
    assert item.source_refs[0].source_id == "MANDATE_PB_SG_ITEM"
    assert item.source_refs[0].source_version == "v7"
    assert item.source_refs[0].supportability_state == "READY"


def test_build_wave_item_blocks_missing_source_evidence() -> None:
    item = build_wave_item(
        index=2,
        portfolio={"portfolio_id": "PB_SG_BLOCKED"},
        mandate_repository=_MandateRepository(),
        tenant_id="tenant-test",
    )

    assert item.state == "SOURCE_BLOCKED"
    assert item.reason_codes == ["MISSING_AFFECTED_PORTFOLIO_SOURCE"]
    assert item.source_refs == []
    assert item.diagnostics == {
        "source_owner": "caller_or_lotus-core",
        "required_action": "SUPPLY_SOURCE_REF",
    }


def test_wave_item_builder_exports_only_item_builder() -> None:
    from src.api.services import wave_item_builder

    assert wave_item_builder.__all__ == ["build_wave_item"]
