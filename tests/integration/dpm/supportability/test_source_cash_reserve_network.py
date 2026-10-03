"""Supported native HTTP + PostgreSQL + controlled Core contract economics.

Not execution of Core, bank ingestion, authenticated IAM or capacity certification.
All financial records are created by supported APIs, never by direct database writes.
"""

from decimal import Decimal
import uuid

import psycopg
import pytest

from tests.integration.dpm.controlled_core import AS_OF, controlled_core
from tests.integration.dpm.network_runtime import disposable_database, native_api


def _headers(tenant):
    return {
        "X-Tenant-Id": tenant,
        "X-Actor-Id": "reserve-pm",
        "X-Service-Identity": "local-reserve-proof",
        "X-Role": "PM",
        "X-Capabilities": "manage.write",
        "Idempotency-Key": uuid.uuid4().hex,
        "X-Correlation-Id": uuid.uuid4().hex,
    }


def _request(portfolio, tenant):
    return {
        "input_mode": "stateful",
        "stateful_input": {
            "portfolio_id": portfolio,
            "tenant_id": tenant,
            "as_of": AS_OF,
            "mandate_id": "mandate-reserve",
            "model_portfolio_id": "model-reserve",
            "booking_center_code": "SG",
            "include_tax_lots": False,
        },
        "options_override": {
            "enable_settlement_awareness": False,
            "enable_tax_awareness": False,
        },
    }


def _call(client, method, path, headers, body=None, expected=200):
    response = client.request(method, path, headers=headers, json=body)
    assert response.status_code == expected, response.text
    return response.json()


def _assert_result(result, reserve, *, expected_shares, expected_cash, price=100):
    # Independent one-security USD arithmetic:100*100+90,000=100,000;
    # invest(1-reserve)*100,000 at100, then reconcile shares and residual cash.
    assert Decimal(result["before"]["total_value"]["amount"]) == 100000
    assert Decimal(result["after_simulated"]["total_value"]["amount"]) == 100000
    assert Decimal(result["after_simulated"]["positions"][0]["quantity"]) == expected_shares
    assert Decimal(result["after_simulated"]["cash_balances"][0]["amount"]) == expected_cash
    assert expected_shares * price + expected_cash == 100000
    lineage = result["lineage"]
    assert lineage["source_mandate_binding_version"] == 7
    assert lineage["source_mandate_effective_from"] == "2026-04-01"
    assert lineage["source_mandate_effective_to"] == "2026-04-30"
    assert lineage["source_mandate_lineage"]["source_record_id"] == "mandate-reserve-v7"
    assert lineage["source_cash_reserve_scope"] == "TOTAL_PORTFOLIO_MARKET_VALUE"
    assert lineage["source_cash_reserve_currency_basis"] == "PORTFOLIO_BASE_CURRENCY"
    assert lineage["source_cash_reserve_authority"] == "MANDATE_BINDING"
    assert lineage["source_cash_reserve_consumer_override_allowed"] is False
    rules = [row for row in result["rule_results"] if row["rule_id"] == "CASH_RESERVE_TARGET"]
    if reserve is None:
        assert lineage["source_cash_reserve_target_weight"] is None
        assert lineage["cash_reserve_override_authority"] is None
        assert not rules
    else:
        assert Decimal(lineage["source_cash_reserve_target_weight"]) == Decimal(reserve)
        assert lineage["cash_reserve_override_authority"] == "NONE"
        assert len(rules) == 1
        assert Decimal(rules[0]["threshold"]["target"]) == Decimal(reserve)


