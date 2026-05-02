from datetime import date
from decimal import Decimal

import httpx
import pytest

from src.core.dpm_source_context import DpmStatefulInput
from src.infrastructure.core_sourcing import (
    DpmCoreResolverClient,
    DpmCoreResolverConfig,
    DpmCoreResolverError,
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


def _mandate_binding_payload() -> dict:
    return {
        "product_name": "DiscretionaryMandateBinding",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
        "client_id": "CIF_SG_000184",
        "mandate_type": "discretionary",
        "discretionary_authority_status": "active",
        "booking_center_code": "Singapore",
        "jurisdiction_code": "SG",
        "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
        "policy_pack_id": "POLICY_DPM_SG_BALANCED_V1",
        "risk_profile": "balanced",
        "investment_horizon": "long_term",
        "leverage_allowed": False,
        "tax_awareness_allowed": True,
        "settlement_awareness_required": True,
        "rebalance_frequency": "monthly",
        "rebalance_bands": {
            "default_band": "0.0250000000",
            "cash_reserve_weight": "0.0200000000",
        },
        "effective_from": "2026-04-01",
        "effective_to": None,
        "binding_version": 1,
        "supportability": {
            "state": "READY",
            "reason": "MANDATE_BINDING_READY",
            "missing_data_families": [],
        },
        "lineage": {
            "source_system": "mandate_admin",
            "source_record_id": "mandate_001_v1",
            "contract_version": "rfc_087_v1",
        },
        "data_quality_status": "ACCEPTED",
        "latest_evidence_timestamp": "2026-04-01T09:00:00Z",
    }


def _instrument_eligibility_payload() -> dict:
    return {
        "product_name": "InstrumentEligibilityProfile",
        "product_version": "v1",
        "as_of_date": "2026-04-10",
        "tenant_id": "tenant_sg_pb",
        "eligibility": [
            {
                "security_id": "EQ_US_AAPL",
                "found": True,
                "eligibility_status": "APPROVED",
                "product_shelf_status": "APPROVED",
                "buy_allowed": True,
                "sell_allowed": True,
                "restriction_reason_codes": [],
                "settlement_days": 2,
                "settlement_calendar_id": "US_NYSE",
                "liquidity_tier": "L1",
                "issuer_id": "APPLE",
                "issuer_name": "Apple Inc.",
                "ultimate_parent_issuer_id": "APPLE_PARENT",
                "ultimate_parent_issuer_name": "Apple Inc.",
                "asset_class": "Equity",
                "country_of_risk": "US",
                "effective_from": "2026-04-01",
                "effective_to": None,
                "source_record_id": "AAPL-elig-20260401",
                "quality_status": "accepted",
            }
        ],
        "supportability": {
            "state": "READY",
            "reason": "INSTRUMENT_ELIGIBILITY_READY",
            "requested_count": 1,
            "found_count": 1,
            "missing_security_ids": [],
        },
        "lineage": {
            "source_system": "instrument_eligibility",
            "contract_version": "rfc_087_v1",
        },
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-04-10T09:00:00Z",
    }


def _portfolio_tax_lots_payload() -> dict:
    return {
        "product_name": "PortfolioTaxLotWindow",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "as_of_date": "2026-04-10",
        "lots": [
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "security_id": "EQ_US_AAPL",
                "instrument_id": "EQ_US_AAPL",
                "lot_id": "LOT-AAPL-001",
                "open_quantity": "100.0000000000",
                "original_quantity": "100.0000000000",
                "acquisition_date": "2026-03-25",
                "cost_basis_base": "15005.5000000000",
                "cost_basis_local": "15005.5000000000",
                "local_currency": "USD",
                "tax_lot_status": "OPEN",
                "source_transaction_id": "TXN-BUY-AAPL-001",
                "source_lineage": {
                    "source_system": "position_lot_state",
                    "calculation_policy_id": "BUY_DEFAULT_POLICY",
                },
            }
        ],
        "page": {
            "page_size": 250,
            "sort_key": "acquisition_date:asc,lot_id:asc",
            "returned_component_count": 1,
            "request_scope_fingerprint": "tax-lot-scope-001",
            "next_page_token": None,
        },
        "supportability": {
            "state": "READY",
            "reason": "TAX_LOTS_READY",
            "requested_security_count": 1,
            "returned_lot_count": 1,
            "missing_security_ids": [],
        },
        "lineage": {
            "source_system": "position_lot_state",
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


def test_core_resolver_fetches_mandate_binding_from_dedicated_source_product():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["correlation_id"] = request.headers.get("X-Correlation-Id")
        seen["payload"] = request.read()
        return httpx.Response(200, json=_mandate_binding_payload())

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = client.resolve_mandate_binding(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=date(2026, 4, 10),
        tenant_id="tenant_sg_pb",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        booking_center_code="Singapore",
        include_policy_pack=True,
        correlation_id="corr-mandate-001",
    )

    assert seen["url"] == (
        "https://core.example.test/integration/portfolios/PB_SG_GLOBAL_BAL_001/mandate-binding"
    )
    assert seen["correlation_id"] == "corr-mandate-001"
    assert b'"as_of_date":"2026-04-10"' in seen["payload"]
    assert b'"tenant_id":"tenant_sg_pb"' in seen["payload"]
    assert b'"mandate_id":"MANDATE_PB_SG_GLOBAL_BAL_001"' in seen["payload"]
    assert b'"booking_center_code":"Singapore"' in seen["payload"]
    assert b'"include_policy_pack":true' in seen["payload"]
    assert response.product_name == "DiscretionaryMandateBinding"
    assert response.supportability.state == "READY"
    assert response.policy_pack_id == "POLICY_DPM_SG_BALANCED_V1"
    assert response.rebalance_bands.default_band == Decimal("0.0250000000")


def test_core_resolver_fetches_instrument_eligibility_from_dedicated_source_product():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["correlation_id"] = request.headers.get("X-Correlation-Id")
        seen["payload"] = request.read()
        return httpx.Response(200, json=_instrument_eligibility_payload())

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = client.resolve_instrument_eligibility(
        security_ids=["EQ_US_AAPL"],
        as_of_date=date(2026, 4, 10),
        tenant_id="tenant_sg_pb",
        include_restricted_rationale=False,
        correlation_id="corr-eligibility-001",
    )

    assert seen["url"] == "https://core.example.test/integration/instruments/eligibility-bulk"
    assert seen["correlation_id"] == "corr-eligibility-001"
    assert b'"as_of_date":"2026-04-10"' in seen["payload"]
    assert b'"security_ids":["EQ_US_AAPL"]' in seen["payload"]
    assert b'"tenant_id":"tenant_sg_pb"' in seen["payload"]
    assert b'"include_restricted_rationale":false' in seen["payload"]
    assert response.product_name == "InstrumentEligibilityProfile"
    assert response.supportability.state == "READY"
    assert response.eligibility[0].security_id == "EQ_US_AAPL"


def test_core_resolver_fetches_portfolio_tax_lots_from_dedicated_source_product():
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["correlation_id"] = request.headers.get("X-Correlation-Id")
        seen["payload"] = request.read()
        return httpx.Response(200, json=_portfolio_tax_lots_payload())

    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = client.resolve_portfolio_tax_lots(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=date(2026, 4, 10),
        security_ids=["EQ_US_AAPL"],
        lot_status_filter="OPEN",
        include_closed_lots=False,
        page_size=250,
        page_token=None,
        tenant_id="tenant_sg_pb",
        correlation_id="corr-tax-lots-001",
    )

    assert seen["url"] == (
        "https://core.example.test/integration/portfolios/PB_SG_GLOBAL_BAL_001/tax-lots"
    )
    assert seen["correlation_id"] == "corr-tax-lots-001"
    assert b'"as_of_date":"2026-04-10"' in seen["payload"]
    assert b'"security_ids":["EQ_US_AAPL"]' in seen["payload"]
    assert b'"lot_status_filter":"OPEN"' in seen["payload"]
    assert b'"include_closed_lots":false' in seen["payload"]
    assert b'"page":{"page_size":250,"page_token":null}' in seen["payload"]
    assert b'"tenant_id":"tenant_sg_pb"' in seen["payload"]
    assert response.product_name == "PortfolioTaxLotWindow"
    assert response.supportability.state == "READY"
    assert response.lots[0].lot_id == "LOT-AAPL-001"


def test_core_resolver_maps_mandate_binding_4xx_to_incomplete_error():
    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(404, json={"detail": "x"}))
        ),
    )

    with pytest.raises(DpmCoreResolverError, match="DPM_CORE_MANDATE_BINDING_INCOMPLETE"):
        client.resolve_mandate_binding(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=date(2026, 4, 10),
            correlation_id=None,
        )


def test_core_resolver_maps_instrument_eligibility_4xx_to_incomplete_error():
    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(404, json={"detail": "x"}))
        ),
    )

    with pytest.raises(DpmCoreResolverError, match="DPM_CORE_INSTRUMENT_ELIGIBILITY_INCOMPLETE"):
        client.resolve_instrument_eligibility(
            security_ids=["UNKNOWN_SEC"],
            as_of_date=date(2026, 4, 10),
            correlation_id=None,
        )


def test_core_resolver_maps_portfolio_tax_lot_4xx_to_incomplete_error():
    client = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(404, json={"detail": "x"}))
        ),
    )

    with pytest.raises(DpmCoreResolverError, match="DPM_CORE_PORTFOLIO_TAX_LOTS_INCOMPLETE"):
        client.resolve_portfolio_tax_lots(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            as_of_date=date(2026, 4, 10),
            correlation_id=None,
        )


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
