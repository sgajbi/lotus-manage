from datetime import date
from decimal import Decimal

from src.api.request_models import RebalanceRequest
from src.api.services.construction_method_authority import (
    authority_context_for_method,
    regime_context_for_method,
    risk_context_for_method,
)
from src.core.construction.models import (
    AuthoritativeRegimeStressContext,
    AuthoritativeRiskContext,
    ConstructionAuthorityContext,
)
from src.core.construction.vocabulary import ConstructionMethod, ConstructionMethodStatus
from src.core.models import EngineOptions, RebalanceResult
from src.core.rebalance.engine import run_simulation
from src.infrastructure.risk_authority import LotusRiskAuthorityUnavailableError
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    position,
    price,
    shelf_entry,
    target,
    valid_api_payload,
)


class _RiskAuthorityClient:
    def __init__(self) -> None:
        self.regime_as_of_date: date | None = None

    def concentration_context(
        self,
        *,
        result: RebalanceResult,
        correlation_id: str | None,
    ) -> AuthoritativeRiskContext:
        return AuthoritativeRiskContext(
            supportability_status=ConstructionMethodStatus.READY,
            source_system="lotus-risk",
            source_product_name="RiskMetricsReport",
            source_product_version="v1",
            reason_codes=["RISK_CONTEXT_READY"],
        )

    def regime_scenario_context(
        self,
        *,
        result: RebalanceResult,
        portfolio_id: str,
        as_of_date: date,
        correlation_id: str | None,
    ) -> AuthoritativeRegimeStressContext:
        self.regime_as_of_date = as_of_date
        return AuthoritativeRegimeStressContext(
            supportability_status=ConstructionMethodStatus.READY,
            source_system="lotus-risk",
            scenario_pack_id="CIO_REGIME_2026_Q2",
            worst_case_loss_pct=Decimal("0.05"),
            maximum_allowed_loss_pct=Decimal("0.12"),
            reason_codes=["REGIME_SCENARIO_READY"],
        )


class _UnavailableRiskAuthorityClient(_RiskAuthorityClient):
    def concentration_context(
        self,
        *,
        result: RebalanceResult,
        correlation_id: str | None,
    ) -> AuthoritativeRiskContext:
        raise LotusRiskAuthorityUnavailableError("risk down")

    def regime_scenario_context(
        self,
        *,
        result: RebalanceResult,
        portfolio_id: str,
        as_of_date: date,
        correlation_id: str | None,
    ) -> AuthoritativeRegimeStressContext:
        raise LotusRiskAuthorityUnavailableError("regime down")


def _request() -> RebalanceRequest:
    return RebalanceRequest.model_validate(valid_api_payload())


def _trade_result() -> RebalanceResult:
    return run_simulation(
        portfolio=portfolio_snapshot(
            portfolio_id="pf_method_authority_1",
            base_currency="USD",
            positions=[position("EQ_A", "10")],
            cash_balances=[cash("USD", "0")],
        ),
        market_data=market_data_snapshot(
            prices=[
                price("EQ_A", "100", "USD"),
                price("EQ_B", "100", "USD"),
            ]
        ),
        model=model_portfolio(
            targets=[
                target("EQ_A", "0.50"),
                target("EQ_B", "0.50"),
            ]
        ),
        shelf=[
            shelf_entry("EQ_A", status="APPROVED", asset_class="EQUITY"),
            shelf_entry("EQ_B", status="APPROVED", asset_class="EQUITY"),
        ],
        options=EngineOptions(max_turnover_pct=Decimal("1.00")),
        request_hash="hash-method-authority",
        correlation_id="corr-method-authority",
    )


def test_authority_context_for_risk_method_fetches_risk_context() -> None:
    authority_context = authority_context_for_method(
        request=_request(),
        method=ConstructionMethod.RISK_AWARE,
        result=_trade_result(),
        authority_context=ConstructionAuthorityContext(),
        risk_authority_client=_RiskAuthorityClient(),  # type: ignore[arg-type]
        correlation_id="corr-risk",
        as_of_date=date(2026, 6, 1),
    )

    assert authority_context.risk_context is not None
    assert authority_context.risk_context.source_product_name == "RiskMetricsReport"


def test_risk_context_for_method_fetches_source_context() -> None:
    context = risk_context_for_method(
        method=ConstructionMethod.RISK_AWARE,
        result=_trade_result(),
        authority_context=ConstructionAuthorityContext(),
        risk_authority_client=_RiskAuthorityClient(),  # type: ignore[arg-type]
        correlation_id="corr-risk",
    )

    assert context is not None
    assert context.source_product_name == "RiskMetricsReport"


