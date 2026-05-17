import httpx
import pytest

from src.infrastructure.core_sourcing.client import (
    DpmCoreResolverClient,
    DpmCoreResolverConfig,
    DpmCoreResolverError,
    DpmCoreResolverUnavailableError,
    _portfolio_snapshot_from_core_snapshot,
    _required_currency_pairs,
)


@pytest.mark.parametrize(
    ("field", "method_name", "expected_code"),
    [
        (
            "model_portfolio_targets_path_template",
            "resolve_model_portfolio_targets_url",
            "DPM_CORE_MODEL_TARGET_RESOLVER_UNAVAILABLE",
        ),
        (
            "mandate_binding_path_template",
            "resolve_mandate_binding_url",
            "DPM_CORE_MANDATE_BINDING_UNAVAILABLE",
        ),
        (
            "portfolio_manager_book_memberships_path_template",
            "resolve_portfolio_manager_book_memberships_url",
            "DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE",
        ),
        (
            "cio_model_change_affected_cohort_path_template",
            "resolve_cio_model_change_affected_cohort_url",
            "DPM_CORE_CIO_MODEL_CHANGE_COHORT_UNAVAILABLE",
        ),
        (
            "instrument_eligibility_path_template",
            "resolve_instrument_eligibility_url",
            "DPM_CORE_INSTRUMENT_ELIGIBILITY_UNAVAILABLE",
        ),
        (
            "portfolio_tax_lots_path_template",
            "resolve_portfolio_tax_lots_url",
            "DPM_CORE_PORTFOLIO_TAX_LOTS_UNAVAILABLE",
        ),
        (
            "market_data_coverage_path_template",
            "resolve_market_data_coverage_url",
            "DPM_CORE_MARKET_DATA_COVERAGE_UNAVAILABLE",
        ),
        (
            "transaction_cost_curve_path_template",
            "resolve_transaction_cost_curve_url",
            "DPM_CORE_TRANSACTION_COST_CURVE_UNAVAILABLE",
        ),
        (
            "external_order_execution_acknowledgement_path_template",
            "resolve_external_order_execution_acknowledgement_url",
            "DPM_CORE_EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT_UNAVAILABLE",
        ),
    ],
)
def test_core_resolver_config_rejects_blank_source_product_paths(
    field: str,
    method_name: str,
    expected_code: str,
) -> None:
    config = DpmCoreResolverConfig(base_url="https://core.example.test", **{field: ""})
    method = getattr(config, method_name)

    with pytest.raises(DpmCoreResolverUnavailableError, match=expected_code):
        if method_name in {
            "resolve_model_portfolio_targets_url",
            "resolve_mandate_binding_url",
            "resolve_portfolio_manager_book_memberships_url",
            "resolve_cio_model_change_affected_cohort_url",
            "resolve_portfolio_tax_lots_url",
            "resolve_transaction_cost_curve_url",
            "resolve_external_order_execution_acknowledgement_url",
        }:
            method("identifier")
        else:
            method()


def test_core_resolver_config_rejects_blank_and_legacy_execution_context_paths() -> None:
    blank_config = DpmCoreResolverConfig(base_url="https://core.example.test")
    with pytest.raises(DpmCoreResolverUnavailableError, match="DPM_CORE_RESOLVER_UNAVAILABLE"):
        blank_config.resolve_url("PF_TEST")

    legacy_config = DpmCoreResolverConfig(
        base_url="https://core.example.test",
        path_template="/integration/portfolios/{portfolio_id}/dpm-execution-context",
    )
    with pytest.raises(DpmCoreResolverUnavailableError, match="DPM_CORE_RESOLVER_UNAVAILABLE"):
        legacy_config.resolve_url("PF_TEST")

    active_config = DpmCoreResolverConfig(
        base_url="https://core.example.test/",
        path_template="/integration/portfolios/{portfolio_id}/core-snapshot",
    )
    assert active_config.resolve_url("PF_TEST") == (
        "https://core.example.test/integration/portfolios/PF_TEST/core-snapshot"
    )