@pytest.mark.parametrize(
    ("reserve", "shares", "cash"),
    [("0.02", 980, 2000), ("0", 1000, 0), (None, 1000, 0), ("0.5", 500, 50000)],
)
def test_stateful_source_reserve_http_economics_and_retained_replay(reserve, shares, cash):
    portfolio, tenant = f"reserve-{uuid.uuid4().hex}", f"tenant-{uuid.uuid4().hex}"
    headers = _headers(tenant)
    request = _request(portfolio, tenant)
    with controlled_core(portfolio=portfolio, reserve=reserve) as (core_url, observations):
        with disposable_database() as dsn:
            with native_api(dsn, core_url=core_url) as (client, _process):
                result = _call(client, "POST", "/api/v1/rebalance/simulate", headers, request)
                _assert_result(result, reserve, expected_shares=shares, expected_cash=cash)
                if reserve == "0.02":
                    refreshed = _call(
                        client,
                        "POST",
                        "/api/v1/mandates/mandate-reserve/refresh-from-core",
                        _headers(tenant),
                        {"portfolio_id": portfolio, "tenant_id": tenant, "as_of_date": AS_OF},
                    )
                    assert Decimal(
                        refreshed["mandate"]["constraints"]["cash_reserve_weight"]
                    ) == Decimal(reserve)
                    retained = _call(
                        client,
                        "GET",
                        f"/api/v1/mandates/mandate-reserve?tenant_id={tenant}",
                        _headers(tenant),
                    )
                    assert retained["mandate_version"] == "7"
                path = f"/api/v1/rebalance/runs/{result['rebalance_run_id']}/artifact"
                artifact = _call(client, "GET", path, headers)
                _assert_result(
                    artifact["result"], reserve, expected_shares=shares, expected_cash=cash
                )
                _call(client, "GET", path, {**headers, "X-Tenant-Id": "foreign"}, expected=404)
            with native_api(dsn, core_url=core_url) as (client, _replacement):
                assert _call(client, "GET", path, headers) == artifact
                replay = _call(client, "POST", "/api/v1/rebalance/simulate", headers, request)
                assert replay["rebalance_run_id"] == result["rebalance_run_id"]
                assert replay["lineage"] == result["lineage"]
            with psycopg.connect(dsn) as connection:
                assert connection.execute("SELECT count(*) FROM dpm_runs").fetchone()[0] == 1
        requests = list(observations.queue)
        assert requests[0][0].endswith("/mandate-binding")
        assert requests[0][1]["as_of_date"] == AS_OF
        assert all(row[2] == tenant for row in requests)


def test_stateful_batch_cash_target_and_constrained_deviation_are_not_silently_approved():
    portfolio, tenant = f"reserve-{uuid.uuid4().hex}", f"tenant-{uuid.uuid4().hex}"
    request = _request(portfolio, tenant)
    del request["options_override"]
    request["scenarios"] = {
        "baseline": {"options": {"enable_settlement_awareness": False}},
        "position_cap": {
            "options": {"single_position_max_weight": "0.5", "enable_settlement_awareness": False}
        },
    }
    with controlled_core(portfolio=portfolio) as (core_url, _observations):
        with disposable_database() as dsn, native_api(dsn, core_url=core_url) as (client, _process):
            results = _call(client, "POST", "/api/v1/rebalance/analyze", _headers(tenant), request)[
                "results"
            ]
            _assert_result(results["baseline"], "0.02", expected_shares=980, expected_cash=2000)
            _assert_result(
                results["position_cap"], "0.02", expected_shares=500, expected_cash=50000
            )
            assert results["baseline"]["gate_decision"]["gate"] == "EXECUTION_READY"
            assert results["position_cap"]["gate_decision"]["gate"] == "RISK_REVIEW_REQUIRED"
            assert "SOFT_RULE_FAIL:CASH_RESERVE_TARGET" in {
                row["reason_code"] for row in results["position_cap"]["gate_decision"]["reasons"]
            }


@pytest.mark.parametrize("invalid_target", [None, "0.02"])
def test_invalid_legacy_source_cannot_enter_runs_or_mandate_state(invalid_target):
    portfolio, tenant = f"reserve-{uuid.uuid4().hex}", f"tenant-{uuid.uuid4().hex}"
    with controlled_core(portfolio=portfolio, reserve=invalid_target, invalid_legacy=True) as (
        core_url,
        observations,
    ):
        with disposable_database() as dsn, native_api(dsn, core_url=core_url) as (client, _process):
            _call(
                client,
                "POST",
                "/api/v1/rebalance/simulate",
                _headers(tenant),
                _request(portfolio, tenant),
                expected=424,
            )
            _call(
                client,
                "POST",
                "/api/v1/mandates/mandate-reserve/refresh-from-core",
                _headers(tenant),
                {"portfolio_id": portfolio, "tenant_id": tenant, "as_of_date": AS_OF},
                expected=424,
            )
            _call(
                client,
                "GET",
                f"/api/v1/mandates/mandate-reserve?tenant_id={tenant}",
                _headers(tenant),
                expected=404,
            )
            with psycopg.connect(dsn) as connection:
                assert connection.execute("SELECT count(*) FROM dpm_runs").fetchone()[0] == 0
        assert len(list(observations.queue)) == 2


