"""All-method native ownership/recovery; controlled contracts, not live Core/IAM.

Mechanical candidates remain counterfactual when hard policy blocks selection.
Only supported APIs write financial records in the disposable database.
"""

from copy import deepcopy
from decimal import Decimal
import uuid

import psycopg
import pytest

from src.core.construction.vocabulary import ConstructionMethod
from tests.integration.dpm.controlled_core import AS_OF, controlled_core, controlled_products
from tests.integration.dpm.network_runtime import disposable_database, native_api
from tests.shared.factories import valid_api_payload


def _headers(tenant):
    return {
        "X-Tenant-Id": tenant,
        "X-Actor-Id": "method-pm",
        "X-Role": "PM",
        "X-Service-Identity": "local-method-proof",
        "X-Capabilities": "manage.write",
        "Idempotency-Key": uuid.uuid4().hex,
        "X-Correlation-Id": uuid.uuid4().hex,
    }


def _request(portfolio, tenant, mode):
    request = {"input_mode": mode, "methods": [method.value for method in ConstructionMethod]}
    options = {"enable_settlement_awareness": False, "enable_tax_awareness": False}
    if mode == "stateful":
        request.update(
            stateful_input={
                "portfolio_id": portfolio,
                "tenant_id": tenant,
                "as_of": AS_OF,
                "mandate_id": "mandate-reserve",
                "model_portfolio_id": "model-reserve",
                "booking_center_code": "SG",
                "include_tax_lots": False,
            },
            options_override=options,
        )
    else:
        payload = valid_api_payload()
        payload["portfolio_snapshot"].update(
            portfolio_id=portfolio,
            base_currency="USD",
            positions=[{"instrument_id": "EQ_1", "quantity": "975"}],
            cash_balances=[{"currency": "USD", "amount": "2500"}],
        )
        payload["market_data_snapshot"] = {
            "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
            "fx_rates": [],
        }
        payload["model_portfolio"]["targets"] = [{"instrument_id": "EQ_1", "weight": "1"}]
        payload["options"] = {**options, "min_cash_buffer_pct": "0.02"}
        request["stateless_input"] = payload
    return request


def _profile(portfolio, restricted):
    profile = deepcopy(controlled_products(portfolio)["client-restriction-profile"])
    if restricted:
        profile["restrictions"] = [
            {
                "restriction_scope": "instrument",
                "restriction_code": "NO_EQ_TRADE",
                "restriction_status": "ACTIVE",
                "restriction_source": "CLIENT_MANDATE",
                "applies_to_buy": True,
                "applies_to_sell": True,
                "instrument_ids": ["EQ_1"],
                "effective_from": "2026-01-01",
                "restriction_version": 3,
                "source_record_id": "no-eq-trade-v3",
            }
        ]
        profile["supportability"]["restriction_count"] = 1
    return profile


def _call(client, method, path, headers, body=None, expected=200):
    response = client.request(method, path, headers=headers, json=body)
    assert response.status_code == expected, response.text
    return response.json()


def _assert_alternatives(client, owned, headers, mode, restricted):
    assert {row["method"] for row in owned["alternatives"]} == set(ConstructionMethod)
    artifacts = {}
    foreign = {**headers, "X-Tenant-Id": "foreign-method-tenant"}
    for row in owned["alternatives"]:
        if row["method"] == "DO_NOTHING_BASELINE":
            assert row["rebalance_run_id"] is None
            assert row["intent_ids"] == []
            assert row["diagnostics"]["proposed_changes"] == []
            assert row["evaluation_context"]["state_basis"] == "BEFORE"
            continue
        rid = row["rebalance_run_id"]
        path = f"/api/v1/rebalance/runs/{rid}"
        _call(client, "GET", path, headers)
        _call(client, "GET", path, foreign, expected=404)
        artifact = _call(client, "GET", f"{path}/artifact", headers)
        _call(client, "GET", f"{path}/artifact", foreign, expected=404)
        _call(client, "GET", f"{path}/support-bundle", headers)
        _call(client, "GET", f"{path}/support-bundle", foreign, expected=404)
        result = artifact["result"]
        # Independent targets: reserve 2%, liquidity floor 3%, risk position cap 30%.
        shares, cash = {"LIQUIDITY_AWARE": (970, 3000), "RISK_AWARE": (300, 70000)}.get(
            row["method"], (980, 2000)
        )
        for state in ("before", "after_simulated"):
            assert Decimal(result[state]["total_value"]["amount"]) == 100000
        after = result["after_simulated"]
        assert Decimal(after["positions"][0]["quantity"]) == shares, row["method"]
        assert Decimal(after["cash_balances"][0]["amount"]) == cash, row["method"]
        assert shares * 100 + cash == 100000
        changes = row["diagnostics"]["proposed_changes"]
        assert len(changes) == 1
        assert changes[0]["action"] == ("BUY" if shares > 975 else "SELL")
        assert Decimal(changes[0]["quantity"]) == abs(shares - 975)
        if not restricted and row["method"] in {
            "COST_AWARE",
            "LIQUIDITY_AWARE",
            "RISK_AWARE",
            "ESG_AWARE",
            "CURRENCY_OVERLAY",
            "REGIME_STRESS_AWARE",
        }:
            assert row["method_status"] != "READY", row["method"]
        if mode == "stateful":
            assert result["lineage"]["source_mandate_binding_version"] == 7
            trace = [r for r in row["constraint_trace"] if r["constraint"] == "CLIENT_RESTRICTION"]
            assert trace
            assert all(r["status"] == ("BLOCKED" if restricted else "READY") for r in trace)
            if restricted:
                assert row["method_status"] == "BLOCKED"
                assert all(
                    "CLIENT_RESTRICTION_VIOLATION_NO_EQ_TRADE" in r["reason_codes"] for r in trace
                )
                refusal = _call(
                    client,
                    "POST",
                    f"/api/v1/construction/alternative-sets/{owned['alternative_set_id']}/selections",
                    headers,
                    {
                        "alternative_id": row["alternative_id"],
                        "actor_id": "method-pm",
                        "reason_code": "REVIEW",
                    },
                    expected=422,
                )
                assert refusal["detail"] == "CONSTRUCTION_ALTERNATIVE_BLOCKED"
        artifacts[rid] = artifact
    baseline = next(r for r in owned["alternatives"] if r["method"] == "DO_NOTHING_BASELINE")
    assert baseline["evaluation_context"]["rebalance_run_id"] in artifacts
    return artifacts


