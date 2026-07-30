import json
from decimal import Decimal

import httpx
import pytest

import src.api.observability as observability_module
from src.infrastructure.core_sourcing.client import (
    DpmCoreResolverClient,
    DpmCoreResolverConfig,
    DpmCoreResolverError,
    DpmCoreResolverUnavailableError,
    _cash_balance_currencies,
    _core_snapshot_row_currency,
    _final_source_product_attempt,
    _map_core_snapshot_row,
    _portfolio_snapshot_from_core_snapshot,
    _portfolio_positions_and_cash_from_core_rows,
    _position_market_value_currencies,
    _required_currency_pairs,
    _required_non_base_currencies,
    _should_retry_transient_source_status,
    _source_product_payload_with_retries,
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


def test_source_product_retry_helper_maps_transient_status_then_payload() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(503, json={"detail": "retry"})
        return httpx.Response(200, json={"source": "ready"})

    payload = _source_product_payload_with_retries(
        httpx.Client(transport=httpx.MockTransport(handler)),
        attempts=2,
        method="get",
        url="https://core.example.test/integration/source",
        selector={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
        headers={"X-Correlation-Id": "corr-source"},
        unavailable_code="UNAVAILABLE",
        incomplete_code="INCOMPLETE",
    )

    assert payload == {"source": "ready"}
    assert calls["count"] == 2


def test_source_product_retry_helper_records_bounded_source_http_metrics(monkeypatch) -> None:
    captured: list[tuple[str, dict[str, str]]] = []
    calls = 0

    class _Counter:
        def __init__(self, name: str) -> None:
            self.name = name

        def labels(self, **labels):
            captured.append((self.name, labels))
            return self

        def inc(self) -> None:
            return None

    class _Histogram:
        def labels(self, **labels):
            captured.append(("duration", labels))
            return self

        def observe(self, value: float) -> None:
            assert value >= 0.0
            return None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.headers["X-Correlation-Id"] == "corr-source"
        if calls == 1:
            raise httpx.ConnectTimeout("temporary timeout")
        if calls == 2:
            return httpx.Response(503, json={"detail": "retry"})
        return httpx.Response(200, json={"source": "ready"})

    monkeypatch.setattr(
        observability_module,
        "SOURCE_HTTP_REQUEST_TOTAL",
        _Counter("request"),
    )
    monkeypatch.setattr(
        observability_module,
        "SOURCE_HTTP_RETRY_TOTAL",
        _Counter("retry"),
    )
    monkeypatch.setattr(
        observability_module,
        "SOURCE_HTTP_REQUEST_DURATION_SECONDS",
        _Histogram(),
    )

    payload = _source_product_payload_with_retries(
        httpx.Client(transport=httpx.MockTransport(handler)),
        attempts=3,
        method="get",
        url="https://core.example.test/integration/source",
        selector={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
        headers={"X-Correlation-Id": "corr-source"},
        unavailable_code="UNAVAILABLE",
        incomplete_code="INCOMPLETE",
        source_service="lotus-core",
    )

    assert payload == {"source": "ready"}
    assert captured == [
        (
            "retry",
            {
                "source_service": "lotus-core",
                "method": "get",
                "reason": "transport_error",
            },
        ),
        (
            "retry",
            {
                "source_service": "lotus-core",
                "method": "get",
                "reason": "transient_status",
            },
        ),
        (
            "request",
            {
                "source_service": "lotus-core",
                "method": "get",
                "outcome": "success",
            },
        ),
        (
            "duration",
            {
                "source_service": "lotus-core",
                "method": "get",
                "outcome": "success",
            },
        ),
    ]
    assert "PB_SG_GLOBAL_BAL_001" not in json.dumps(captured)
    assert "corr-source" not in json.dumps(captured)


def test_source_product_retry_helper_exhausts_transient_status_safely() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(503, json={"detail": "still unavailable"})

    with pytest.raises(DpmCoreResolverUnavailableError, match="UNAVAILABLE"):
        _source_product_payload_with_retries(
            httpx.Client(transport=httpx.MockTransport(handler)),
            attempts=2,
            method="post",
            url="https://core.example.test/integration/source",
            selector={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
            headers={},
            unavailable_code="UNAVAILABLE",
            incomplete_code="INCOMPLETE",
        )

    assert calls["count"] == 2


@pytest.mark.parametrize(
    ("attempt_index", "attempts", "expected"),
    [
        (0, 2, False),
        (1, 2, True),
        (0, 1, True),
    ],
)
def test_final_source_product_attempt_identifies_retry_boundary(
    attempt_index: int,
    attempts: int,
    expected: bool,
) -> None:
    assert _final_source_product_attempt(attempt_index=attempt_index, attempts=attempts) is expected


@pytest.mark.parametrize(
    ("status_code", "attempt_index", "attempts", "expected"),
    [
        (503, 0, 2, True),
        (502, 1, 2, False),
        (504, 0, 1, False),
        (500, 0, 2, False),
        (429, 0, 2, False),
    ],
)
def test_should_retry_transient_source_status_only_before_final_attempt(
    status_code: int,
    attempt_index: int,
    attempts: int,
    expected: bool,
) -> None:
    assert (
        _should_retry_transient_source_status(
            httpx.Response(status_code, json={"detail": "source posture"}),
            attempt_index=attempt_index,
            attempts=attempts,
        )
        is expected
    )


def test_core_resolver_source_product_helpers_preserve_selector_transport_shape() -> None:
    seen: dict[str, dict[str, str | dict[str, object]]] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            seen["post"] = {
                "correlation_id": request.headers["X-Correlation-Id"],
                "json": json.loads(request.content),
            }
        else:
            seen["get"] = {
                "correlation_id": request.headers["X-Correlation-Id"],
                "portfolio_id": request.url.params["portfolio_id"],
            }
        return httpx.Response(200, json={"ok": True})

    resolver = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url="https://core.example.test"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert resolver._post_source_product(
        url="https://core.example.test/integration/test",
        payload={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
        correlation_id="corr-post",
        unavailable_code="UNAVAILABLE",
        incomplete_code="INCOMPLETE",
    ) == {"ok": True}
    assert resolver._get_source_product(
        url="https://core.example.test/integration/test",
        params={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
        correlation_id="corr-get",
        unavailable_code="UNAVAILABLE",
        incomplete_code="INCOMPLETE",
    ) == {"ok": True}

    assert seen == {
        "post": {
            "correlation_id": "corr-post",
            "json": {"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
        },
        "get": {
            "correlation_id": "corr-get",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        },
    }


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


def test_core_snapshot_transform_uses_reporting_currency_and_valid_zero_quantity() -> None:
    snapshot = _portfolio_snapshot_from_core_snapshot(
        {
            "portfolio_id": "PF_TEST",
            "as_of_date": "2026-04-10",
            "valuation_context": {"reporting_currency": "EUR"},
            "sections": {
                "positions_baseline": [
                    {
                        "instrument_id": "EQ_EU",
                        "quantity": "0",
                        "currency": "EUR",
                        "market_value_local": "0",
                    },
                    {"instrument_id": "CASH_USD", "quantity": "250", "currency": "USD"},
                ],
                "portfolio_totals": {"baseline_total_market_value_base": "250"},
            },
        }
    )

    assert snapshot.snapshot_id == "PortfolioStateSnapshot:PF_TEST:2026-04-10"
    assert snapshot.base_currency == "EUR"
    assert [position.instrument_id for position in snapshot.positions] == ["EQ_EU"]
    assert snapshot.positions[0].quantity == Decimal("0")
    assert snapshot.cash_balances[0].currency == "USD"


def test_core_snapshot_row_mapper_rejects_blank_identifier() -> None:
    with pytest.raises(ValueError, match="instrument_id"):
        _map_core_snapshot_row({"quantity": "99"}, base_currency="USD")


def test_core_snapshot_row_mapper_preserves_position_market_value_currency() -> None:
    mapped_row = _map_core_snapshot_row(
        {
            "security_id": "EQ_US",
            "quantity": "12.5",
            "currency": "usd",
            "market_value_local": "1234.56",
        },
        base_currency="SGD",
    )

    assert mapped_row is not None
    assert mapped_row.position is not None
    assert mapped_row.position.instrument_id == "EQ_US"
    assert mapped_row.position.quantity == Decimal("12.5")
    assert mapped_row.position.market_value is not None
    assert mapped_row.position.market_value.amount == Decimal("1234.56")
    assert mapped_row.position.market_value.currency == "USD"
    assert mapped_row.position._core_source_identity_namespace == "security_id"


def test_core_snapshot_row_mapper_marks_instrument_fallback_identity_namespace() -> None:
    mapped_row = _map_core_snapshot_row(
        {
            "instrument_id": "AAPL",
            "quantity": "12.5",
            "currency": "usd",
            "market_value_local": "1234.56",
        },
        base_currency="SGD",
    )

    assert mapped_row is not None
    assert mapped_row.position is not None
    assert mapped_row.position.instrument_id == "AAPL"
    assert mapped_row.position._core_source_identity_namespace == "instrument_id"


def test_core_snapshot_row_currency_normalizes_and_rejects_missing_currency() -> None:
    assert _core_snapshot_row_currency({"currency": "sgd"}, base_currency="USD") == "SGD"
    with pytest.raises(ValueError, match="currency"):
        _core_snapshot_row_currency({}, base_currency="eur")


def test_core_snapshot_rows_aggregate_cash_by_currency() -> None:
    positions, cash_by_currency = _portfolio_positions_and_cash_from_core_rows(
        [
            {"instrument_id": "CASH_USD", "quantity": "10", "currency": "USD"},
            {"instrument_id": "CASH_USD_2", "quantity": "15", "currency": "USD"},
            {
                "instrument_id": "EQ_EU",
                "quantity": "2",
                "currency": "EUR",
                "market_value_local": "20",
            },
        ],
        base_currency="SGD",
    )

    assert [position.instrument_id for position in positions] == ["EQ_EU"]
    assert cash_by_currency == {"USD": Decimal("25")}


def test_core_snapshot_currency_helpers_return_uppercase_non_base_families() -> None:
    snapshot = _portfolio_snapshot_from_core_snapshot(
        {
            "portfolio_id": "PF_TEST",
            "as_of_date": "2026-04-10",
            "valuation_context": {"portfolio_currency": "USD"},
            "sections": {
                "positions_baseline": [
                    {
                        "instrument_id": "EQ_US",
                        "quantity": "10",
                        "currency": "usd",
                        "market_value_local": "100",
                    },
                    {
                        "instrument_id": "EQ_EU",
                        "quantity": "5",
                        "currency": "eur",
                        "market_value_local": "50",
                    },
                    {"instrument_id": "CASH_GBP", "quantity": "100", "currency": "gbp"},
                ],
                "portfolio_totals": {"baseline_total_market_value_base": "250"},
            },
        }
    )

    assert _position_market_value_currencies(snapshot.positions) == {"EUR", "USD"}
    assert _cash_balance_currencies(snapshot.cash_balances) == {"GBP"}
    assert _required_non_base_currencies(
        portfolio_snapshot=snapshot,
        base_currency="USD",
    ) == {"EUR", "GBP"}


def test_required_currency_pairs_ignores_base_currency() -> None:
    snapshot = _portfolio_snapshot_from_core_snapshot(
        {
            "portfolio_id": "PF_TEST",
            "as_of_date": "2026-04-10",
            "valuation_context": {"portfolio_currency": "USD"},
            "sections": {
                "positions_baseline": [
                    {
                        "instrument_id": "EQ_US",
                        "quantity": "10",
                        "currency": "USD",
                        "market_value_local": "100",
                    },
                    {"instrument_id": "CASH_EUR", "quantity": "100", "currency": "EUR"},
                ],
                "portfolio_totals": {"baseline_total_market_value_base": "200"},
            },
        }
    )

    assert _required_currency_pairs(portfolio_snapshot=snapshot, base_currency="USD") == [
        ("EUR", "USD")
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"portfolio_id": "PF_TEST"},
        {
            "portfolio_id": "PF_TEST",
            "as_of_date": "2026-04-10",
            "valuation_context": {"portfolio_currency": "USD"},
            "sections": {"portfolio_totals": {}},
        },
        {
            "portfolio_id": "PF_TEST",
            "as_of_date": "2026-04-10",
            "valuation_context": {"portfolio_currency": "US"},
            "sections": {"positions_baseline": [], "portfolio_totals": {}},
        },
        {
            "portfolio_id": "PF_TEST",
            "as_of_date": "2026-04-10",
            "valuation_context": {"portfolio_currency": "USD"},
            "sections": {
                "positions_baseline": [{"instrument_id": "EQ_US", "currency": "USD"}],
                "portfolio_totals": {},
            },
        },
        {
            "portfolio_id": "PF_TEST",
            "as_of_date": "2026-04-10",
            "valuation_context": {"portfolio_currency": "USD"},
            "sections": {
                "positions_baseline": [
                    {"instrument_id": "EQ_US", "quantity": "1", "currency": "USD"}
                ],
                "portfolio_totals": {},
            },
        },
    ],
)
def test_core_snapshot_mapper_fails_closed_on_incomplete_source_payloads(
    payload: dict[str, object],
) -> None:
    with pytest.raises(DpmCoreResolverError, match="DPM_CORE_PORTFOLIO_SNAPSHOT_INCOMPLETE"):
        _portfolio_snapshot_from_core_snapshot(payload)
