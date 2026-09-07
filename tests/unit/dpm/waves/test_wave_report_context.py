from pytest import MonkeyPatch

from src.api.services import wave_report_context
from src.api.services.wave_report_context import portfolio_memory_context_for_report
from src.core.portfolio_memory.handoffs import DpmPortfolioMemoryReportContext
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem


def _wave(*, items: list[DpmRebalanceWaveItem] | None = None) -> DpmRebalanceWave:
    return DpmRebalanceWave.model_construct(
        wave_id="dwv_report",
        state="HANDOFF_READY",
        items=items
        if items is not None
        else [
            DpmRebalanceWaveItem(
                wave_item_id="dwi_report",
                portfolio_id="PB_SG_REPORT",
                state="HANDOFF_READY",
            )
        ],
    )


def test_portfolio_memory_context_for_report_returns_none_without_required_repositories() -> None:
    assert (
        portfolio_memory_context_for_report(
            wave=_wave(),
            proof_pack_repository=None,
            wave_repository=object(),  # type: ignore[arg-type]
            outcome_review_repository=object(),  # type: ignore[arg-type]
            mandate_repository=None,
            tenant_id="tenant-test",
        )
        is None
    )
    assert (
        portfolio_memory_context_for_report(
            wave=_wave(items=[]),
            proof_pack_repository=object(),  # type: ignore[arg-type]
            wave_repository=object(),  # type: ignore[arg-type]
            outcome_review_repository=object(),  # type: ignore[arg-type]
            mandate_repository=None,
            tenant_id="tenant-test",
        )
        is None
    )


def test_portfolio_memory_context_for_report_uses_first_wave_item_portfolio(
    monkeypatch: MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    context = DpmPortfolioMemoryReportContext.model_construct(
        portfolio_id="PB_SG_REPORT",
        supportability_state="READY",
    )

    def _build(**kwargs: object) -> DpmPortfolioMemoryReportContext:
        captured.update(kwargs)
        return context

    monkeypatch.setattr(
        wave_report_context,
        "build_report_portfolio_memory_context",
        _build,
    )

    result = portfolio_memory_context_for_report(
        wave=_wave(),
        proof_pack_repository=object(),  # type: ignore[arg-type]
        wave_repository=object(),  # type: ignore[arg-type]
        outcome_review_repository=object(),  # type: ignore[arg-type]
        mandate_repository=object(),  # type: ignore[arg-type]
        tenant_id="tenant-test",
    )

    assert result is context
    assert captured["portfolio_id"] == "PB_SG_REPORT"


def test_wave_report_context_exports_only_report_context_builder() -> None:
    assert wave_report_context.__all__ == ["portfolio_memory_context_for_report"]