def test_core_resolver_shared_post_helper_retries_transport_then_succeeds() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            raise httpx.TransportError("connection reset")
        return httpx.Response(200, json={"ok": True})

    resolver = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test", max_attempts=2),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = resolver._post_source_product(
        url="https://core.example.test/integration/test",
        payload={"selector": "value"},
        correlation_id="corr-1",
        unavailable_code="UNAVAILABLE",
        incomplete_code="INCOMPLETE",
    )

    assert response == {"ok": True}
    assert calls["count"] == 2


@pytest.mark.parametrize(
    ("status_code", "expected_error", "expected_code"),
    [
        (400, DpmCoreResolverError, "INCOMPLETE"),
        (500, DpmCoreResolverUnavailableError, "UNAVAILABLE"),
        (503, DpmCoreResolverUnavailableError, "UNAVAILABLE"),
    ],
)
def test_core_resolver_shared_post_helper_maps_terminal_errors(
    status_code: int,
    expected_error: type[Exception],
    expected_code: str,
) -> None:
    resolver = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test", max_attempts=1),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(status_code, json={}))
        ),
    )

    with pytest.raises(expected_error, match=expected_code):
        resolver._post_source_product(
            url="https://core.example.test/integration/test",
            payload={},
            correlation_id=None,
            unavailable_code="UNAVAILABLE",
            incomplete_code="INCOMPLETE",
        )


def test_core_resolver_shared_post_helper_rejects_non_object_success_payload() -> None:
    resolver = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test", max_attempts=1),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=[]))
        ),
    )

    with pytest.raises(DpmCoreResolverError, match="INCOMPLETE"):
        resolver._post_source_product(
            url="https://core.example.test/integration/test",
            payload={},
            correlation_id=None,
            unavailable_code="UNAVAILABLE",
            incomplete_code="INCOMPLETE",
        )


def test_core_resolver_shared_post_helper_closes_owned_client_on_terminal_error(
    monkeypatch,
) -> None:
    closed = {"value": False}

    class _OwnedClient:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        def post(self, *_args, **_kwargs):
            raise httpx.TimeoutException("timeout")

        def close(self) -> None:
            closed["value"] = True

    monkeypatch.setattr(httpx, "Client", _OwnedClient)
    resolver = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test", max_attempts=1)
    )

    with pytest.raises(DpmCoreResolverUnavailableError):
        resolver._post_source_product(
            url="https://core.example.test/integration/test",
            payload={},
            correlation_id=None,
            unavailable_code="UNAVAILABLE",
            incomplete_code="INCOMPLETE",
        )

    assert closed["value"] is True


def test_core_snapshot_transform_uses_reporting_currency_and_skips_blank_rows() -> None:
    snapshot = _portfolio_snapshot_from_core_snapshot(
        {
            "portfolio_id": "PF_TEST",
            "as_of_date": "2026-04-10",
            "valuation_context": {"reporting_currency": "EUR"},
            "sections": {
                "positions_baseline": [
                    {"security_id": "", "quantity": "99", "currency": "EUR"},
                    {"instrument_id": "EQ_EU", "quantity": "10", "currency": "EUR"},
                    {"instrument_id": "CASH_USD", "quantity": "250", "currency": "USD"},
                ]
            },
        }
    )

    assert snapshot.snapshot_id == "PortfolioStateSnapshot:PF_TEST:2026-04-10"
    assert snapshot.base_currency == "EUR"
    assert [position.instrument_id for position in snapshot.positions] == ["EQ_EU"]
    assert snapshot.cash_balances[0].currency == "USD"


def test_required_currency_pairs_ignores_base_currency_and_missing_market_values() -> None:
    snapshot = _portfolio_snapshot_from_core_snapshot(
        {
            "portfolio_id": "PF_TEST",
            "as_of_date": "2026-04-10",
            "sections": {
                "positions_baseline": [
                    {"instrument_id": "EQ_US", "quantity": "10", "currency": "USD"},
                    {"instrument_id": "EQ_NO_VALUE", "quantity": "5"},
                    {"instrument_id": "CASH_EUR", "quantity": "100", "currency": "EUR"},
                ]
            },
        }
    )

    assert _required_currency_pairs(portfolio_snapshot=snapshot, base_currency="USD") == [
        ("EUR", "USD")
    ]
