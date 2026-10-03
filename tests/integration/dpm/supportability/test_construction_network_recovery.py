"""Native network/process recovery, not Core authority, production IAM or capacity.

Each case owns a disposable database. SQL only sets up/tears down schema or reads
durability evidence; financial records are created through the unmodified API.
The configured authorization policy remains enabled with caller-asserted headers.
"""

from __future__ import annotations

import json
import multiprocessing
import os
import socket
import threading
import time
import uuid
from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal

import httpx
import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row

from src.infrastructure.postgres_migrations import apply_postgres_migrations
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip
from tests.shared.factories import valid_api_payload


@contextmanager
def _database():
    dsn = postgres_dsn_or_skip("construction network/API-process recovery")
    name = f"manage_network_{uuid.uuid4().hex}"
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            isolated = make_conninfo(dsn, dbname=name)
            with psycopg.connect(isolated, row_factory=dict_row) as connection:
                apply_postgres_migrations(connection=connection, namespace="dpm")
            yield isolated
        finally:
            # Only this successfully created UUID database is eligible for removal.
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
            assert (
                admin.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,)).fetchone()
                is None
            )


def _serve(dsn, pipe, stop):
    # Spawned interpreters do not inherit parent's in-process dependency overrides.
    for name in list(os.environ):
        if name.startswith(("DPM_", "ENTERPRISE_", "APP_")):
            del os.environ[name]
    os.environ.update(
        APP_PERSISTENCE_PROFILE="LOCAL",
        DPM_MANAGE_POSTGRES_DSN=dsn,
        DPM_SUPPORTABILITY_POSTGRES_DSN=dsn,
        DPM_ARTIFACT_STORE_MODE="PERSISTED",
        DPM_SUPPORT_APIS_ENABLED="true",
        DPM_ARTIFACTS_ENABLED="true",
        ENTERPRISE_ENFORCE_AUTHZ="true",
        ENTERPRISE_CAPABILITY_RULES_JSON=json.dumps({"POST /api/v1": "manage.write"}),
    )
    import uvicorn
    from src.api.main import app

    assert not app.dependency_overrides
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", log_level="warning"))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        pipe.send(listener.getsockname()[1])
        pipe.close()

        def shutdown():
            stop.wait()
            server.should_exit = True

        threading.Thread(target=shutdown, daemon=True).start()
        server.run(sockets=[listener])


@contextmanager
def _api(dsn):
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    stop = context.Event()
    process = context.Process(target=_serve, args=(dsn, child, stop))
    process.start()
    child.close()
    port = None
    try:
        assert parent.poll(45), "Native API did not publish its bound port"
        port = parent.recv()
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}", timeout=30, trust_env=False
        ) as client:
            deadline = time.monotonic() + 45
            while True:
                assert process.is_alive(), "Native API exited before readiness"
                try:
                    if client.get("/health/ready").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                assert time.monotonic() < deadline, "Native API readiness timed out"
                time.sleep(0.1)
            yield client, process
    finally:
        parent.close()
        # A killed process can leave multiprocessing.Event's lock held. Never
        # signal that shared primitive after its owning process has terminated.
        if process.is_alive():
            stop.set()
        process.join(15)
        if process.is_alive():
            process.kill()
            process.join(10)
        assert not process.is_alive(), "Owned API process was not removed"
        process.close()
        if port is not None:
            with socket.socket() as probe:
                probe.settimeout(1)
                assert probe.connect_ex(("127.0.0.1", port)) != 0, "Owned listener survived"


def _request(quote_currency):
    payload = valid_api_payload()
    payload["portfolio_snapshot"].update(
        portfolio_id=f"NETWORK_{uuid.uuid4().hex}",
        base_currency="USD",
        positions=[{"instrument_id": "EQ_1", "quantity": "100"}],
        cash_balances=[{"currency": "USD", "amount": "5000"}],
    )
    payload["market_data_snapshot"]["prices"][0]["currency"] = quote_currency
    payload["market_data_snapshot"]["fx_rates"] = (
        [{"pair": "EUR/USD", "rate": "1.25"}] if quote_currency == "EUR" else []
    )
    payload["model_portfolio"]["targets"][0]["weight"] = "0.80"
    payload["options"] = {
        "target_method": "HEURISTIC",
        "enable_settlement_awareness": False,
        "enable_tax_awareness": False,
    }
    return {
        "input_mode": "stateless",
        "stateless_input": payload,
        "methods": ["DO_NOTHING_BASELINE", "HEURISTIC_EXPLAINABLE"],
    }


def _call(client, method, path, headers, body=None, expected=200):
    response = client.request(method, path, headers=headers, json=body)
    assert response.status_code == expected, response.text
    return response.json()


