from decimal import Decimal

from src.api.request_models import RebalanceRequest
from src.api.services.construction_method_readiness import (
    method_specific_reason_codes,
    method_specific_status,
)
from src.core.construction.models import (
    ConstructionAuthorityContext,
    ConstructionEnrichmentSummary,
)
from src.core.construction.vocabulary import ConstructionMethod, ConstructionMethodStatus
from src.core.models import EngineOptions, RebalanceResult
from src.core.rebalance.engine import run_simulation
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


def _request() -> RebalanceRequest:
    return RebalanceRequest.model_validate(valid_api_payload())


def _enrichment(
    *, risk_status: ConstructionMethodStatus = ConstructionMethodStatus.DEGRADED
) -> ConstructionEnrichmentSummary:
    return ConstructionEnrichmentSummary(
        tax_status=ConstructionMethodStatus.READY,
        turnover_status=ConstructionMethodStatus.READY,
        liquidity_status=ConstructionMethodStatus.READY,
        cost_status=ConstructionMethodStatus.DEGRADED,
        fx_status=ConstructionMethodStatus.READY,
        risk_status=risk_status,
        performance_status=ConstructionMethodStatus.DEGRADED,
        reason_codes=[],
    )


def _trade_result() -> RebalanceResult:
    return run_simulation(
        portfolio=portfolio_snapshot(
            portfolio_id="pf_method_readiness_1",
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
        request_hash="hash-method-readiness",
        correlation_id="corr-method-readiness",
    )


def test_solver_reason_codes_include_solver_warnings_and_comparison_evidence() -> None:
    result = _trade_result().model_copy(deep=True)
    result.diagnostics.warnings.extend(["SOLVER_NON_OPTIMAL_USER_LIMIT", "TURNOVER_WARNING"])
    result.explanation["target_method_comparison"] = {"primary_status": "READY"}

    reason_codes = method_specific_reason_codes(
        request=_request(),
        method=ConstructionMethod.SOLVER_CONSTRAINED,
        result=result,
        authority_context=ConstructionAuthorityContext(),
    )

    assert reason_codes == [
        "SOLVER_NON_OPTIMAL_USER_LIMIT",
        "TARGET_METHOD_COMPARISON_AVAILABLE",
    ]


def test_risk_method_status_uses_enrichment_and_records_missing_authority() -> None:
    enrichment = _enrichment(risk_status=ConstructionMethodStatus.DEGRADED)
    result = _trade_result()
    authority_context = ConstructionAuthorityContext()

    assert (
        method_specific_status(
            request=_request(),
            method=ConstructionMethod.RISK_AWARE,
            result=result,
            enrichment=enrichment,
            authority_context=authority_context,
        )
        == ConstructionMethodStatus.DEGRADED
    )
    assert method_specific_reason_codes(
        request=_request(),
        method=ConstructionMethod.RISK_AWARE,
        result=result,
        authority_context=authority_context,
    ) == ["RISK_AUTHORITY_NOT_CONNECTED"]
