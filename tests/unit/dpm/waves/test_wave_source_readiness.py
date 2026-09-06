from datetime import date

from src.api.services.wave_source_readiness import (
    classify_item_source_readiness,
    resolve_mandate_twin,
)
from src.core.mandates import (
    DpmMandateDigitalTwin,
    DpmMandateHealthSnapshot,
    MandateHealthState,
    MandateRecommendedAction,
)
from src.core.waves import DpmRebalanceWaveItem


class _MandateRepository:
    def __init__(
        self,
        *,
        by_id: dict[str, DpmMandateDigitalTwin] | None = None,
        by_portfolio: dict[str, DpmMandateDigitalTwin] | None = None,
        health_by_mandate: dict[str, DpmMandateHealthSnapshot] | None = None,
    ) -> None:
        self._by_id = by_id or {}
        self._by_portfolio = by_portfolio or {}
        self._health_by_mandate = health_by_mandate or {}

    def get_latest_mandate(
        self,
        *,
        mandate_id: str,
        tenant_id: str,
    ) -> DpmMandateDigitalTwin | None:
        return self._by_id.get(mandate_id)

    def get_latest_mandate_by_portfolio(
        self,
        *,
        portfolio_id: str,
        tenant_id: str,
    ) -> DpmMandateDigitalTwin | None:
        return self._by_portfolio.get(portfolio_id)

    def get_latest_health_snapshot(
        self,
        *,
        mandate_id: str,
        tenant_id: str,
    ) -> DpmMandateHealthSnapshot | None:
        return self._health_by_mandate.get(mandate_id)


def _item(
    *,
    mandate_id: str | None = "MANDATE_PB_SG_READY",
) -> DpmRebalanceWaveItem:
    return DpmRebalanceWaveItem(
        wave_item_id="dwi_source",
        portfolio_id="PB_SG_READY",
        mandate_id=mandate_id,
        state="CANDIDATE",
    )


def _twin(
    *,
    mandate_id: str = "MANDATE_PB_SG_READY",
    portfolio_id: str = "PB_SG_READY",
) -> DpmMandateDigitalTwin:
    return DpmMandateDigitalTwin.model_construct(
        mandate_id=mandate_id,
        portfolio_id=portfolio_id,
        mandate_version="v1",
        model_portfolio_id="MODEL_SG_BALANCED",
        field_gap_codes=[],
        source_lineage=[],
    )


def _health(
    *,
    mandate_id: str = "MANDATE_PB_SG_READY",
) -> DpmMandateHealthSnapshot:
    return DpmMandateHealthSnapshot.model_construct(
        health_snapshot_id="mhs_ready",
        mandate_id=mandate_id,
        as_of_date=date(2026, 5, 3),
        health_state=MandateHealthState.READY,
        source_readiness_state="READY",
        recommended_action=MandateRecommendedAction.NONE,
    )


def test_resolve_mandate_twin_uses_matching_mandate_id_first() -> None:
    twin = _twin()

    assert (
        resolve_mandate_twin(
            item=_item(),
            mandate_repository=_MandateRepository(by_id={twin.mandate_id: twin}),
            tenant_id="tenant-test",
        )
        is twin
    )


def test_resolve_mandate_twin_falls_back_to_portfolio_when_id_mismatches_portfolio() -> None:
    wrong_portfolio_twin = _twin(portfolio_id="PB_SG_OTHER")
    portfolio_twin = _twin(mandate_id="MANDATE_BY_PORTFOLIO")

    assert (
        resolve_mandate_twin(
            item=_item(),
            mandate_repository=_MandateRepository(
                by_id={wrong_portfolio_twin.mandate_id: wrong_portfolio_twin},
                by_portfolio={portfolio_twin.portfolio_id: portfolio_twin},
            ),
            tenant_id="tenant-test",
        )
        is portfolio_twin
    )


def test_classify_item_source_readiness_loads_twin_and_health_from_repository() -> None:
    twin = _twin()
    health = _health()

    classified = classify_item_source_readiness(
        item=_item(),
        wave_as_of_date="2026-05-03",
        mandate_repository=_MandateRepository(
            by_id={twin.mandate_id: twin},
            health_by_mandate={twin.mandate_id: health},
        ),
        tenant_id="tenant-test",
    )

    assert classified.state == "SOURCE_READY"
    assert classified.reason_codes == ["SOURCE_READINESS_READY"]
    assert classified.mandate_id == twin.mandate_id
    assert classified.model_portfolio_id == twin.model_portfolio_id


def test_classify_item_source_readiness_blocks_missing_twin() -> None:
    classified = classify_item_source_readiness(
        item=_item(mandate_id=None),
        wave_as_of_date="2026-05-03",
        mandate_repository=_MandateRepository(),
        tenant_id="tenant-test",
    )

    assert classified.state == "SOURCE_BLOCKED"
    assert classified.reason_codes == ["MANDATE_DIGITAL_TWIN_MISSING"]


def test_wave_source_readiness_exports_only_lookup_helpers() -> None:
    from src.api.services import wave_source_readiness

    assert wave_source_readiness.__all__ == [
        "classify_item_source_readiness",
        "resolve_mandate_twin",
    ]