def test_conflicting_overrides_leave_no_financial_records():
    portfolio, tenant = f"reserve-{uuid.uuid4().hex}", f"tenant-{uuid.uuid4().hex}"
    with controlled_core(portfolio=portfolio) as (core_url, _observations):
        with disposable_database() as dsn, native_api(dsn, core_url=core_url) as (client, _process):
            request = _request(portfolio, tenant)
            for override in [
                {"cash_reserve_target_weight": "0"},
                {"min_cash_buffer_pct": "0.5"},
                {"cash_reserve_target_tolerance": "1"},
            ]:
                request["options_override"] = override
                _call(
                    client,
                    "POST",
                    "/api/v1/rebalance/simulate",
                    _headers(tenant),
                    request,
                    expected=424,
                )
            with psycopg.connect(dsn) as connection:
                assert connection.execute("SELECT count(*) FROM dpm_runs").fetchone()[0] == 0


@pytest.mark.parametrize("batch", [False, True])
def test_absent_source_target_refuses_caller_target_but_allows_independent_buffer(batch):
    portfolio, tenant = f"reserve-{uuid.uuid4().hex}", f"tenant-{uuid.uuid4().hex}"
    path = "/api/v1/rebalance/analyze" if batch else "/api/v1/rebalance/simulate"
    with controlled_core(portfolio=portfolio, reserve=None) as (core_url, _observations):
        with disposable_database() as dsn, native_api(dsn, core_url=core_url) as (client, _process):
            request = _request(portfolio, tenant)
            base_options = request.pop("options_override")

            def set_options(override):
                options = {**base_options, **override}
                if batch:
                    request["scenarios"] = {"caller": {"options": options}}
                else:
                    request["options_override"] = options

            for override in [
                {"cash_reserve_target_weight": "0"},
                {"cash_reserve_target_weight": "0.02"},
                {"cash_reserve_target_tolerance": "1"},
            ]:
                set_options(override)
                _call(client, "POST", path, _headers(tenant), request, expected=424)
            with psycopg.connect(dsn) as connection:
                assert connection.execute("SELECT count(*) FROM dpm_runs").fetchone()[0] == 0

            set_options({"cash_reserve_target_weight": None, "min_cash_buffer_pct": "0.03"})
            response = _call(client, "POST", path, _headers(tenant), request)
            result = response["results"]["caller"] if batch else response
            # The independent 3% operating buffer leaves $3,000; no mandate target is invented.
            _assert_result(result, None, expected_shares=970, expected_cash=3000)


def test_source_reserve_whole_share_residual_requires_review_without_widening_tolerance():
    portfolio, tenant = f"reserve-{uuid.uuid4().hex}", f"tenant-{uuid.uuid4().hex}"
    with controlled_core(portfolio=portfolio, price=123) as (core_url, _observations):
        with disposable_database() as dsn, native_api(dsn, core_url=core_url) as (client, _process):
            result = _call(
                client,
                "POST",
                "/api/v1/rebalance/simulate",
                _headers(tenant),
                _request(portfolio, tenant),
            )
            # floor(98,000 / 123) = 796 shares; cash = 100,000 - 796 * 123 = 2,092.
            _assert_result(result, "0.02", expected_shares=796, expected_cash=2092, price=123)
            reserve_rule = next(
                row for row in result["rule_results"] if row["rule_id"] == "CASH_RESERVE_TARGET"
            )
            assert Decimal(reserve_rule["measured"]) == Decimal("0.02092")
            assert Decimal(reserve_rule["threshold"]["tolerance"]) == Decimal("0.0001")
            assert reserve_rule["status"] == "FAIL"
            assert reserve_rule["reason_code"] == "TARGET_DEVIATION"
            assert result["gate_decision"]["gate"] == "RISK_REVIEW_REQUIRED"