def _assert_economics(client, owned, headers, quote_currency):
    baseline, heuristic = owned["alternatives"]
    assert baseline["method"] == "DO_NOTHING_BASELINE"
    assert baseline["rebalance_run_id"] is None
    assert baseline["intent_ids"] == []
    assert baseline["diagnostics"]["proposed_changes"] == []
    assert baseline["comparison_metrics"]["trade_count"] == 0
    assert Decimal(baseline["comparison_metrics"]["turnover_weight"]) == 0
    assert baseline["comparison_metrics"]["estimated_transaction_cost"] is None
    metrics = baseline["comparison_metrics"]
    assert Decimal(metrics["cash_weight_after"]) == Decimal(
        "0.2857" if quote_currency == "EUR" else "0.3333"
    )
    assert metrics["drift_after"] == metrics["drift_before"]
    assert Decimal(metrics["drift_reduction"]) == 0
    assert baseline["evaluation_context"] == {
        "rebalance_run_id": heuristic["rebalance_run_id"],
        "state_basis": "BEFORE",
    }
    artifact = _call(
        client, "GET", f"/api/v1/rebalance/runs/{heuristic['rebalance_run_id']}/artifact", headers
    )
    result = artifact["result"]
    nav, shares, usd_cash = (
        ("17500", "112", "3485") if quote_currency == "EUR" else ("15000", "120", "3000")
    )
    for state in ["before", "after_simulated"]:
        assert Decimal(result[state]["total_value"]["amount"]) == Decimal(nav)
    assert Decimal(result["before"]["positions"][0]["quantity"]) == 100
    assert Decimal(result["before"]["cash_balances"][0]["amount"]) == 5000
    assert Decimal(result["after_simulated"]["positions"][0]["quantity"]) == Decimal(shares)
    cash = {
        row["currency"]: Decimal(row["amount"])
        for row in result["after_simulated"]["cash_balances"]
    }
    assert cash["USD"] == Decimal(usd_cash)
    if quote_currency == "EUR":
        assert cash["EUR"] == 12  # 1% FX funding buffer, not invented USD cash.
    buys = [row for row in heuristic["diagnostics"]["proposed_changes"] if row["action"] == "BUY"]
    assert len(buys) == 1
    assert Decimal(buys[0]["quantity"]) == Decimal(shares) - 100


@pytest.mark.parametrize("quote_currency", ["USD", "EUR"])
def test_native_network_construction_survives_api_process_replacement(quote_currency):
    headers = {
        "X-Tenant-Id": f"tenant-network-{uuid.uuid4().hex}",
        "X-Actor-Id": "network-pm",
        "X-Role": "PM",
        "X-Service-Identity": "local-network-proof",
        "X-Capabilities": "manage.write",
        "Idempotency-Key": uuid.uuid4().hex,
        "X-Correlation-Id": uuid.uuid4().hex,
    }
    request = _request(quote_currency)
    generate = "/api/v1/construction/alternative-sets/generate"
    with _database() as dsn:
        with _api(dsn) as (client, original):
            missing_capability = {
                key: value for key, value in headers.items() if key != "X-Capabilities"
            }
            _call(client, "POST", generate, missing_capability, request, expected=403)
            owned = _call(client, "POST", generate, headers, request)
            _assert_economics(client, owned, headers, quote_currency)
            set_path = f"/api/v1/construction/alternative-sets/{owned['alternative_set_id']}"
            foreign = {**headers, "X-Tenant-Id": "foreign-network-tenant"}
            _call(client, "GET", set_path, foreign, expected=404)
            changed = deepcopy(request)
            changed["stateless_input"]["model_portfolio"]["targets"][0]["weight"] = "0.70"
            _call(client, "POST", generate, headers, changed, expected=409)
            selection = _call(
                client,
                "POST",
                f"{set_path}/selections",
                headers,
                {
                    "alternative_id": owned["alternatives"][0]["alternative_id"],
                    "actor_id": "network-pm",
                    "reason_code": "NO_ACTION",
                },
            )
            proof_body = {
                "source_type": "SELECTED_ALTERNATIVE",
                "alternative_set_id": owned["alternative_set_id"],
                "selected_alternative_id": selection["alternative_id"],
                "actor_id": "network-pm",
            }
            proof_path = f"/api/v1/rebalance/proof-packs?tenant_id={headers['X-Tenant-Id']}"
            proof = _call(client, "POST", proof_path, headers, proof_body)["proof_pack"]
            assert proof["status"] == "BLOCKED"
            assert proof["rebalance_run_id"] is None
            old_pid = original.pid
            original.kill()
            original.join(10)
            assert original.exitcode not in (None, 0)
        with _api(dsn) as (client, replacement):
            assert replacement.pid != old_pid
            assert _call(client, "GET", set_path, headers) == owned
            assert _call(client, "POST", generate, headers, request) == owned
            _assert_economics(client, owned, headers, quote_currency)
            retained_proof = _call(client, "POST", proof_path, headers, proof_body)["proof_pack"]
            assert retained_proof == proof
            _call(client, "GET", set_path, foreign, expected=404)
            rid = owned["alternatives"][1]["rebalance_run_id"]
            _call(client, "GET", f"/api/v1/rebalance/runs/{rid}/artifact", foreign, expected=404)
        # Independent read-only storage evidence: replay did not create extra
        # runs, artifacts, selections or proof packs after interpreter death.
        with psycopg.connect(dsn) as connection:
            connection.execute("SET TRANSACTION READ ONLY")
            for table in (
                "dpm_construction_alternative_sets",
                "dpm_construction_alternative_selections",
                "dpm_runs",
                "dpm_pre_trade_proof_packs",
            ):
                rows = connection.execute(
                    sql.SQL("SELECT tenant_id FROM {}").format(sql.Identifier(table))
                ).fetchall()
                assert rows == [(headers["X-Tenant-Id"],)], table
            assert connection.execute(
                "SELECT rebalance_run_id FROM dpm_run_artifacts"
            ).fetchall() == [(rid,)]
            assert (
                connection.execute(
                    "SELECT payload_json FROM dpm_construction_alternative_selections"
                ).fetchone()[0]
                == selection
            )