def test_risk_context_for_method_preserves_existing_context_without_fetch() -> None:
    existing_context = _RiskAuthorityClient().concentration_context(
        result=_trade_result(),
        correlation_id="corr-risk",
    )

    context = risk_context_for_method(
        method=ConstructionMethod.RISK_AWARE,
        result=_trade_result(),
        authority_context=ConstructionAuthorityContext(risk_context=existing_context),
        risk_authority_client=_UnavailableRiskAuthorityClient(),  # type: ignore[arg-type]
        correlation_id="corr-risk",
    )

    assert context is existing_context


def test_authority_context_preserves_fail_closed_risk_unavailable_posture() -> None:
    authority_context = authority_context_for_method(
        request=_request(),
        method=ConstructionMethod.RISK_AWARE,
        result=_trade_result(),
        authority_context=ConstructionAuthorityContext(),
        risk_authority_client=_UnavailableRiskAuthorityClient(),  # type: ignore[arg-type]
        correlation_id="corr-risk",
        as_of_date=date(2026, 6, 1),
    )

    assert authority_context.risk_context is None


def test_risk_context_for_method_preserves_fail_closed_unavailable_posture() -> None:
    context = risk_context_for_method(
        method=ConstructionMethod.RISK_AWARE,
        result=_trade_result(),
        authority_context=ConstructionAuthorityContext(),
        risk_authority_client=_UnavailableRiskAuthorityClient(),  # type: ignore[arg-type]
        correlation_id="corr-risk",
    )

    assert context is None


def test_authority_context_passes_governed_as_of_date_to_regime_context() -> None:
    risk_client = _RiskAuthorityClient()

    authority_context = authority_context_for_method(
        request=_request(),
        method=ConstructionMethod.REGIME_STRESS_AWARE,
        result=_trade_result(),
        authority_context=ConstructionAuthorityContext(),
        risk_authority_client=risk_client,  # type: ignore[arg-type]
        correlation_id="corr-regime",
        as_of_date=date(2026, 5, 31),
    )

    assert risk_client.regime_as_of_date == date(2026, 5, 31)
    assert authority_context.regime_stress_context is not None
    assert authority_context.regime_stress_context.scenario_pack_id == "CIO_REGIME_2026_Q2"


def test_regime_context_for_method_fetches_with_governed_as_of_date() -> None:
    risk_client = _RiskAuthorityClient()

    context = regime_context_for_method(
        request=_request(),
        method=ConstructionMethod.REGIME_STRESS_AWARE,
        result=_trade_result(),
        authority_context=ConstructionAuthorityContext(),
        risk_authority_client=risk_client,  # type: ignore[arg-type]
        correlation_id="corr-regime",
        as_of_date=date(2026, 5, 31),
    )

    assert risk_client.regime_as_of_date == date(2026, 5, 31)
    assert context is not None
    assert context.scenario_pack_id == "CIO_REGIME_2026_Q2"


def test_regime_context_for_method_preserves_existing_context_without_fetch() -> None:
    existing_context = _RiskAuthorityClient().regime_scenario_context(
        result=_trade_result(),
        portfolio_id="pf_method_authority_1",
        as_of_date=date(2026, 5, 31),
        correlation_id="corr-regime",
    )
    risk_client = _RiskAuthorityClient()

    context = regime_context_for_method(
        request=_request(),
        method=ConstructionMethod.REGIME_STRESS_AWARE,
        result=_trade_result(),
        authority_context=ConstructionAuthorityContext(regime_stress_context=existing_context),
        risk_authority_client=risk_client,  # type: ignore[arg-type]
        correlation_id="corr-regime",
        as_of_date=date(2026, 6, 1),
    )

    assert context is existing_context
    assert risk_client.regime_as_of_date is None


def test_regime_context_for_method_preserves_fail_closed_unavailable_posture() -> None:
    context = regime_context_for_method(
        request=_request(),
        method=ConstructionMethod.REGIME_STRESS_AWARE,
        result=_trade_result(),
        authority_context=ConstructionAuthorityContext(),
        risk_authority_client=_UnavailableRiskAuthorityClient(),  # type: ignore[arg-type]
        correlation_id="corr-regime",
        as_of_date=date(2026, 5, 31),
    )

    assert context is None
