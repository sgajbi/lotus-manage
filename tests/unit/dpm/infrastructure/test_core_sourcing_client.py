from datetime import date

import httpx
import pytest

from src.core.dpm_source_context import DpmStatefulInput
from src.infrastructure.core_sourcing import (
    DpmCoreResolverClient,
    DpmCoreResolverConfig,
    DpmCoreResolverUnavailableError,
)


def _context_payload() -> dict:
    return {
        "portfolio_snapshot": {
            "snapshot_id": "core-pf-snap-001",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "base_currency": "SGD",
            "positions": [{"instrument_id": "EQ_1", "quantity": "100"}],
            "cash_balances": [{"currency": "SGD", "amount": "10000"}],
        },
        "market_data_snapshot": {
            "snapshot_id": "core-md-snap-001",
            "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "SGD"}],
            "fx_rates": [],
        },
        "model_portfolio": {"targets": [{"instrument_id": "EQ_1", "weight": "1.0"}]},
        "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
        "source_lineage": {
            "portfolio_snapshot_id": "core-pf-snap-001",
            "market_data_snapshot_id": "core-md-snap-001",
        },
        "supportability": {"state": "READY", "reason": "DPM_CORE_CONTEXT_READY"},
    }


def _model_portfolio_target_payload() -> dict:
    return {
        "product_name": "DpmModelPortfolioTarget",
        "product_version": "v1",
        "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
        "model_portfolio_version": "2026.04",
        "as_of_date": "2026-04-10",
        "display_name": "Singapore Global Balanced DPM Model",
        "base_currency": "SGD",
        "risk_profile": "balanced",
        "mandate_type": "discretionary",
        "rebalance_frequency": "monthly",
        "approval_status": "approved",
        "approved_at": "2026-04-10T09:00:00Z",
        "effective_from": "2026-04-10",
        "effective_to": None,
        "targets": [
            {
                "instrument_id": "EQ_US_AAPL",
                "target_weight": "0.6000000000",
                "min_weight": "0.5500000000",
                "max_weight": "0.6500000000",
                "target_status": "active",
                "quality_status": "accepted",
                "source_record_id": "target-aapl",
            },
            {
                "instrument_id": "FI_US_TREASURY_10Y",
                "target_weight": "0.4000000000",
                "min_weight": "0.3500000000",
                "max_weight": "0.4500000000",
                "target_status": "active",
                "quality_status": "accepted",
                "source_record_id": "target-treasury",
            },
        ],
        "supportability": {
            "state": "READY",
            "reason": "MODEL_TARGETS_READY",
            "target_count": 2,
            "total_target_weight": "1.0000000000",
        },
        "lineage": {
            "source_system": "investment_office_model_system",
            "contract_version": "rfc_087_v1",
        },
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-04-10T09:00:00Z",
    }


def _stateful_input() -> DpmStatefulInput:
    return DpmStatefulInput(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of=date(2026, 3, 25),
        mandate_id="mandate_balanced_discretionary",
        model_portfolio_id="model_balanced_sgd",
        tenant_id="tenant_001",
        booking_center_code="SG",
    )


def test_core_resolver_posts_selector_payload_and_correlation_header():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["correlation_id"] = request.headers.get("X-Correlation-Id")
        seen["payload"] = request.read()
        return httpx.Response(200, json=_context_payload())

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(
            base_url="https://core.example.test",
            path_template="/integration/portfolios/{portfolio_id}/core-snapshot",
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    context = client.resolve_execution_context(
        stateful_input=_stateful_input(),
        correlation_id="corr-core-001",
    )

    assert seen["url"] == (
        "https://core.example.test/integration/portfolios/PB_SG_GLOBAL_BAL_001/core-snapshot"
    )
    assert seen["correlation_id"] == "corr-core-001"
    assert b'"include_tax_lots":true' in seen["payload"]
    assert context.source_lineage.portfolio_snapshot_id == "core-pf-snap-001"


def test_core_resolver_retries_transient_unavailable_response():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, json={"detail": "not ready"})
        return httpx.Response(200, json=_context_payload())

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(
            base_url="https://core.example.test",
            path_template="/integration/portfolios/{portfolio_id}/core-snapshot",
            max_attempts=2,
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    context = client.resolve_execution_context(
        stateful_input=_stateful_input(),
        correlation_id=None,
    )

    assert calls == 2
    assert context.supportability.state == "READY"


def test_core_resolver_fetches_model_portfolio_targets_from_dedicated_source_product():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["correlation_id"] = request.headers.get("X-Correlation-Id")
        seen["payload"] = request.read()
        return httpx.Response(200, json=_model_portfolio_target_payload())

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = client.resolve_model_portfolio_targets(
        model_portfolio_id="MODEL_PB_SG_GLOBAL_BAL_DPM",
        as_of_date=date(2026, 4, 10),
        tenant_id="tenant_sg_pb",
        correlation_id="corr-targets-001",
    )

    assert seen["url"] == (
        "https://core.example.test/integration/model-portfolios/MODEL_PB_SG_GLOBAL_BAL_DPM/targets"
    )
    assert seen["correlation_id"] == "corr-targets-001"
    assert b'"as_of_date":"2026-04-10"' in seen["payload"]
    assert b'"tenant_id":"tenant_sg_pb"' in seen["payload"]
    assert response.product_name == "DpmModelPortfolioTarget"
    assert response.supportability.state == "READY"
    assert [target.instrument_id for target in response.targets] == [
        "EQ_US_AAPL",
        "FI_US_TREASURY_10Y",
    ]


def test_core_resolver_timeout_maps_to_source_safe_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(
            base_url="https://core.example.test",
            path_template="/integration/portfolios/{portfolio_id}/core-snapshot",
            max_attempts=1,
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(DpmCoreResolverUnavailableError, match="DPM_CORE_RESOLVER_UNAVAILABLE"):
        client.resolve_execution_context(stateful_input=_stateful_input(), correlation_id=None)


def test_core_resolver_rejects_missing_or_legacy_monolithic_route():
    for path_template in ("", "/integration/portfolios/{portfolio_id}/dpm-execution-context"):
        client = DpmCoreResolverClient(
            config=DpmCoreResolverConfig(
                base_url="https://core.example.test",
                path_template=path_template,
            ),
            client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200))),
        )

        with pytest.raises(
            DpmCoreResolverUnavailableError,
            match="DPM_CORE_RESOLVER_UNAVAILABLE",
        ):
            client.resolve_execution_context(
                stateful_input=_stateful_input(),
                correlation_id=None,
            )