def _stored_runs(dsn, tenant, artifacts):
    with psycopg.connect(dsn) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        rows = connection.execute(
            "SELECT rebalance_run_id, tenant_id, result_json::jsonb FROM dpm_runs ORDER BY rebalance_run_id"
        ).fetchall()
        assert {row[0] for row in rows} == set(artifacts)
        assert all(row[1] == tenant for row in rows)
        assert all(result == artifacts[rid]["result"] for rid, _owner, result in rows)
        assert {
            row[0] for row in connection.execute("SELECT rebalance_run_id FROM dpm_run_artifacts")
        } == set(artifacts)
        edges = connection.execute(
            "SELECT target_entity_id, tenant_id FROM dpm_lineage_edges"
        ).fetchall()
        assert {row[0] for row in edges} == set(artifacts)
        assert all(row[1] == tenant for row in edges)
        assert (
            connection.execute("SELECT COUNT(*) FROM dpm_construction_alternative_sets").fetchone()[
                0
            ]
            == 1
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM dpm_construction_alternative_selections"
            ).fetchone()[0]
            == 0
        )
        return rows


@pytest.mark.parametrize(
    ("mode", "restricted"), [("stateless", False), ("stateful", False), ("stateful", True)]
)
def test_all_method_owned_artifacts_and_policy_survive_process_replacement(mode, restricted):
    portfolio, tenant = f"methods-{uuid.uuid4().hex}", f"tenant-{uuid.uuid4().hex}"
    headers, request = _headers(tenant), _request(portfolio, tenant, mode)
    generate = "/api/v1/construction/alternative-sets/generate"
    with controlled_core(
        portfolio=portfolio,
        starting_shares=975,
        product_overrides={"client-restriction-profile": _profile(portfolio, restricted)},
    ) as (core_url, observations):
        with disposable_database() as dsn:
            with native_api(dsn, core_url=core_url if mode == "stateful" else None) as (
                client,
                original,
            ):
                _call(
                    client,
                    "POST",
                    generate,
                    {k: v for k, v in headers.items() if k != "X-Tenant-Id"},
                    request,
                    expected=403,
                )
                owned = _call(client, "POST", generate, headers, request)
                artifacts = _assert_alternatives(client, owned, headers, mode, restricted)
                assert _call(client, "POST", generate, headers, request) == owned
                changed = {**request, "methods": ["HEURISTIC_EXPLAINABLE"]}
                _call(client, "POST", generate, headers, changed, expected=409)
                before = _stored_runs(dsn, tenant, artifacts)
                old_pid = original.pid
                original.kill()
                original.join(10)
                assert original.exitcode not in (None, 0)
            with native_api(dsn, core_url=core_url if mode == "stateful" else None) as (
                client,
                replacement,
            ):
                assert replacement.pid != old_pid
                path = f"/api/v1/construction/alternative-sets/{owned['alternative_set_id']}"
                assert _call(client, "GET", path, headers) == owned
                _call(
                    client,
                    "GET",
                    path,
                    {**headers, "X-Tenant-Id": "foreign-method-tenant"},
                    expected=404,
                )
                assert _call(client, "POST", generate, headers, request) == owned
                assert _assert_alternatives(client, owned, headers, mode, restricted) == artifacts
            assert _stored_runs(dsn, tenant, artifacts) == before
        source_calls = list(observations.queue)
        assert all(call[2] == tenant for call in source_calls)
        assert bool(source_calls) == (mode == "stateful")
