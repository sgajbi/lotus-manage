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
