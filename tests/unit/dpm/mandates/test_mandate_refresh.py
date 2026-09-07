from datetime import date
from types import SimpleNamespace

import pytest
from pytest import MonkeyPatch

from src.api.services import mandate_refresh
from src.api.services.mandate_errors import (
    DpmMandateSourceIncompleteError,
    DpmMandateSourceUnavailableError,
)
from src.api.services.mandate_health_result import DpmMandateHealthCalculationResult
from src.api.services.mandate_optional_sources import DpmMandateOptionalSources
from src.api.services.mandate_refresh import (
    DpmMandateRefreshResult,
    build_mandate_refresh_result_from_core,
)
from src.core.mandates import (
    DpmMandateDigitalTwin,
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
)
from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError


class _Resolver:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, dict[str, object]]] = []

    def resolve_mandate_binding(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(("mandate", kwargs))
        if self.error is not None:
            raise self.error
        return SimpleNamespace(model_portfolio_id="MODEL_DEFAULT")

    def resolve_model_portfolio_targets(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(("model_targets", kwargs))
        return SimpleNamespace(
            base_currency="SGD",
            targets=[
                SimpleNamespace(instrument_id="SG_EQ_001"),
                SimpleNamespace(instrument_id="US_BOND_001"),
            ],
        )

    def resolve_market_data_coverage(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(("market_data", kwargs))
        return SimpleNamespace(source_product_name="MarketDataCoverageWindow")


def _optional_sources() -> DpmMandateOptionalSources:
    return DpmMandateOptionalSources(
        client_restriction_profile=None,
        sustainability_preference_profile=None,
        portfolio_cashflow_projection=None,
        client_income_needs_schedule=None,
        liquidity_reserve_requirement=None,
        planned_withdrawal_schedule=None,
        benchmark_assignment=None,
        unavailable_source_families=["CLIENT_RESTRICTION_PROFILE"],
    )


def _twin() -> DpmMandateDigitalTwin:
    return DpmMandateDigitalTwin.model_construct(
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        source_lineage=[],
    )


def _snapshot() -> DpmMandateHealthSnapshot:
    return DpmMandateHealthSnapshot.model_construct(
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
    )


def _exception() -> DpmMonitoringException:
    return DpmMonitoringException.model_construct(
        exception_id="me_refresh_001",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
    )


def test_build_mandate_refresh_result_from_core_resolves_sources_and_health(
    monkeypatch: MonkeyPatch,
) -> None:
    resolver = _Resolver()
    captured: dict[str, object] = {}
    twin = _twin()
    snapshot = _snapshot()
    exception = _exception()

    def _resolve_optional(**kwargs: object) -> DpmMandateOptionalSources:
        captured["optional"] = kwargs
        return _optional_sources()

    def _compile(**kwargs: object) -> DpmMandateDigitalTwin:
        captured["compile"] = kwargs
        return twin

    def _build_health_input(**kwargs: object) -> object:
        captured["health_input"] = kwargs
        return SimpleNamespace(source="health_input")

    def _calculate(health_input: object, *, tenant_id: str) -> DpmMandateHealthCalculationResult:
        captured["calculate"] = health_input
        return DpmMandateHealthCalculationResult(
            snapshot=snapshot,
            monitoring_exceptions=[exception],
        )

    monkeypatch.setattr(mandate_refresh, "resolve_mandate_optional_sources", _resolve_optional)
    monkeypatch.setattr(mandate_refresh, "compile_mandate_digital_twin_from_core", _compile)
    monkeypatch.setattr(
        mandate_refresh, "build_health_input_from_core_sources", _build_health_input
    )
    monkeypatch.setattr(mandate_refresh, "calculate_mandate_health_result", _calculate)

    result = build_mandate_refresh_result_from_core(
        core_resolver=resolver,  # type: ignore[arg-type]
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        as_of_date=date(2026, 5, 3),
        tenant_id="tenant_sg",
        booking_center_code="SG",
        model_portfolio_id="MODEL_OVERRIDE",
        reference_currency="SGD",
        include_market_data_coverage=True,
        correlation_id="corr-refresh",
    )

    assert isinstance(result, DpmMandateRefreshResult)
    assert result.twin is twin
    assert result.health_snapshot is snapshot
    assert result.monitoring_exceptions == [exception]
    assert resolver.calls == [
        (
            "mandate",
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "as_of_date": date(2026, 5, 3),
                "tenant_id": "tenant_sg",
                "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                "booking_center_code": "SG",
                "include_policy_pack": True,
                "correlation_id": "corr-refresh",
            },
        ),
        (
            "model_targets",
            {
                "model_portfolio_id": "MODEL_OVERRIDE",
                "as_of_date": date(2026, 5, 3),
                "tenant_id": "tenant_sg",
                "correlation_id": "corr-refresh",
            },
        ),
        (
            "market_data",
            {
                "instrument_ids": ["SG_EQ_001", "US_BOND_001"],
                "currency_pairs": [],
                "as_of_date": date(2026, 5, 3),
                "valuation_currency": "SGD",
                "tenant_id": "tenant_sg",
                "correlation_id": "corr-refresh",
            },
        ),
    ]
    assert captured["calculate"] == SimpleNamespace(source="health_input")
    assert captured["health_input"]["unavailable_source_families"] == ["CLIENT_RESTRICTION_PROFILE"]


def test_build_mandate_refresh_result_from_core_uses_binding_model_when_not_overridden(
    monkeypatch: MonkeyPatch,
) -> None:
    resolver = _Resolver()
    monkeypatch.setattr(
        mandate_refresh, "resolve_mandate_optional_sources", lambda **_: _optional_sources()
    )
    monkeypatch.setattr(
        mandate_refresh, "compile_mandate_digital_twin_from_core", lambda **_: _twin()
    )
    monkeypatch.setattr(
        mandate_refresh,
        "build_health_input_from_core_sources",
        lambda **_: SimpleNamespace(source="health_input"),
    )
    monkeypatch.setattr(
        mandate_refresh,
        "calculate_mandate_health_result",
        lambda _health_input, *, tenant_id: DpmMandateHealthCalculationResult(
            snapshot=_snapshot(),
            monitoring_exceptions=[],
        ),
    )

    build_mandate_refresh_result_from_core(
        core_resolver=resolver,  # type: ignore[arg-type]
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        as_of_date=date(2026, 5, 3),
        tenant_id=None,
        booking_center_code=None,
        model_portfolio_id=None,
        reference_currency=None,
        include_market_data_coverage=False,
        correlation_id=None,
    )

    assert resolver.calls[1][1]["model_portfolio_id"] == "MODEL_DEFAULT"
    assert [call[0] for call in resolver.calls] == ["mandate", "model_targets"]


@pytest.mark.parametrize(
    ("source_error", "service_error"),
    [
        (
            DpmCoreResolverUnavailableError("source unavailable"),
            DpmMandateSourceUnavailableError,
        ),
        (DpmCoreResolverError("source incomplete"), DpmMandateSourceIncompleteError),
    ],
)
def test_build_mandate_refresh_result_from_core_maps_core_source_errors(
    source_error: Exception,
    service_error: type[Exception],
) -> None:
    with pytest.raises(service_error):
        build_mandate_refresh_result_from_core(
            core_resolver=_Resolver(error=source_error),  # type: ignore[arg-type]
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
            as_of_date=date(2026, 5, 3),
            tenant_id=None,
            booking_center_code=None,
            model_portfolio_id=None,
            reference_currency=None,
            include_market_data_coverage=False,
            correlation_id=None,
        )


def test_mandate_refresh_exports_refresh_result_builder() -> None:
    assert mandate_refresh.__all__ == [
        "DpmMandateRefreshResult",
        "build_mandate_refresh_result_from_core",
    ]


def test_service_preserves_mandate_refresh_import_surface() -> None:
    from src.api.services import mandate_service

    assert mandate_service.DpmMandateRefreshResult is DpmMandateRefreshResult
